from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from typing import Literal
from datetime import datetime



class UserQuery(BaseModel):
    """ validates user incoming wuery before it is reaches to the agent """

    question:str =Field(...,min_length=1,max_length=1000)
    
    tenant_id:UUID
    
    user_id:UUID
    conversation_id:UUID | None = None
    
    
    @field_validator("question")
    @classmethod
    def clean_questions(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Question cannot be empty or whitespace")
        cleaned = "".join(ch for ch in stripped if ch.isprintable() or ch in "\n\t")
        if not cleaned:
            raise ValueError("question contains no valid printable content")
        return cleaned

