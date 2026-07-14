from typing import List, Dict, Any, Optional
from backend.rag.vector_store import VectorStore
from backend.rag.bm25_index import BM25Index

class HybridRetriever:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.bm25 = BM25Index()
        self.all_chunks = []

    def fit_bm25(self, chunks: List[Dict[str, Any]]):
        """
        Updates the BM25 index with the current set of codebase chunks.
        """
        self.all_chunks = chunks
        self.bm25.fit(chunks)

    def retrieve(self, query: str, limit: int = 5, where_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Retrieves top documents using Reciprocal Rank Fusion (RRF) over
        Vector search and BM25 lexical search.
        """
        if not self.all_chunks:
            # Fall back to vector search only if BM25 is not fitted
            return self.vector_store.search(query, limit=limit, where=where_filter)

        # 1. Retrieve from Vector Store
        vector_results = self.vector_store.search(query, limit=limit * 2, where=where_filter)
        
        # 2. Retrieve from BM25
        # Apply where_filter manually to BM25 results if active
        bm25_results = self.bm25.search(query, limit=limit * 2)
        if where_filter:
            filtered_bm25 = []
            for doc, score in bm25_results:
                match = True
                for k, v in where_filter.items():
                    if doc.get("metadata", {}).get(k) != v:
                        match = False
                        break
                if match:
                    filtered_bm25.append((doc, score))
            bm25_results = filtered_bm25

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF Score = 1 / (60 + rank_vector) + 1 / (60 + rank_bm25)
        rrf_scores = {}
        doc_map = {}
        
        # Helper to compute key
        def get_chunk_key(doc: Dict[str, Any]) -> str:
            meta = doc.get("metadata", {})
            path = meta.get("path", "unknown_path")
            chunk_type = meta.get("chunk_type", "unknown_type")
            start_line = meta.get("start_line", 1)
            return f"{path}#{chunk_type}#{start_line}"

        # Vector Ranks
        for rank, doc in enumerate(vector_results, start=1):
            key = get_chunk_key(doc)
            doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (60.0 + rank))

        # BM25 Ranks
        for rank, (doc, _) in enumerate(bm25_results, start=1):
            key = get_chunk_key(doc)
            # Add to map if not present (BM25 can return docs that vector search missed)
            if key not in doc_map:
                doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (60.0 + rank))

        # Sort combined documents by RRF score descending
        sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        
        merged_results = []
        for key in sorted_keys[:limit]:
            doc = doc_map[key].copy()
            # Store RRF score in results
            doc["rrf_score"] = rrf_scores[key]
            merged_results.append(doc)
            
        return merged_results
