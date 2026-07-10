import logging 
import re 
from uuid import UUID 
import numpy as np 
from sentence_transformers import SentenceTransformer

from src.ingestion.chunking.base_chunker import BaseChunker
from src.schemas.chunk_schema import ChunkCreate

logger = logging.getLogger(__name__)

class SemanticChunker(BaseChunker):
    """
    Splits text where the MEANING shifts, rather than at a fixed size.
    Best for long, unstructured prose with no headers (transcripts,
    contracts, books). More expensive than RecursiveChunker - use
    selectively, not as the default for every document.
    """
    def __init__(self,similarity_threshold:float=0.6,
                 min_sentences_per_chunk:int = 3,
                 max_chunk_tokens:int = 800,
                 embedding_model_name: str = "all-MiniLM-L6-v2",
                 ): 
        self.model=SentenceTransformer(embedding_model_name)
        self.similarity_threshold = similarity_threshold
        self.min_sentences_per_chunk=min_sentences_per_chunk
        self.max_chunk_tokens=max_chunk_tokens
        
    def _split_into_sentences(self,text:str)-> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip()for s in sentences if s.strip()]
    
    
    def _cosine_similarity(self,a:np.ndarray,b:np.ndarray)-> float:
        return float(np.dot(a,b)/ (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def chunk(self, text:str,document_id:UUID,tenant_id:UUID)-> list[ChunkCreate]:
        sentences = self._split_into_sentences(text)
        if len(sentences) <self.min_sentences_per_chunk:
            return self._build_chunk([text],document_id,tenant_id)
        
        sentence_embeddings=self.model.encode(sentences)

        boundries=[0]
        for i in range (1,len(sentences)):
            sim =  self._cosine_similarity(sentence_embeddings[i - 1], sentence_embeddings[i])

            if sim<self.similarity_threshold:
                boundries.append(i)
        boundries.append(len(sentences)) # end of the last chunk 
        
        raw_chunks= []
        
        for start , end in zip (boundries[:-1],boundries[1:]):
            group = sentences[start:end]
            
            if len(group) < self.min_sentences_per_chunk and raw_chunks:
                # too small a group — merge it into the previous chunk
                # instead of creating a tiny, low-value chunk
                raw_chunks[-1]= " " + " ".join(group)
            else: 
                raw_chunks.append(" ".join(group))

        return self._build_chunks(raw_chunks,document_id,tenant_id)
    
    
    def _build_chunks(self,raw_chunks : list[str],document_id:UUID,tenant_id:UUID)-> list[ChunkCreate]:
        
        chunks: list[ChunkCreate]=[]
        
        for index , raw_chunk in enumerate(raw_chunks):
            token_count=max(1,len(raw_chunk.split()))
            try:
                chunk = ChunkCreate(
                    document_id=document_id,
                    tenant_id=tenant_id,
                    content = raw_chunk,
                    chunk_index=index,
                    token_count= min(token_count,2000)
                )
                
                chunks.append(chunk)
            except Exception as e :
                logger.warning(f"skipped invalid chunk at index {index} : Ex-> {e}")
        
        logger.info(f"SemanticChunker produced {len(chunks)} chunks for document {document_id}")
        return chunks
        
        
    
        

