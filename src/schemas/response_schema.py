from pydantic import BaseModel, Field, model_validator
from uuid import UUID

class Citation(BaseModel):
    chunk_id:UUID
    document_id:UUID
    document_title:str
    snippet:str=Field(...,max_length=300) # preview 
    
class AgentResponse(BaseModel):
    """ Validate the outbound answer before it's returned to user f."""
    answer:str
    used_retrieval:bool
    citations:list[Citation]=Field(default_factory=list)
    grounded:bool
    conversation_id:UUID
    latency_ms:int = Field(...,ge=0)
    
    @model_validator(mode="after") # let us check relationships btw fields 
    def citation_is_required_if_retrieval_used(self):
        if self.used_retrieval and not self.citations:
            raise ValueError(
                "response claims to have used retrieval but has not citatio is attached " 
            )
        return self
        
    