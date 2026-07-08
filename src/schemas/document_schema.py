from pydantic import BaseModel,Field ,  field_validator
from uuid import UUID
from typing import Literal
from datetime import datetime
import re  

SOURCE_TYPES = Literal["pdf", "html", "docx", "url", "txt", "markdown"]

class DocumentCreate(BaseModel):
    """ validated the documents before it is written to the SupppaBase """
    tenant_id: UUID
    title:str=Field(...,min_length=1,max_length=500)
    source_uri: str | None = None
    source_type: SOURCE_TYPES
    checksum:str=Field(...,min_length=64,max_length=64) # sh256 checksum of the document
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    metadata:dict = Field(default_factory=dict)
    
    
    @field_validator("title")
    @classmethod
    def no_blank_title(cls,v:str)->str:
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()
    
    @field_validator("checksum")
    @classmethod
    def checksum_must_be_hex(cls,v:str)->str :
        if not re.fullmatch(r"[0-9a-fA-F]{64}", v.lower()):
            raise ValueError("Checksum must be a 64-character hexadecimal string")
        return v.lower()
    
    
    
class DocumentRecord(DocumentCreate):
    """ what comes back from the database after a document is created"""
    id:UUID
    created_at:datetime
    updated_at:datetime
        
    
