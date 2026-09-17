import hashlib
import json
import logging
import math
import os
import re
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    """
    Embedding Engine for Semantic & Hybrid Search (PRD Section 42, 61, 74).
    Supports:
    1. Remote OpenAI Compatible API (/v1/embeddings)
    2. Local zero-dependency semantic feature projection (N-gram feature hashing + L2 normalization)
    3. Cosine similarity calculation
    4. Reciprocal Rank Fusion (RRF) for Hybrid BM25 + Vector Retrieval
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model
        self.dim = 256

    def _local_hash_vector(self, text: str) -> List[float]:
        """
        Pure-Python zero-dependency semantic feature projector using
        sliding CJK character n-grams, word tokens, and signed hash projection with L2 normalization.
        """
        if not text or not text.strip():
            return [0.0] * self.dim

        vec = [0.0] * self.dim
        tokens = []

        # 1. Alphanumeric words
        words = re.findall(r'[a-zA-Z0-9_]{2,}', text.lower())
        tokens.extend(words)

        # 2. CJK characters and sliding 1-gram, 2-gram, 3-gram shingles
        cjk_chunks = re.findall(r'[\u4e00-\u9fa5]+', text)
        for chunk in cjk_chunks:
            for c in chunk:
                tokens.append(c)
            for i in range(len(chunk) - 1):
                tokens.append(chunk[i:i+2])
            for i in range(len(chunk) - 2):
                tokens.append(chunk[i:i+3])

        if not tokens:
            tokens = text.lower().split()

        for t in tokens:
            h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            # Give higher weight to longer n-grams
            weight = 1.0 + 0.5 * (len(t) - 1)
            vec[idx] += sign * weight

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            vec = [x / norm for x in vec]
        return vec

    async def get_embedding(self, text: str) -> List[float]:

        """
        Retrieve embedding vector. Uses remote API if configured; otherwise uses
        the built-in local semantic projector.
        """
        if not text or not text.strip():
            return [0.0] * self.dim

        clean_text = text[:4000].replace("\n", " ").strip()

        if self.api_key and "openai" in self.base_url.lower():
            try:
                import httpx
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "input": clean_text
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{self.base_url}/embeddings", json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["data"][0]["embedding"]
            except Exception as e:
                logger.warning(f"Remote embedding request failed, falling back to local projector: {e}")

        return self._local_hash_vector(clean_text)

    def get_embedding_sync(self, text: str) -> List[float]:
        """Synchronous embedding generation (defaults to local projector for speed)."""
        return self._local_hash_vector(text)

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two unit vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 < 1e-9 or norm2 < 1e-9:
            return 0.0
        return dot / (norm1 * norm2)

    @staticmethod
    def reciprocal_rank_fusion(
        ranked_lists: List[List[str]],
        k: int = 60
    ) -> List[Tuple[str, float]]:
        """
        Reciprocal Rank Fusion (RRF) algorithm to combine multiple ranking lists.
        Score(d) = sum(1 / (k + rank(d)))
        """
        scores: Dict[str, float] = {}
        for r_list in ranked_lists:
            for rank_idx, doc_id in enumerate(r_list):
                rank = rank_idx + 1
                scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))

        sorted_items = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return sorted_items

# Global singleton
embedding_engine = EmbeddingEngine()
