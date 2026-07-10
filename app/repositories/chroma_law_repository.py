"""ChromaDB 기반 백문백답 검색 저장소 (파트B Day3).

파트 A의 nodes.py chroma 분기가 이 모듈의 search_law_qa를 호출한다(존재 기반 선택).
계약은 mock_law_repository와 동일하며 저장소는 문서 반환만 한다.

조용한 fallback 방지 규칙 (파트B_DAY3_작업지시 3절):
- import 시점에는 어떤 I/O도 하지 않는다 (지연 초기화).
- 저장소 미준비(chroma_db/ 없음, 컬렉션 없음/비어 있음, API 키 없음)는
  호출 시점에 RuntimeError를 올린다.
- "검색 결과 없음"(임계값 필터 후 0건)은 빈 리스트. 예외와 절대 섞지 않는다.
"""

from pathlib import Path

import chromadb
import requests

from app.core.config import settings
from app.schemas.document import RetrievedDocument

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "law_qa"
EMBEDDING_URL = "https://api.upstage.ai/v1/embeddings"
EMBEDDING_MODEL = "embedding-query"  # 적재(embedding-passage)와 쌍을 이루는 질의용 모델

# 검색 부족 판정 임계값 (cosine distance, 팀 승인 2026-07-10)
# 근거: scripts/check_search.py 20건 기준 — 관련 매칭 0.47~0.53, 무관 최근접 0.75.
# 두 분포의 중간값으로 양쪽에 ~0.1 여유. 전량(~1,200건) 적재 후 재점검 필요.
SCORE_THRESHOLD = 0.65

_INGEST_GUIDE = "scripts/ingest_chroma.py를 먼저 실행하세요."

_collection = None  # 첫 호출 시 초기화 후 재사용


def _get_collection():
    """law_qa 컬렉션을 지연 초기화로 얻는다. 미준비 상태면 RuntimeError."""
    global _collection
    if _collection is not None:
        return _collection

    if not CHROMA_PATH.exists():
        raise RuntimeError(f"chroma_db/가 없습니다. {_INGEST_GUIDE}")

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(f"{COLLECTION_NAME} 컬렉션이 없습니다. {_INGEST_GUIDE}") from exc
    if collection.count() == 0:
        raise RuntimeError(f"{COLLECTION_NAME} 컬렉션이 비어 있습니다. {_INGEST_GUIDE}")

    _collection = collection
    return collection


def _embed_query(text: str) -> list[float]:
    """질문을 Upstage Embedding API로 벡터화한다."""
    if not settings.upstage_api_key:
        raise RuntimeError("UPSTAGE_API_KEY가 비어 있습니다. .env를 설정하세요.")
    response = requests.post(
        EMBEDDING_URL,
        headers={"Authorization": f"Bearer {settings.upstage_api_key}"},
        json={"model": EMBEDDING_MODEL, "input": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def search_law_qa(query: str, top_k: int = 3) -> list[RetrievedDocument]:
    """ChromaDB 벡터 검색.

    - query를 임베딩해 law_qa 컬렉션에서 top_k 검색한다.
    - distance가 SCORE_THRESHOLD를 초과하는 문서는 제외한다.
    - 남는 문서가 없으면 빈 리스트를 반환한다 (예외 금지).
    - metadata + document 본문으로 RetrievedDocument를 복원해 반환한다.
    """
    collection = _get_collection()
    result = collection.query(
        query_embeddings=[_embed_query(query)],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    retrieved: list[RetrievedDocument] = []
    for text, metadata, distance in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        if distance > SCORE_THRESHOLD:
            continue
        # 적재 형식이 question + "\n" + answer 이므로 첫 줄 이후가 answer다
        answer = text.split("\n", 1)[1] if "\n" in text else text
        retrieved.append(
            RetrievedDocument(
                id=metadata["id"],
                question=metadata["question"],
                answer=answer,
                category=metadata["category"],
            )
        )
    return retrieved
