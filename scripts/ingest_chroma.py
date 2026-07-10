"""data/mock_law_qa.json을 ChromaDB에 적재하는 스크립트.

- 임베딩: Upstage Embedding API (문서는 embedding-passage 모델, HTTP 직접 호출)
  ※ LLM wrapper 경유 규칙은 Solar 생성 호출 대상이므로, 적재용 임베딩 호출은
    이 스크립트 안의 함수로 분리한다 (파트B_DAY3_작업지시 4절).
- 저장소: chromadb.PersistentClient(path="chroma_db/"), 컬렉션명 law_qa
- 거리 공간: cosine (distance = 1 - cosine 유사도, 0에 가까울수록 유사)
- 청크 규칙: 1문답 = 1청크, 임베딩 텍스트는 question + "\n" + answer
- metadata: id, category, question 유지
- 재실행 가능: 기존 컬렉션을 삭제 후 재생성하므로 중복 적재가 없다.

실행: python scripts/ingest_chroma.py  (사전 조건: .env에 UPSTAGE_API_KEY)
"""

import json
import sys
from pathlib import Path

import chromadb
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402

DATA_PATH = PROJECT_ROOT / "data" / "mock_law_qa.json"
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "law_qa"
EMBEDDING_URL = "https://api.upstage.ai/v1/embeddings"
EMBEDDING_MODEL = "embedding-passage"  # 문서 적재용. 검색 질의는 embedding-query 사용


def load_data(path: Path) -> list[dict]:
    """백문백답 JSON을 읽어 문서 dict 리스트로 반환한다."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_documents(items: list[dict]) -> tuple[list[str], list[str], list[dict]]:
    """문서 리스트를 ChromaDB 적재 형식(ids, documents, metadatas)으로 변환한다."""
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    for item in items:
        ids.append(item["id"])
        documents.append(f"{item['question']}\n{item['answer']}")
        metadatas.append(
            {"id": item["id"], "category": item["category"], "question": item["question"]}
        )
    return ids, documents, metadatas


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Upstage Embedding API로 텍스트 목록을 벡터화한다."""
    response = requests.post(
        EMBEDDING_URL,
        headers={"Authorization": f"Bearer {settings.upstage_api_key}"},
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=60,
    )
    response.raise_for_status()
    data = sorted(response.json()["data"], key=lambda entry: entry["index"])
    return [entry["embedding"] for entry in data]


def main() -> None:
    if not settings.upstage_api_key:
        raise SystemExit("UPSTAGE_API_KEY가 비어 있습니다. .env 설정 후 다시 실행하세요.")

    items = load_data(DATA_PATH)
    ids, documents, metadatas = build_documents(items)
    embeddings = embed_texts(documents)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:  # 컬렉션이 아직 없는 첫 실행이면 그대로 진행
        pass
    collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    print(f"{collection.count()}건 적재 완료")


if __name__ == "__main__":
    main()
