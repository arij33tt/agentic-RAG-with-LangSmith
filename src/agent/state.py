from typing import TypedDict, Annotated
from operator import add 
from langchain_core.messages import BaseMessage 


class AgentState(TypedDict):
    messages : Annotated[list[BaseMessage],add] 
    questions:str
    rewritten_questions:str |None
    documents:list[dict] # retrieved chunks 
    generation:str |None
    retry_count:int
    grounded:bool |None
    route:str|None
    tenant_id:str
    user_id:str
    security_flags: list[str]
    





