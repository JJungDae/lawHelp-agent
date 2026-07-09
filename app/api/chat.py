from fastapi import APIRouter

from app.agents.workflow import run_chat_workflow
from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sync", response_model=ChatResponse)
def chat_sync(request: ChatRequest) -> ChatResponse:
    return run_chat_workflow(
        message=request.message,
        thread_id=request.thread_id,
    )
