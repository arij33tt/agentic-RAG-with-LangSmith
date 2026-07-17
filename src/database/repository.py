import logging
from uuid import UUID
from datetime import datetime
from src.database.supabase_client import supabase

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Raised when a non-search database operation fails."""
    pass


class Repository:
    """
    General-purpose data access layer for documents, audit logs, etc.
    Search-specific queries live in vector_store.py instead.
    """

    def get_document(self, document_id: UUID, tenant_id: UUID) -> dict | None:
        try:
            response = (
                supabase.table("documents")
                .select("*")
                .eq("id", str(document_id))
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            raise RepositoryError(f"get_document failed: {e}") from e

    def list_documents(self, tenant_id: UUID, status: str | None = None) -> list[dict]:
        try:
            query = supabase.table("documents").select("*").eq("tenant_id", str(tenant_id))
            if status:
                query = query.eq("status", status)
            response = query.execute()
            return response.data
        except Exception as e:
            raise RepositoryError(f"list_documents failed: {e}") from e

    def log_interaction(
        self,
        tenant_id: UUID,
        user_id: UUID,
        query_text: str,
        retrieved_chunk_ids: list[UUID],
        response_text: str,
        latency_ms: int,
        flagged: bool = False,
        flagged_reason: str | None = None,
    ) -> None:
        """Writes one row to audit_log — called at the end of every /chat request."""
        try:
            supabase.table("audit_log").insert({
                "tenant_id": str(tenant_id),
                "user_id": str(user_id),
                "query_text": query_text,
                "retrieved_chunk_ids": [str(cid) for cid in retrieved_chunk_ids],
                "response_text": response_text,
                "latency_ms": latency_ms,
                "flagged": flagged,
                "flagged_reason": flagged_reason,
            }).execute()
        except Exception as e:
            # never let audit logging failure break the actual user response —
            # log locally and move on, this is non-critical-path
            logger.error(f"Failed to write audit log: {e}")

    def get_low_quality_queries(self, tenant_id: UUID, limit: int = 20) -> list[dict]:
        """Surfaces flagged/low-groundedness interactions for review (Part 13.3)."""
        try:
            response = (
                supabase.table("audit_log")
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .eq("flagged", True)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data
        except Exception as e:
            raise RepositoryError(f"get_low_quality_queries failed: {e}") from e