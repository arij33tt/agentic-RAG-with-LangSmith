import logging
from uuid import UUID
from src.database.vector_store import VectorStore, VectorStoreError
from src.ingestion.embedder import EmbeddingService, EmbeddingGenerationError

logger = logging.getLogger(__name__)


class RetrievalError(Exception):
    """Raised when retrieval fails across all fallback options."""
    pass


class HybridRetriever:
    """
    Turns a raw user question into ranked chunks, using hybrid
    (vector + keyword) search with graceful degradation if any
    part of that fails.
    """

    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(
        self,
        query_text: str,
        tenant_id: UUID,
        k: int = 10,
    ) -> list[dict]:
        # 1. embed the query — if this fails,  truly cannot do vector
        #    search at all, so fall back to keyword-only rather than failing
        try:
            query_embedding = self.embedding_service.embed_single(query_text)
        except EmbeddingGenerationError as e:
            logger.warning(f"Query embedding failed, falling back to keyword-only search: {e}")
            return self._keyword_only_fallback(query_text, tenant_id, k)

        # 2. try full hybrid search first (best quality)
        try:
            results = self.vector_store.hybrid_search(
                query_embedding=query_embedding,
                query_text=query_text,
                tenant_id=tenant_id,
                k=k,
            )
            return results
        except VectorStoreError as e:
            logger.warning(f"Hybrid search failed, falling back to vector-only: {e}")

        # 3. fall back to vector-only search
        try:
            results = self.vector_store.similarity_search(
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                k=k,
            )
            return results
        except VectorStoreError as e:
            logger.warning(f"Vector-only search also failed, falling back to keyword-only: {e}")

        # 4. last resort — keyword-only search
        return self._keyword_only_fallback(query_text, tenant_id, k)

    def _keyword_only_fallback(self, query_text: str, tenant_id: UUID, k: int) -> list[dict]:
        try:
            return self.vector_store.keyword_search(query_text, tenant_id, k)
        except VectorStoreError as e:
            logger.error(f"All retrieval methods failed: {e}")
            raise RetrievalError("All retrieval methods (hybrid, vector, keyword) failed") from e

    def retrieve_with_parents(
        self,
        query_text: str,
        tenant_id: UUID,
        k: int = 10,
    ) -> list[dict]:
        """
        Retrieves child chunks as usual, then swaps in each one's parent
        chunk content for generation (small-to-big retrieval, Part 4.5).
        """
        children = self.retrieve(query_text, tenant_id, k)
        enriched = []
        for child in children:
            parent = self.vector_store.get_parent_chunk(child, tenant_id)
            enriched.append({
                **child,
                "generation_content": parent["content"] if parent else child["content"],
            })
        return enriched