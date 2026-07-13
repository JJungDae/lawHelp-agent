import json
from typing import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.nodes import (
    GENERATION_SYSTEM_PROMPT,
    LEGAL_NOTICE,
    AgentState,
    _build_generation_prompt,
    build_source_link_line,
    fallback_response,
    guardrail_exit,
    retrieve,
    scope_check,
)
from app.agents.workflow import run_chat_workflow
from app.core.llm import LLMError, stream_text
from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sync", response_model=ChatResponse)
def chat_sync(request: ChatRequest) -> ChatResponse:
    return run_chat_workflow(
        message=request.message,
        thread_id=request.thread_id,
    )


@router.post("/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_chat_events(request),
        media_type="text/event-stream",
    )


def _stream_chat_events(request: ChatRequest) -> Iterator[str]:
    state: AgentState = {
        "message": request.message,
        "thread_id": request.thread_id,
        "category": "기타",
        "documents": [],
        "guardrail_blocked": False,
        "is_fallback": False,
        "retrieved_count": 0,
    }

    state = scope_check(state)
    if state.get("guardrail_blocked"):
        state = guardrail_exit(state)
        yield _sse_event("token", {"text": state.get("answer", "")})
        yield _sse_event("done", {})
        return

    state = retrieve(state)
    documents = state.get("documents", [])
    if state.get("retrieved_count", 0) == 0:
        state = fallback_response(state)
        yield _sse_event("token", {"text": state.get("answer", "")})
        yield _sse_event("done", {})
        return

    try:
        prompt = _build_generation_prompt(request.message, documents)
        streamed_text = ""
        for text in stream_text(prompt=prompt, system=GENERATION_SYSTEM_PROMPT):
            streamed_text += text
            yield _sse_event("token", {"text": text})

        # 본문 전송 완료 후, done 전에 원문 링크와 고지문을 부착한다
        # (본문 → 링크 → 고지문 순서. 차단·fallback·error 경로에는 부착하지 않는다)
        tail_parts = []
        link_line = build_source_link_line(documents)
        if link_line:
            tail_parts.append(link_line)
        if LEGAL_NOTICE not in streamed_text:
            tail_parts.append(LEGAL_NOTICE)
        if tail_parts:
            yield _sse_event("token", {"text": "\n\n" + "\n\n".join(tail_parts)})
        yield _sse_event("done", {})
    except LLMError as exc:
        yield _sse_event("error", {"message": str(exc)})


def _sse_event(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
