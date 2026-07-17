import logging
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class Reranker:
    """
    Re-scores candidate chunks using a cross-encoder for higher
    accuracy than embedding similarity alone. Degrades gracefully
    (passes through unranked-but-fused order) if the model fails.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        try:
            self.model = CrossEncoder(model_name)
            self.available = True
        except Exception as e:
            logger.error(f"Failed to load reranker model, reranking will be skipped: {e}")
            self.model = None
            self.available = False

    def rerank(
        self,
        query_text: str,
        candidates: list[dict],
        top_n: int = 5,
        content_field: str = "content",
    ) -> list[dict]:
        if not candidates:
            return []

        if not self.available:
            logger.warning("Reranker unavailable, passing through original order")
            return candidates[:top_n]

        try:
            pairs = [(query_text, c[content_field]) for c in candidates]
            scores = self.model.predict(pairs)

            scored = list(zip(candidates, scores))
            scored.sort(key=lambda x: x[1], reverse=True)

            return [chunk for chunk, score in scored[:top_n]]
        except Exception as e:
            logger.warning(f"Reranking failed at query time, passing through original order: {e}")
            return candidates[:top_n]