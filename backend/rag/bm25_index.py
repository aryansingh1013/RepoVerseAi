import math
import re
from typing import List, Dict, Any, Tuple

class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[Dict[str, Any]] = []
        self.doc_count = 0
        self.avg_doc_len = 0.0
        self.doc_lengths: List[int] = []
        self.term_freqs: List[Dict[str, int]] = []
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    def tokenize(self, text: str) -> List[str]:
        # Simple lowercased alphabetic-numeric tokenization
        text = text.lower()
        # Include underscores and dots to preserve programming concepts (variables, imports)
        return re.findall(r'[a-zA-Z0-9_\.]+', text)

    def fit(self, chunks: List[Dict[str, Any]]):
        """
        Fits BM25 index on code/text chunks.
        """
        self.documents = chunks
        self.doc_count = len(chunks)
        if self.doc_count == 0:
            return

        self.doc_lengths = []
        self.term_freqs = []
        self.doc_freqs = {}

        total_len = 0
        for chunk in chunks:
            tokens = self.tokenize(chunk["content"])
            self.doc_lengths.append(len(tokens))
            total_len += len(tokens)

            # Compute term frequencies for this document
            freqs = {}
            for t in tokens:
                freqs[t] = freqs.get(t, 0) + 1
            self.term_freqs.append(freqs)

            # Count document frequencies (how many docs have term t)
            for t in freqs.keys():
                self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1

        self.avg_doc_len = total_len / self.doc_count

        # Compute IDF for all terms
        for term, df in self.doc_freqs.items():
            # Standard BM25 IDF formula
            numerator = self.doc_count - df + 0.5
            denominator = df + 0.5
            self.idf[term] = math.log((numerator / denominator) + 1.0)

    def search(self, query: str, limit: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        Searches the BM25 index and returns list of (chunk, score) sorted descending.
        """
        if self.doc_count == 0:
            return []

        query_tokens = self.tokenize(query)
        scores = []

        for idx in range(self.doc_count):
            score = 0.0
            doc_len = self.doc_lengths[idx]
            freqs = self.term_freqs[idx]

            for term in query_tokens:
                if term not in self.idf:
                    continue
                tf = freqs.get(term, 0)
                idf = self.idf[term]
                
                # BM25 scoring function
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

            if score > 0:
                scores.append((self.documents[idx], score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]
