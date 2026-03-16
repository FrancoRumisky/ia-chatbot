from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    session_id: str = Field(..., min_length=1, max_length=100)
    document_ids: List[str] = Field(..., min_length=1)
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    response: str
    context_used: str
    session_id: str
    document_ids: List[str]


class ResetSessionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    session_id: str = Field(..., min_length=1, max_length=100)


class ToolDescription(BaseModel):
    name: str
    description: str


class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., min_length=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    tool_name: str
    output: str
