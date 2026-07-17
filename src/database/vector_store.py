import logging
from uuid import UUID
from src.database.supabase_client import supabase

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Raised when a search operation against Supabase fails."""
    pass


class VectorStore:
    """
    The single point of contact for chunk search. Every method requires
    tenant_id, even though the backend uses the service_role key (which
    bypasses RLS) 
    """

    def similarity_search(
        self,
        query_embedding: list[float],
        tenant_id: UUID,
        k: int = 10,
    ) -> list[dict]:
        """Pure vector/semantic search — no keyword matching."""
        try:
            response = supabase.rpc(
                "match_chunks_vector_only",   # a simpler RPC, see note below
                {
                    "query_embedding": query_embedding,
                    "filter_tenant_id": str(tenant_id),
                    "match_count": k,
                },
            ).execute()
            return response.data
        except Exception as e:
            logger.error(f"Vector similarity search failed: {e}")
            raise VectorStoreError(f"similarity_search failed: {e}") from e

    def keyword_search(
        self,
        query_text: str,
        tenant_id: UUID,
        k: int = 10,
    ) -> list[dict]:
        """Pure keyword/full-text search — no semantic matching."""
        try:
            response = (
                supabase.table("chunks")
                .select("id, content, document_id")
                .eq("tenant_id", str(tenant_id))
                .text_search("content", query_text, config="english")
                .limit(k)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            raise VectorStoreError(f"keyword_search failed: {e}") from e

    def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        tenant_id: UUID,
        k: int = 10,
    ) -> list[dict]:
        """
        Combined vector + keyword search using RRF fusion.
        Calls the match_chunks_hybrid() Postgres function directly.
        """
        try:
            response = supabase.rpc(
                "match_chunks_hybrid",
                {
                    "query_embedding": query_embedding,
                    "query_text": query_text,
                    "filter_tenant_id": str(tenant_id),
                    "match_count": k,
                },
            ).execute()
            return response.data
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise VectorStoreError(f"hybrid_search failed: {e}") from e

    def get_chunk_by_id(self, chunk_id: UUID, tenant_id: UUID) -> dict | None:
        response = (
            supabase.table("chunks")
            .select("*")
            .eq("id", str(chunk_id))
            .eq("tenant_id", str(tenant_id))
            .execute()
        )
        return response.data[0] if response.data else None

    def get_parent_chunk(self, child_chunk: dict, tenant_id: UUID) -> dict | None:
        """Given a retrieved child chunk, fetch its parent (small-to-big retrieval)."""
        parent_id = child_chunk.get("parent_chunk_id")
        if not parent_id:
            return None
        return self.get_chunk_by_id(UUID(parent_id), tenant_id)