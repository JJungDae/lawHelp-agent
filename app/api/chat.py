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
from app.core.observability import (
    add_trace_attributes,
    build_trace_metadata,
    guardrail_result_from_state,
    mask_sensitive_text,
    response_type_from_state,
    start_trace,
    trace_tags,
)
from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter(prefix="/chat", tags=["chat"])
STREAM_TRACE_NAME = "law-help-chat-stream"
STREAM_ENDPOINT = "/chat/stream"


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
    state = _initial_state(request)

    with start_trace(
        name=STREAM_TRACE_NAME,
        input={"question": mask_sensitive_text(request.message)},
        metadata=build_trace_metadata(endpoint=STREAM_ENDPOINT, mode="stream"),
        tags=trace_tags("stream", "pending"),
    ) as trace:
        state = scope_check(state)
        if state.get("guardrail_blocked"):
            state = guardrail_exit(state)
            _complete_stream_trace(trace, state, state.get("answer", ""))
            yield _sse_event("token", {"text": state.get("answer", "")})
            yield _sse_event("done", {})
            return

        state = retrieve(state)
        documents = state.get("documents", [])
        if state.get("retrieved_count", 0) == 0:
            state = fallback_response(state)
            _complete_stream_trace(trace, state, state.get("answer", ""))
            yield _sse_event("token", {"text": state.get("answer", "")})
            yield _sse_event("done", {})
            return

        try:
            prompt = _build_generation_prompt(request.message, documents)
            streamed_text = ""
            for text in stream_text(prompt=prompt, system=GENERATION_SYSTEM_PROMPT):
                streamed_text += text
                yield _sse_event("token", {"text": text})

            tail_parts = []
            link_line = build_source_link_line(documents)
            if link_line:
                tail_parts.append(link_line)
            if LEGAL_NOTICE not in streamed_text:
                tail_parts.append(LEGAL_NOTICE)

            tail_text = ""
            if tail_parts:
                tail_text = "\n\n" + "\n\n".join(tail_parts)
                yield _sse_event("token", {"text": tail_text})

            final_state = {
                **state,
                "answer": streamed_text + tail_text,
                "guardrail_blocked": False,
                "is_fallback": False,
                "retrieved_count": len(documents),
            }
            _complete_stream_trace(trace, final_state, streamed_text + tail_text)
            yield _sse_event("done", {})
        except LLMError as exc:
            _fail_stream_trace(trace, state, exc)
            yield _sse_event("error", {"message": str(exc)})


def _initial_state(request: ChatRequest) -> AgentState:
    return {
        "message": request.message,
        "thread_id": request.thread_id,
        "category": "기타",
        "documents": [],
        "guardrail_blocked": False,
        "is_fallback": False,
        "retrieved_count": 0,
    }


def _complete_stream_trace(trace, state: AgentState, answer: str) -> None:
    response_type = response_type_from_state(state)
    add_trace_attributes(
        trace_name=STREAM_TRACE_NAME,
        tags=trace_tags("stream", response_type),
    )
    trace.update(
        output={
            "response_type": response_type,
            "answer": answer,
        },
        metadata=build_trace_metadata(
            endpoint=STREAM_ENDPOINT,
            mode="stream",
            guardrail_result=guardrail_result_from_state(state),
            retrieved_count=state.get("retrieved_count", 0),
            response_type=response_type,
            success=True,
        ),
    )


def _fail_stream_trace(trace, state: AgentState, exc: LLMError) -> None:
    add_trace_attributes(
        trace_name=STREAM_TRACE_NAME,
        tags=trace_tags("stream", "error"),
    )
    trace.update(
        output={"response_type": "error"},
        metadata=build_trace_metadata(
            endpoint=STREAM_ENDPOINT,
            mode="stream",
            guardrail_result=guardrail_result_from_state(state),
            retrieved_count=state.get("retrieved_count", 0),
            response_type="error",
            success=False,
            error_type=type(exc).__name__,
        ),
        level="ERROR",
        status_message=str(exc),
    )


def _sse_event(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
