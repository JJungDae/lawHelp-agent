from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    category: str
    guardrail_blocked: bool = False
    is_fallback: bool = False
    retrieved_count: int = 0
