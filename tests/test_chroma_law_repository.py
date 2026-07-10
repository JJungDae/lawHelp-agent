"""chroma_law_repository 테스트 (파트B Day3).

chroma_db/ 적재본과 Upstage API 키가 있는 환경에서만 실행된다.
없는 환경(CI 등)에서는 전체 skip 처리한다.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.repositories.chroma_law_repository import search_law_qa  # noqa: E402
from app.schemas.document import RetrievedDocument  # noqa: E402

CHROMA_READY = (PROJECT_ROOT / "chroma_db").exists() and bool(settings.upstage_api_key)

pytestmark = pytest.mark.skipif(
    not CHROMA_READY,
    reason="chroma_db/ 또는 UPSTAGE_API_KEY 없음 — scripts/ingest_chroma.py와 .env를 먼저 준비",
)


def test_search_normal_question_returns_retrieved_documents():
    results = search_law_qa("월세 계약 전에 뭘 확인해야 하나요?")
    assert len(results) >= 1
    assert all(isinstance(document, RetrievedDocument) for document in results)
    assert any(document.id.startswith("rent_") for document in results)


def test_search_no_result_question_returns_empty_list_without_error():
    results = search_law_qa("상속 포기 절차가 궁금해요")
    assert results == []


def test_search_top_k_limits_result_count():
    results = search_law_qa("월세 계약 전에 뭘 확인해야 하나요?", top_k=1)
    assert len(results) <= 1
