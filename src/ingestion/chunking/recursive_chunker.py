import logging 
from uuid import UUID 
from langchain_text_splitters  import RecursiveCharacterTextSplitter
import tiktoken
from src.ingestion.chunking.base_chunker import BaseChunker
from src.schemas.chunk_schema import ChunkCreate

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

        