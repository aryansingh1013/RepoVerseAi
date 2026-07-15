import os
import chromadb
from typing import List, Dict, Any, Optional
from backend.core.config import settings

class EmbeddingsManager:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                # Load BGE embeddings
                print(f"Lazy loading embedding model {self.model_name}...")
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"Failed to load primary embedding model {self.model_name}: {e}")
                print(f"Falling back to {settings.EMBEDDING_MODEL_FALLBACK}")
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(settings.EMBEDDING_MODEL_FALLBACK)
        return self._model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(text, show_progress_bar=False)
        return embedding.tolist()


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
