from pydantic import BaseModel, Field , field_validator

from uuid import UUID

from datetime import datetime 


class ChunkCreate(BaseModel):
    
    """ Validates the chunks before it is written to the SUPABASe Database.
    This is to ensure that the data is in the correct format and that all 
    required fields are present. """

    document_id:UUID
    tenant_id:UUID
    content:str= Field(...,description="The content of the chunk", min_length=1,max_length=6000)
    chunk_index:int= Field(...,ge=0)
    token_count:int = Field(...,gt=0,le=2000)
    section_path:str | None = None
    parent_chunk_id: UUID | None = None
    embedding:list[float] | None = None # pupolated after embedding is generated 
    
    
    @field_validator("content")
    @classmethod
    def no_empty_or_whitespace(cls,v: str)-> str:
        
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace")
        return v.strip()
    
    
    @field_validator("embedding")
    @classmethod
    def check_embedding_dimension(cls,v):
        if v is not None and len(v) != 1024:
            raise ValueError(f"Embedding must be a list of 1024 floats but got {len(v)}")
        return v
    
class ChunkRecord(ChunkCreate):
    
    """ what comes back from the database after a chunk is created"""
    id:UUID
    created_at:datetime
        
