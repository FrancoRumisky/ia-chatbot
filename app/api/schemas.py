from typing import List

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    document_ids: List[str] = Field(..., min_length=1)
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    response: str
    context_used: str
    session_id: str
    document_ids: List[str]


class ResetSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
