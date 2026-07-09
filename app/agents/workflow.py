from typing import Any, Optional

from app.agents.nodes import (
    AgentState,
    fallback_response,
    generate,
    guardrail_exit,
    output_guardrail,
    retrieve,
    scope_check,
)
from app.schemas.chat import ChatResponse


_COMPILED_WORKFLOW: Optional[Any] = None


def run_chat_workflow(message: str, thread_id: Optional[str] = None) -> ChatResponse:
    initial_state: AgentState = {
        "message": message,
        "thread_id": thread_id,
        "category": "기타",
        "documents": [],
        "guardrail_blocked": False,
        "is_fallback": False,
        "retrieved_count": 0,
    }

    workflow = _get_compiled_workflow()
    if workflow is None:
        final_state = _run_function_chain(initial_state)
    else:
        final_state = workflow.invoke(initial_state)

    return _to_chat_response(final_state)


def _get_compiled_workflow() -> Optional[Any]:
    global _COMPILED_WORKFLOW
    if _COMPILED_WORKFLOW is not None:
        return _COMPILED_WORKFLOW

    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError:
        return None

    graph = StateGraph(AgentState)
    graph.add_node("scope_check", scope_check)
    graph.add_node("guardrail_exit", guardrail_exit)
    graph.add_node("retrieve", retrieve)
    graph.add_node("fallback_response", fallback_response)
    graph.add_node("generate", generate)
    graph.add_node("output_guardrail", output_guardrail)

    graph.set_entry_point("scope_check")
    graph.add_conditional_edges(
        "scope_check",
        _route_after_scope_check,
        {
            "blocked": "guardrail_exit",
            "passed": "retrieve",
        },
    )
    graph.add_conditional_edges(
        "retrieve",
        _route_after_retrieve,
        {
            "found": "generate",
            "no_result": "fallback_response",
        },
    )
    graph.add_edge("generate", "output_guardrail")
    graph.add_edge("guardrail_exit", END)
    graph.add_edge("fallback_response", END)
    graph.add_edge("output_guardrail", END)

    _COMPILED_WORKFLOW = graph.compile()
    return _COMPILED_WORKFLOW


def _run_function_chain(state: AgentState) -> AgentState:
    state = scope_check(state)
    if state.get("guardrail_blocked"):
        return guardrail_exit(state)

    state = retrieve(state)
    if state.get("retrieved_count", 0) == 0:
        return fallback_response(state)

    state = generate(state)
    return output_guardrail(state)


def _route_after_scope_check(state: AgentState) -> str:
    return "blocked" if state.get("guardrail_blocked") else "passed"


def _route_after_retrieve(state: AgentState) -> str:
    return "found" if state.get("retrieved_count", 0) > 0 else "no_result"


def _to_chat_response(state: AgentState) -> ChatResponse:
    return ChatResponse(
        answer=state.get("answer", ""),
        category=state.get("category", "기타"),
        guardrail_blocked=state.get("guardrail_blocked", False),
        is_fallback=state.get("is_fallback", False),
        retrieved_count=state.get("retrieved_count", 0),
    )
