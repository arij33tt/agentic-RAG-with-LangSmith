import hashlib
from uuid import UUID
import logging
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
    """ Raise exception when ingestion failed """
    pass

class IngestionPipeline:
    """
    orchestrate full ingestion flow 
    i.e 
     load -> chunk -> enrich ->embed - > sotre Supabase
     
     IDEMPOTENT H
    
    """
    def __init__(
        self,
        embedding_service:EmbeddingService,
        llm_client, # contextual meaning add 
        use_semantic_chunking:bool = False,
        use_parent_child:bool=True
    ):
        self.embedding_service= embedding_service
        self.cleaner = TextCleaner()
        self.semantic_chunker= SemanticChunker()
        self.recursive_chunker = RecursiveChunker()
        self.enricher = ChunkEnricher(llm_client=llm_client)
        self.use_semantic_chunking = use_semantic_chunking
        self.use_parent_child = use_parent_child
        
    
    def run( self , raw_bytes:bytes, title:str,source_type:str,
            tenant_id:UUID,source_uri:str | None=None)->DocumentRecord:
        checksum =  hashlib.sha256(raw_bytes).hexdigest()
        existing=self._find_existing_document(tenant_id,checksum)
        
        if existing:
            logger.info(f"Document with checksum {checksum[:9]} is already present/igested ")
            return existing

        
        #  create the document row 
        doc_create = DocumentCreate(
            tenant_id=tenant_id,
            source_type=source_type,
            source_uri=source_uri,
            status="pending",
            checksum=checksum,
            title=title
            )
        document = self._insert_document(doc_create)
        
        try :
            self._makr_status(document.id,"processing")
            # load
            loader = get_loader(source_type)
            raw_text = loader.load(raw_bytes if source_type !="url" else source_uri)
            
            # clean
            clean_text = self.cleaner.clean(raw_text)
            if not clean_text:
                raise IngestionError(f"Document produced no usable text after cleaning")
            
            # chunking 
            chunker = self.semantic_chunker if self.use_semantic_chunking else self.recursive_chunker
            child_chunks = chunker.chunk(clean_text,document_id=document.id,tenant_id=tenant_id)
            if not child_chunks:
                raise IngestionError(f"failed to produced chunk or 0 chunk produced ")
            
            #  enrich k contextual headers 
            
            child_chunks=self.enricher.add_contextual_headers(child_chunks,document_title=title)

            # enrich parent chunk 
            if self.use_parent_child:
                child_chunks = self._apply_parent_child(child_chunks)
            
            
            #  embedding 
            
            texts = [c.content for c in child_chunks]
            vectors= self.embedding_service.embed_batch(texts=texts)
            
            for chunk , vector in zip (child_chunks,vectors):
                chunk.embedding = vector
            
            
            #  store children 
            
            self._insert_chunks(child_chunks)
            
            self._makr_status(document.id,"ready")
            logger.info(f" ingestion complete for the document {document.id} and length of chunks ->  {len(child_chunks)}")
            
            
        except Exception(LoaderError,EmbeddingGenerationError,IngestionError) as e :
            logger.error(f"Ingestion failed for document {document.id}: {e}")
            self._mark_status(document.id, "failed")
            raise IngestionError(f"Ingestion failed: {e}") from e
        
        
        
        return self._get_document(document.id)
    
    
    #  my internal helpsers
    
    def _apply_parent_child (self,child_chunks:list[ChunkCreate])-> list[ChunkCreate]:
        parents , children = self.enricher.create_parent_chunk_links(child_chunks=child_chunks)
        
        #  embedding the parent as well tough we search them by child chunk 
        
        parent_texts= [p.content for p in parents]
        parent_vectors=self.embedding_service.embed_batch(parent_texts)
        
        for parent,vector in zip (parents,parent_vectors):
            parent.embedding =vector
            
        inserted_parents= self._insert_chunks(parents)
        parent_ids = [p["id"] for p in inserted_parents]
        
        return self.enricher.attach_parent_ids(children, parent_ids)
    
    
    def _find_existing_document(self , tenant_id:UUID, checksum)->DocumentRecord | None:
        response = (
            supabase.table("documents")
            .select("*")
            .eq("tenant_id", str(tenant_id))
            .eq("checksum",checksum)
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
    
        
            
    
            
            
        
    
    
    