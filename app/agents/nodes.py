from pathlib import Path
from typing import Any, Dict, Optional, TypedDict, Union

from app.schemas.document import RetrievedDocument


BLOCKED_ANSWER = (
    "이 서비스는 법제처 생활법령 백문백답을 바탕으로 일반 정보를 안내하는 서비스입니다.\n"
    "개별 사건의 승소 가능성 판단, 법률문서 작성, 구체적 법률 자문은 제공하지 않습니다.\n"
    "필요한 경우 대한법률구조공단 등 전문기관 상담을 이용해 주세요."
)

FALLBACK_ANSWER = "관련 정보를 충분히 찾지 못했습니다. 질문을 조금 더 구체적으로 입력해 주세요."
LEGAL_NOTICE = "이 답변은 일반 정보 제공이며 법률 자문이 아닙니다."

DANGEROUS_PHRASES = (
    "승소",
    "이길 수",
    "소장 좀 써",
    "소장 작성",
    "고소장 써",
    "고소장 작성",
    "계약서 써줘",
    "계약서 작성해줘",
    "주민등록번호",
    "계좌번호",
    "시스템 프롬프트",
    "이전 지시 무시",
    "개발자 지시",
)


class AgentState(TypedDict, total=False):
    message: str
    thread_id: Optional[str]
    category: str
    documents: list[RetrievedDocument]
    answer: str
    guardrail_blocked: bool
    is_fallback: bool
    retrieved_count: int


def scope_check(state: AgentState) -> AgentState:
    message = state.get("message", "")
    normalized_message = message.casefold()
    is_blocked = any(phrase.casefold() in normalized_message for phrase in DANGEROUS_PHRASES)

    return {
        **state,
        "guardrail_blocked": is_blocked,
        "category": "차단" if is_blocked else state.get("category", "기타"),
    }


def guardrail_exit(state: AgentState) -> AgentState:
    return {
        **state,
        "answer": BLOCKED_ANSWER,
        "category": "차단",
        "documents": [],
        "guardrail_blocked": True,
        "is_fallback": False,
        "retrieved_count": 0,
    }


def retrieve(state: AgentState) -> AgentState:
    documents = _search_law_qa(state.get("message", ""))
    category = documents[0].category if documents else "기타"

    return {
        **state,
        "documents": documents,
        "category": category,
        "retrieved_count": len(documents),
    }


def generate(state: AgentState) -> AgentState:
    documents = state.get("documents", [])
    if not documents:
        return fallback_response(state)

    primary_document = documents[0]
    answer = _build_guidance_answer(primary_document)

    return {
        **state,
        "answer": answer,
        "category": primary_document.category,
        "guardrail_blocked": False,
        "is_fallback": False,
        "retrieved_count": len(documents),
    }


def output_guardrail(state: AgentState) -> AgentState:
    if state.get("guardrail_blocked") or state.get("is_fallback"):
        return state

    answer = state.get("answer", "").strip()
    if LEGAL_NOTICE not in answer:
        answer = f"{answer}\n\n{LEGAL_NOTICE}"

    return {
        **state,
        "answer": answer,
        "guardrail_blocked": False,
        "is_fallback": False,
    }


def fallback_response(state: AgentState) -> AgentState:
    return {
        **state,
        "answer": FALLBACK_ANSWER,
        "category": "기타",
        "documents": [],
        "guardrail_blocked": False,
        "is_fallback": True,
        "retrieved_count": 0,
    }


def _search_law_qa(query: str) -> list[RetrievedDocument]:
    repository_path = Path(__file__).resolve().parents[1] / "repositories" / "mock_law_repository.py"
    if not repository_path.exists():
        return _temporary_search_law_qa(query)

    from app.repositories.mock_law_repository import search_law_qa

    return [_coerce_document(document) for document in search_law_qa(query)]


def _coerce_document(document: Union[RetrievedDocument, Dict[str, Any]]) -> RetrievedDocument:
    if isinstance(document, RetrievedDocument):
        return document
    return RetrievedDocument(**document)


def _temporary_search_law_qa(query: str) -> list[RetrievedDocument]:
    # TODO: 역할 B의 app.repositories.mock_law_repository.search_law_qa 병합 후 제거한다.
    mock_documents = [
        RetrievedDocument(
            id="rent_001",
            category="임대차",
            question="전월세 계약 전 확인할 사항은 무엇인가요?",
            answer="등기부등본 확인, 계약 당사자 확인, 전입신고와 확정일자 확인이 필요합니다.",
        ),
        RetrievedDocument(
            id="rent_002",
            category="임대차",
            question="전세 계약서에서 확인할 사항은 무엇인가요?",
            answer="임대인과 임차인 정보, 보증금과 월세, 계약 기간, 특약 사항을 확인할 수 있습니다.",
        ),
        RetrievedDocument(
            id="labor_001",
            category="근로",
            question="임금이 밀리면 어떻게 해야 하나요?",
            answer="임금체불이 발생한 경우 사업주에게 지급을 요청하고, 해결되지 않으면 고용노동부 진정 절차를 확인할 수 있습니다.",
        ),
        RetrievedDocument(
            id="welfare_001",
            category="복지",
            question="기초생활보장 급여는 어디서 확인하나요?",
            answer="주소지 관할 읍면동 주민센터 또는 복지로에서 신청 자격과 급여 종류를 확인할 수 있습니다.",
        ),
    ]

    query_keywords = _extract_query_keywords(query)
    if not query_keywords:
        return []

    scored_documents = [
        (document, _score_document(document, query_keywords)) for document in mock_documents
    ]
    return [document for document, score in scored_documents if score > 0]


def _extract_query_keywords(query: str) -> set[str]:
    normalized_query = query.casefold()
    keyword_groups = {
        "월세": "임대차",
        "전세": "임대차",
        "전월세": "임대차",
        "임대차": "임대차",
        "보증금": "임대차",
        "확정일자": "임대차",
        "계약 전": "임대차",
        "계약서": "임대차",
        "임금": "근로",
        "월급": "근로",
        "체불": "근로",
        "노동청": "근로",
        "근로": "근로",
        "해고": "근로",
        "기초생활": "복지",
        "복지": "복지",
        "급여": "복지",
    }

    return {category for keyword, category in keyword_groups.items() if keyword in normalized_query}


def _score_document(document: RetrievedDocument, query_keywords: set[str]) -> int:
    score = 0
    if document.category in query_keywords:
        score += 2

    text = f"{document.question} {document.answer}".casefold()
    score += sum(1 for keyword in query_keywords if keyword in text)
    return score


def _build_guidance_answer(document: RetrievedDocument) -> str:
    softened_answer = _soften_answer(document.answer)
    return f"{document.category} 관련해서는 아래 내용을 확인해 보세요.\n{softened_answer}"


def _soften_answer(answer: str) -> str:
    softened = answer.strip()
    if softened.endswith("."):
        softened = softened[:-1]

    replacements = {
        "확인이 필요합니다": "확인해 보시는 것이 좋습니다",
        "필요합니다": "확인해 보시는 것이 좋습니다",
        "해야 합니다": "확인해 보시는 것이 좋습니다",
    }
    for original, replacement in replacements.items():
        softened = softened.replace(original, replacement)

    return f"{softened}."
