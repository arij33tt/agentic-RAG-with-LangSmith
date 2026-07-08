import logging 
from uuid import UUID 
from langchain_text_splitters  import RecursiveCharacterTextSplitter
import tiktoken
from src.ingestion.chunking.base_chunker import BaseChunker
from src.schemas.chunk_schema import ChunkCreate
logger = logging.getLogger(__name__)

class RecursiveChunker(BaseChunker):
    """
    Structure-aware chunking: tries paragraph breaks first, then
    sentences, then words — only cutting mid-sentence as a last resort.
    This is the safe, reliable default chunker for most document types.
    """
    
    def  __init__(self,chunk_size:int = 600,chunk_overlap:int = 200,
                  encoding_name:str ="cl100k_base" ):
        
        self.tokenizer= tiktoken.get_encoding(encoding_name)
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function = self._count_tokens,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        
        def _count_tokens(self, text:str)-> int:
            
            return len (self.tokenizer.encode(text))
        
        def chunk(
            self,
            text:str,
            document_id:UUID,
            tenant_id:UUID
        ) -> list[ChunkCreate]:
            
            raw_chunks=self.splitter.split_text(text)
            
            chunks:list[ChunkCreate]=[]
            
            for index , raw_chunk in enumerate(raw_chunks):
                token_count=self._count_tokens(raw_chunk)
                try:
                    chunk = ChunkCreate(
                        document_id=document_id,
                         tenant_id= tenant_id,
                         content=raw_chunk,
                         token_count= token_count,
                    )
                    chunks.append(chunk)
                except Exception as e :
                    logging.warning(f"Skipped invalid chunk at index {index}: {e}")

            logger.info(f"RecursiveChunker produced {len(chunks)} chunks for document {document_id}")
            return chunks

        