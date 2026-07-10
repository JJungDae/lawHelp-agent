"""top-k 검색 단독 확인 스크립트 (파트B Day3 작업 2).

data/test_questions.json의 normal + no_result 질문으로 law_qa 컬렉션을
top-3 검색해 질문별 매칭 문서 id와 distance를 출력하고,
검색 부족 판정 임계값 제안의 근거가 되는 스코어 분포 요약을 낸다.

거리 공간은 cosine distance(0에 가까울수록 유사, ingest_chroma.py에서 설정).

실행: python scripts/check_search.py  (사전 조건: scripts/ingest_chroma.py 적재 완료)
"""

import json
import sys
from pathlib import Path

import chromadb
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402

QUESTIONS_PATH = PROJECT_ROOT / "data" / "test_questions.json"
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "law_qa"
EMBEDDING_URL = "https://api.upstage.ai/v1/embeddings"
EMBEDDING_MODEL = "embedding-query"  # 검색 질의용 모델 (적재는 embedding-passage)
TOP_K = 3

# normal 질문별로 "관련 문서"로 인정할 id 접두어 (관련/무관 스코어 분리 기준)
EXPECTED_PREFIX = {
    "월세 계약 전에 뭘 확인해야 하나요?": "rent",
    "임금이 두 달째 밀렸는데 어떻게 하죠?": "labor",
    "보증금은 어떻게 보호받을 수 있나요?": "rent",
}


def embed_query(text: str) -> list[float]:
    response = requests.post(
        EMBEDDING_URL,
        headers={"Authorization": f"Bearer {settings.upstage_api_key}"},
        json={"model": EMBEDDING_MODEL, "input": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def search(collection, question: str) -> list[tuple[str, float]]:
    result = collection.query(query_embeddings=[embed_query(question)], n_results=TOP_K)
    return list(zip(result["ids"][0], result["distances"][0]))


def main() -> None:
    if not settings.upstage_api_key:
        raise SystemExit("UPSTAGE_API_KEY가 비어 있습니다. .env 설정 후 다시 실행하세요.")

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as exc:
        raise SystemExit(f"law_qa 컬렉션이 없습니다. scripts/ingest_chroma.py를 먼저 실행하세요. ({exc})")

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    relevant_best: list[float] = []  # normal 질문에서 관련 문서의 최고(최소) distance
    hit_count = 0
    for question in questions["normal"]:
        matches = search(collection, question)
        print(f"\n[normal] {question}")
        for doc_id, distance in matches:
            print(f"  {doc_id}: {distance:.4f}")
        prefix = EXPECTED_PREFIX.get(question)
        related = [d for doc_id, d in matches if prefix and doc_id.startswith(prefix)]
        if related:
            hit_count += 1
            relevant_best.append(min(related))
        else:
            print("  !! 관련 문서가 top-3에 없음")

    irrelevant_best: list[float] = []  # no_result 질문에서 가장 가까운 문서의 distance
    for question in questions["no_result"]:
        matches = search(collection, question)
        print(f"\n[no_result] {question}")
        for doc_id, distance in matches:
            print(f"  {doc_id}: {distance:.4f}")
        irrelevant_best.append(min(distance for _, distance in matches))

    total = len(questions["normal"])
    print("\n===== 요약 =====")
    print(f"normal 질문 top-3 적중률: {hit_count}/{total}")
    if relevant_best:
        print(f"관련 매칭 distance 범위: {min(relevant_best):.4f} ~ {max(relevant_best):.4f}")
    if irrelevant_best:
        print(f"무관 질문 최근접 distance 범위: {min(irrelevant_best):.4f} ~ {max(irrelevant_best):.4f}")
    print("※ 임계값은 위 두 분포 사이에서 제안하고 승인 후 확정한다 (작업지시 5절).")


if __name__ == "__main__":
    main()
