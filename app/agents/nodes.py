from pathlib import Path
from typing import Any, Dict, Optional, TypedDict, Union

from loguru import logger

from app.core.llm import generate_text
from app.schemas.document import RetrievedDocument


BLOCKED_ANSWER = (
    "이 서비스는 법제처 생활법령 백문백답을 바탕으로 일반 정보를 안내하는 서비스입니다.\n"
    "개별 사건의 승소 가능성 판단, 법률문서 작성, 구체적 법률 자문은 제공하지 않습니다.\n"
    "필요한 경우 대한법률구조공단 등 전문기관 상담을 이용해 주세요."
)

FALLBACK_ANSWER = "관련 정보를 충분히 찾지 못했습니다. 질문을 조금 더 구체적으로 입력해 주세요."
LEGAL_NOTICE = "이 답변은 일반 정보 제공이며 법률 자문이 아닙니다."
GENERATION_SYSTEM_PROMPT = (
    "너는 법제처 생활법령 백문백답 기반 생활법률 안내 챗봇이다.\n"
    "규칙:\n"
    "- 제공된 근거 안에서만 답변한다.\n"
    "- 근거에 없는 내용은 단정하지 말고 \"확인 불가\" 또는 \"전문기관 상담 권장\"으로 처리한다.\n"
    "- 사용자의 상황을 먼저 짧게 정리한다.\n"
    "- 관련 제도/권리를 쉬운 말로 설명한다.\n"
    "- 다음 행동을 안내한다.\n"
    "- 법률 용어는 한 줄 풀이를 덧붙인다.\n"
    "- 강한 지시보다 안내형 표현을 사용한다."
)
# 고지문은 LLM에게 시키지 않고 코드가 부착한다 —
# sync는 output_guardrail, stream은 chat.py의 tail 전송이 담당한다.
# (본문 → 원문 링크 → 고지문 순서를 두 경로에서 동일하게 보장하기 위함)

SOURCE_LINK_TEMPLATE = "더 도움이 필요하시면 {url} 에서 추가 정보를 확인할 수 있습니다."

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

    answer = generate_text(
        prompt=_build_generation_prompt(state.get("message", ""), documents),
        system=GENERATION_SYSTEM_PROMPT,
    )

    return {
        **state,
        "answer": answer,
        "category": documents[0].category,
        "guardrail_blocked": False,
        "is_fallback": False,
        "retrieved_count": len(documents),
    }


def build_source_link_line(documents: list[RetrievedDocument]) -> Optional[str]:
    """검색 top-1 문서의 원문 링크 문구를 만든다. sync/stream 공용 (문구 단일 정의).

    링크를 얻지 못하는 모든 경우(문서 없음, source_url 없음, 저장소 예외)에
    None을 반환해 답변 반환을 막지 않는다. 예외는 warning 로그만 남긴다.
    """
    if not documents:
        return None
    try:
        from app.repositories.chroma_law_repository import get_source_url

        url = get_source_url(documents[0].id)
    except Exception as exc:
        logger.warning("원문 링크 조회 실패 — 링크 없이 답변을 반환한다: {}", exc)
        return None
    if not url:
        return None
    return SOURCE_LINK_TEMPLATE.format(url=url)


def output_guardrail(state: AgentState) -> AgentState:
    if state.get("guardrail_blocked") or state.get("is_fallback"):
        return state

    answer = state.get("answer", "").strip()
    # 본문 → 링크 → 고지문 순서를 보장하기 위해, LLM이 임의로 넣은 고지문은
    # 떼어낸 뒤 마지막에 다시 부착한다.
    if LEGAL_NOTICE in answer:
        answer = answer.replace(LEGAL_NOTICE, "").strip()

    parts = [answer]
    link_line = build_source_link_line(state.get("documents", []))
    if link_line:
        parts.append(link_line)
    parts.append(LEGAL_NOTICE)

    return {
        **state,
        "answer": "\n\n".join(parts),
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
    repositories_dir = Path(__file__).resolve().parents[1] / "repositories"

    chroma_repository_path = repositories_dir / "chroma_law_repository.py"
    if chroma_repository_path.exists():
        from app.repositories.chroma_law_repository import search_law_qa

        return [_coerce_document(document) for document in search_law_qa(query)]

    mock_repository_path = repositories_dir / "mock_law_repository.py"
    if not mock_repository_path.exists():
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


def _build_generation_prompt(message: str, documents: list[RetrievedDocument]) -> str:
    evidence = "\n\n".join(
        (
            f"{index}. 분야: {document.category}\n"
            f"   질문: {document.question}\n"
            f"   답변: {document.answer}"
        )
        for index, document in enumerate(documents, start=1)
    )

    return (
        "[사용자 질문]\n"
        f"{message}\n\n"
        "[검색된 근거]\n"
        f"{evidence}\n\n"
        "[답변 형식]\n"
        "1. 상황 정리\n"
        "2. 관련 제도/권리\n"
        "3. 다음 행동\n"
        "4. 일반 정보 제공 고지"
    )
