from pydantic import BaseModel, Field
from uuid import UUID

class AgentStateValidator(BaseModel):
    
     """
    Mirrors the LangGraph AgentState TypedDict (src/agent/state.py).
    Used to validate state at entry/exit points of the graph — NOT
    used inside the graph itself (LangGraph needs the TypedDict for that).
    """
     question:str =Field(...,min_length=1)
     rewritten_question:str |None = None
     documents: list[dict] = Field(default_factory=list) #avoids the shared-mutable-default bug.
     generation: str | None = None
     retry_count: int = Field(default=0, ge=0, le=5)
     grounded: bool | None = None
     route: str | None = None #Literal["retrieve", "direct", "tool"] 
     tenant_id: UUID
     security_flags: list[str] = Field(default_factory=list)
     
     
     def has_exceeded_retries(self, max_retries: int) -> bool:
        return self.retry_count >= max_retries
   
     