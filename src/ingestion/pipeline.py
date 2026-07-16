import logging
import hashlib
from uuid import UUID

from src.schemas.document_schema import DocumentCreate, DocumentRecord
from src.schemas.chunk_schema import ChunkCreate
from src.ingestion.loaders import get_loader, LoaderError
from src.ingestion.cleaners import TextCleaner
from src.ingestion.chunking.recursive_chunker import RecursiveChunker
from src.ingestion.chunking.semantic_chunker import SemanticChunker
from src.ingestion.chunking.chunk_enricher import ChunkEnricher
from src.ingestion.embedder import EmbeddingService, EmbeddingGenerationError
from src.database.supabase_client import supabase

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Raised when a document fails ingestion after all internal handling."""
    pass


class IngestionPipeline:
    """
    Orchestrates the full ingestion flow:
    load -> clean -> chunk -> enrich -> embed -> store in Supabase.
    Idempotent: re-running on an unchanged file (same checksum) is a no-op.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        llm_client,                      # for ChunkEnricher's contextual headers
        use_semantic_chunking: bool = False,
        use_parent_child: bool = True,
    ):
        self.embedding_service = embedding_service
        self.cleaner = TextCleaner()
        self.recursive_chunker = RecursiveChunker()
        self.semantic_chunker = SemanticChunker()
        self.enricher = ChunkEnricher(llm_client=llm_client)
        self.use_semantic_chunking = use_semantic_chunking
        self.use_parent_child = use_parent_child

    def run(self, raw_bytes: bytes, title: str, source_type: str,
            tenant_id: UUID, source_uri: str | None = None) -> DocumentRecord:

        checksum = hashlib.sha256(raw_bytes).hexdigest()

        # 1. idempotency check — skip if this exact file was already ingested
        existing = self._find_existing_document(tenant_id, checksum)
        if existing:
            logger.info(f"Document with checksum {checksum[:8]}... already ingested, skipping")
            return existing

        # 2. create the document row (status=pending)
        doc_create = DocumentCreate(
            tenant_id=tenant_id,
            title=title,
            source_uri=source_uri,
            source_type=source_type,
            checksum=checksum,
            status="pending",
        )
        document = self._insert_document(doc_create)

        try:
            self._mark_status(document.id, "processing")

            # 3. load
            loader = get_loader(source_type)
            raw_text = loader.load(raw_bytes if source_type != "url" else source_uri)

            # 4. clean
            clean_text = self.cleaner.clean(raw_text)
            if not clean_text:
                raise IngestionError("Document produced no usable text after cleaning")

            # 5. chunk
            chunker = self.semantic_chunker if self.use_semantic_chunking else self.recursive_chunker
            child_chunks = chunker.chunk(clean_text, document_id=document.id, tenant_id=tenant_id)
            if not child_chunks:
                raise IngestionError("Chunking produced zero chunks")

            # 6. enrich — contextual headers
            child_chunks = self.enricher.add_contextual_headers(child_chunks, document_title=title)

            # 7. enrich — parent-child linking (optional)
            if self.use_parent_child:
                child_chunks = self._apply_parent_child(child_chunks)

            # 8. embed
            texts = [c.content for c in child_chunks]
            vectors = self.embedding_service.embed_batch(texts)
            for chunk, vector in zip(child_chunks, vectors):
                chunk.embedding = vector

            # 9. store children
            self._insert_chunks(child_chunks)

            # 10. mark ready
            self._mark_status(document.id, "ready")
            logger.info(f"Ingestion complete: {len(child_chunks)} chunks for document {document.id}")

        except (LoaderError, EmbeddingGenerationError, IngestionError) as e:
            logger.error(f"Ingestion failed for document {document.id}: {e}")
            self._mark_status(document.id, "failed")
            raise IngestionError(f"Ingestion failed: {e}") from e

        return self._get_document(document.id)

    # ---------- internal helpers ----------

    def _apply_parent_child(self, child_chunks: list[ChunkCreate]) -> list[ChunkCreate]:
        parents, children = self.enricher.create_parent_child_links(child_chunks)

        # embed parents too (so they CAN be searched directly if ever needed,
        # though normally you search children and fetch parents by id)
        parent_texts = [p.content for p in parents]
        parent_vectors = self.embedding_service.embed_batch(parent_texts)
        for parent, vector in zip(parents, parent_vectors):
            parent.embedding = vector

        inserted_parents = self._insert_chunks(parents)
        parent_ids = [p["id"] for p in inserted_parents]

        return self.enricher.attach_parent_ids(children, parent_ids)

    def _find_existing_document(self, tenant_id: UUID, checksum: str) -> DocumentRecord | None:
        response = (
            supabase.table("documents")
            .select("*")
            .eq("tenant_id", str(tenant_id))
            .eq("checksum", checksum)
            .execute()
        )
        if response.data:
            return DocumentRecord(**response.data[0])
        return None

    def _insert_document(self, doc: DocumentCreate) -> DocumentRecord:
        response = supabase.table("documents").insert(doc.model_dump(mode="json")).execute()
        return DocumentRecord(**response.data[0])

    def _insert_chunks(self, chunks: list[ChunkCreate]) -> list[dict]:
        payload = [c.model_dump(mode="json") for c in chunks]
        response = supabase.table("chunks").insert(payload).execute()
        return response.data

    def _mark_status(self, document_id: UUID, status: str) -> None:
        supabase.table("documents").update({"status": status}).eq("id", str(document_id)).execute()

    def _get_document(self, document_id: UUID) -> DocumentRecord:
        response = supabase.table("documents").select("*").eq("id", str(document_id)).execute()
        return DocumentRecord(**response.data[0])