"""ChromaDB 적재 스크립트 — Day3 구현 예정 스켈레톤.

Day2에서는 구조만 정의한다. chromadb를 import하지 않는다.

Day3 구현 방향 (기획서 기준):
- 임베딩: Upstage Embedding API
- 저장소: 컨테이너 내부 ChromaDB PersistentClient
- 청킹: 1문답 = 1청크
- metadata: id, category, question 유지 (공통_작업지시 8절)
- collection 이름: law_qa (예정)

실행 예정 명령: python scripts/ingest_chroma.py
"""


def load_data(path: str) -> list[dict]:
    """JSON 파일(Day2: data/mock_law_qa.json, Day3~4: 백문백답 전량)을 읽어
    문서 dict 리스트로 반환한다."""
    raise NotImplementedError("Day3에서 구현")


def build_documents(items: list[dict]) -> tuple[list[str], list[str], list[dict]]:
    """문서 리스트를 ChromaDB 적재 형식으로 변환한다.

    1문답 = 1청크. 반환값:
    - ids: 문서 id 리스트
    - documents: 임베딩 대상 텍스트(question + answer) 리스트
    - metadatas: {"id", "category", "question"} dict 리스트
    """
    raise NotImplementedError("Day3에서 구현")


def main() -> None:
    """Day3에서 구현:
    1. load_data()로 문서 로드
    2. build_documents()로 적재 형식 변환
    3. chromadb.PersistentClient(path=...)로 연결
    4. Upstage Embedding API로 임베딩 후 law_qa collection에 적재
    """
    raise NotImplementedError("Day3에서 구현")


if __name__ == "__main__":
    main()
