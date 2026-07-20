import os
import chromadb
from typing import List, Dict, Any, Optional
from backend.core.config import settings

class EmbeddingsManager:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.hf_token = getattr(settings, "HF_TOKEN", "") or os.getenv("HF_TOKEN", "")
        self._local_model = None

    def _embed_via_hf_api(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Calls Hugging Face Cloud Inference API (0 MB server RAM usage)."""
        import requests
        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
            
        url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
        try:
            resp = requests.post(url, headers=headers, json={"inputs": texts, "options": {"wait_for_model": True}}, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) == len(texts):
                    # 3D token array -> mean pooling
                    if len(data) > 0 and isinstance(data[0], list) and len(data[0]) > 0 and isinstance(data[0][0], list):
                        pooled = []
                        for doc_tokens in data:
                            num_tokens = len(doc_tokens)
                            dim = len(doc_tokens[0])
                            vec = [sum(doc_tokens[t][d] for t in range(num_tokens)) / num_tokens for d in range(dim)]
                            pooled.append(vec)
                        return pooled
                    # 2D document array
                    elif len(data) > 0 and isinstance(data[0], list) and isinstance(data[0][0], (int, float)):
                        return data
        except Exception as e:
            print(f"EmbeddingsManager: HF Inference API failed: {e}")
        return None

    def _embed_via_gemini(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Fallback to Gemini embedding API if GEMINI_API_KEY set."""
        api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=texts
            )
            if "embedding" in result:
                emb = result["embedding"]
                if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
                    return emb
                elif isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], (int, float)):
                    return [emb]
        except Exception as e:
            print(f"EmbeddingsManager: Gemini embedding failed: {e}")
        return None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # 1. Try Hugging Face Cloud Inference API (0 MB RAM)
        api_res = self._embed_via_hf_api(texts)
        if api_res is not None:
            return api_res

        # 2. Try Gemini Embedding API
        gemini_res = self._embed_via_gemini(texts)
        if gemini_res is not None:
            return gemini_res

        # 3. Fallback to local SentenceTransformer if available
        if self._local_model is None:
            try:
                print("EmbeddingsManager: Falling back to local SentenceTransformer...")
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"EmbeddingsManager: Local model load failed: {e}")
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer(settings.EMBEDDING_MODEL_FALLBACK)
                
        embeddings = self._local_model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        res = self.embed_texts([text])
        return res[0] if res else [0.0] * 384


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.DB_DIR)
        self.embeddings = EmbeddingsManager()
        self.collection_name = "repoverse_chunks"
        
        # Ensure collection exists
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"} # cosine similarity
        )

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Expects chunk dictionaries:
        {
           "content": "str",
           "metadata": { ... }
        }
        """
        if not chunks:
            return

        ids = []
        documents = []
        metadatas = []
        
        for idx, chunk in enumerate(chunks):
            # Unique ID based on path and start line
            path = chunk["metadata"]["path"]
            chunk_type = chunk["metadata"]["chunk_type"]
            start = chunk["metadata"]["start_line"]
            
            chunk_id = f"{path}#{chunk_type}#{start}#{idx}"
            
            ids.append(chunk_id)
            documents.append(chunk["content"])
            
            # Serialize metadata for ChromaDB (no lists allowed as metadata values)
            meta = chunk["metadata"].copy()
            meta["imports"] = json.dumps(meta["imports"]) if isinstance(meta["imports"], list) else str(meta["imports"])
            meta["exports"] = json.dumps(meta["exports"]) if isinstance(meta["exports"], list) else str(meta["exports"])
            metadatas.append(meta)

        # Generate embeddings in batches to avoid CPU memory saturation
        EMBED_BATCH = 32
        all_embeddings = []
        for i in range(0, len(documents), EMBED_BATCH):
            batch = documents[i:i + EMBED_BATCH]
            all_embeddings.extend(self.embeddings.embed_texts(batch))
        
        # Upsert into Chroma
        self.collection.upsert(
            ids=ids,
            embeddings=all_embeddings,
            documents=documents,
            metadatas=metadatas
        )

    def search(self, query: str, limit: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Semantic search in ChromaDB.
        """
        query_vector = self.embeddings.embed_query(query)
        
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=where
        )

        formatted_results = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            ids = results["ids"][0]
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

            for i in range(len(docs)):
                meta = metas[i].copy()
                # Deserialize lists
                try:
                    meta["imports"] = json.loads(meta["imports"])
                except Exception:
                    pass
                try:
                    meta["exports"] = json.loads(meta["exports"])
                except Exception:
                    pass
                
                formatted_results.append({
                    "id": ids[i],
                    "content": docs[i],
                    "metadata": meta,
                    "score": 1.0 - distances[i] # Cosine similarity score
                })

        return formatted_results

    def clear(self):
        """
        Clears all documents from the collection efficiently (IDs only).
        """
        try:
            results = self.collection.get(include=[])  # fetch only IDs, no content
            if results and "ids" in results and results["ids"]:
                self.collection.delete(ids=results["ids"])
        except Exception as e:
            print(f"VectorStore: Failed to clear collection: {e}")
import json # Used inside class
