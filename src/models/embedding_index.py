import faiss
import numpy as np
from typing import List, Dict, Any, Tuple
import pickle
import os
import hashlib


class ProductEmbeddingIndex:
    """Lightweight, Torch-free embedding index.

    NOTE: This implementation intentionally avoids SentenceTransformer / Torch
    to prevent native segfaults on some macOS/Python combinations. It uses a
    simple hashing-based bag-of-words embedding instead. This is less accurate
    than a real transformer model but safe and fast, and keeps the API running.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim
        self.index = None
        self.product_ids: List[str] = []
        self.embeddings: np.ndarray | None = None
        
    def build_index(self, products: List[Dict[str, Any]]):
        """Build FAISS index from product descriptions"""
        descriptions = []
        self.product_ids = []
        
        for product in products:
            desc = f"{product['style']} {product['category']} {product['color_primary']} {product['material']} {product['name']} {product['description']}"
            descriptions.append(desc)
            self.product_ids.append(product['walmart_id'])

        # Generate embeddings using lightweight hashing encoder
        self.embeddings = self._encode(descriptions)

        # Build FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for similarity
        self.index.add(self.embeddings.astype("float32"))
        
        print(f"Built FAISS index with {len(products)} products")
    
    def search_similar(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """Search for similar products"""
        if self.index is None:
            return []

        query_embedding = self._encode([query])
        scores, indices = self.index.search(query_embedding.astype("float32"), top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.product_ids):
                results.append((self.product_ids[idx], float(score)))
        
        return results
    
    def save_index(self, path: str):
        os.makedirs(path, exist_ok=True)  # Create directory if it doesn't exist
        if self.index is not None:
            faiss.write_index(self.index, f"{path}/faiss.index")
    
        with open(f"{path}/metadata.pkl", 'wb') as f:
            pickle.dump({
                'product_ids': self.product_ids,
                'embeddings': self.embeddings
            }, f)
        print(f"✅ Saved FAISS index to {path}")
    
    def load_index(self, path: str):
        """Load index from disk"""
        self.index = faiss.read_index(f"{path}/faiss.index")
        
        with open(f"{path}/metadata.pkl", 'rb') as f:
            metadata = pickle.load(f)
            self.product_ids = metadata["product_ids"]
            self.embeddings = metadata["embeddings"]

    def _encode(self, texts: List[str]) -> np.ndarray:
        """Deterministic hashing-based embedding for a list of texts.

        For each token, we hash it and map into a fixed-size vector, summing
        contributions. This gives a rough semantic signal without heavy models.
        """
        vecs = np.zeros((len(texts), self.dim), dtype="float32")

        for i, text in enumerate(texts):
            tokens = str(text).lower().split()
            for tok in tokens:
                # Stable hash to 64-bit integer, then fold into embedding dim
                h = int(hashlib.sha256(tok.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dim
                sign = 1.0 if (h >> 63) & 1 == 0 else -1.0
                vecs[i, idx] += sign

        # L2-normalize to make inner product behave like cosine similarity
        norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-8
        vecs = vecs / norms
        return vecs
