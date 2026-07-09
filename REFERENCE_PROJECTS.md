# REFERENCE PROJECTS

## 1. 문서 목적

이 문서는 기존 실습 프로젝트와 교육 제공 Medical QA Agent 프로젝트를 이번 생활법령 RAG Agent 구현에 어떻게 참고할지 정리한 문서이다.

참고 프로젝트는 그대로 복사하는 대상이 아니라, 구조와 흐름을 이해하고 우리 프로젝트에 맞게 변환하기 위한 레퍼런스이다.

---

## 2. 참고 프로젝트 1: lumi-server

### 활용 목적

이전 실습을 통해 만든 프로젝트로, FastAPI, SSE, Docker, GitHub Actions 등 배포형 백엔드 흐름을 참고한다.

### 참고할 부분

- FastAPI 앱 구성 방식
- API router 구조
- SSE 스트리밍 처리 방식
- 환경변수 관리 방식
- Docker / Docker Compose 구성
- GitHub Actions 기반 lint/test 구조
- 이전 실습에서 검증한 실행 명령어와 배포 흐름

### 주의할 부분

- 도메인 로직은 생활법령 RAG에 맞게 교체한다.
- Supabase 관련 코드가 있다면 이번 MVP에서는 사용하지 않는다.
- 불필요한 인증, 세션, 부가 기능은 가져오지 않는다.
- “작동했던 코드”라도 현재 MVP 범위와 맞지 않으면 제외한다.

---

## 3. 참고 프로젝트 2: Medical QA Agent

### 프로젝트 성격

교육 자료로 제공된 의료 QA용 RAG 챗봇 프로젝트이다.

구조는 다음과 같다.

```text
FastAPI 백엔드
+ LangGraph 에이전트 흐름
+ ChromaDB 벡터 검색
+ Streamlit 프론트엔드
+ Docker Compose
```

이번 생활법령 RAG Agent와 구조가 매우 유사하므로 핵심 레퍼런스로 활용한다.

---

## 4. Medical QA Agent 주요 파일과 참고 내용

| 파일 | 참고할 내용 |
|---|---|
| `app/main.py` | FastAPI 앱 진입점, CORS, health, router 등록 |
| `app/api.py` | `/api/v1/chat/sync`, SSE 채팅 API 구조 |
| `app/graph.py` | LangGraph workflow 정의 방식 |
| `app/agents/query_analyzer.py` | 질문 분석 및 도메인 분류 |
| `app/agents/retrieval.py` | ChromaDB 검색 노드 |
| `app/agents/responder.py` | 최종 답변 생성 노드 |
| `app/core/` | 설정, LLM, embedding, Chroma client |
| `app/vector_store.py` | JSON 데이터를 ChromaDB에 적재하고 검색하는 구조 |
| `frontend/ui.py` | Streamlit 채팅 UI |
| `Dockerfile.api` | API 컨테이너 빌드 |
| `Dockerfile.frontend` | Streamlit 컨테이너 빌드 |
| `docker-compose.yml` | API/FE 컨테이너 실행 구성 |

---

## 5. Medical QA Agent 흐름 요약

```text
사용자가 Streamlit UI에 질문 입력
→ 프론트가 FastAPI `/chat/sync` 또는 SSE endpoint 호출
→ API가 LangGraph 초기 상태 생성
→ analyze 노드에서 질문 분석
→ retrieve 노드에서 ChromaDB 벡터 검색
→ respond 노드에서 답변 생성
→ 최종 답변을 프론트에 표시
```

---

## 6. 우리 프로젝트로 변환할 때의 대응 관계

| Medical QA Agent | 생활법령 RAG Agent |
|---|---|
| 의료 질문 | 생활법률 질문 |
| medical/general/out_of_scope | in_scope/out_of_scope 또는 law/general |
| 의료 지식 JSON | 백문백답 JSON/CSV |
| 의료 면책 문구 | 법률 자문 아님 고지 |
| Medical Consultant | 생활법률 안내 Agent |
| Chroma medical collection | Chroma law_qa collection |
| 의료 안전 가드레일 | 법률 자문·소장 작성·개인정보·인젝션 차단 |
| ChromaDB 검색 | ChromaDB 백문백답 검색 |
| Streamlit 의료 QA UI | Streamlit 생활법률 챗봇 UI |

---

## 7. 그대로 가져오면 안 되는 부분

- 의료 도메인 프롬프트
- 의료 면책 문구
- 의료 질문 분류 기준
- 의료 지식 데이터
- 의료용 테스트 질문
- 현재 프로젝트의 MVP 범위를 벗어나는 기능

---

## 8. 이번 프로젝트에 맞게 새로 정의해야 하는 부분

- 생활법률 범위 판단 기준
- 법률 자문 아님 고지 문구
- 백문백답 데이터 스키마
- ChromaDB collection 이름
- Guardrail 차단 대상
- 검색 결과 부족 시 fallback 문구
- Streamlit 화면 안내 문구
- README와 발표자료의 데이터 출처 설명

---

## 9. 에이전트에게 레퍼런스를 줄 때의 원칙

로컬 코딩 에이전트에게 참고 프로젝트를 제공할 때는 반드시 다음처럼 지시한다.

```text
이 프로젝트를 그대로 복사하지 말고 구조만 참고해줘.
의료 도메인 코드는 생활법령 RAG 도메인에 맞게 바꿔줘.
Supabase, 로그인, 장기 기억, 출처 표시 UI는 구현하지 마.
현재 MVP는 ChromaDB 기반 RAG + LiteLLM wrapper + Guardrail + SSE + Docker/GCE 배포야.
```

---

## 10. 추천 분석 순서

로컬 에이전트에게 참고 프로젝트를 분석시킬 때는 아래 순서로 요청한다.

1. 폴더 구조 요약
2. 실행 흐름 요약
3. FastAPI endpoint 구조 확인
4. LangGraph node 흐름 확인
5. ChromaDB 적재/검색 코드 확인
6. Streamlit UI 호출 방식 확인
7. Docker Compose 구조 확인
8. 우리 프로젝트에 재사용 가능한 파일/패턴만 추출

---

## 11. 최종 활용 기준

참고 프로젝트에서 가져올 것은 “코드 전체”가 아니라 “구조와 연결 방식”이다.

특히 다음 네 가지를 우선 참고한다.

```text
1. FastAPI와 Streamlit의 연결 방식
2. LangGraph에서 analyze → retrieve → respond로 이어지는 흐름
3. ChromaDB 적재 및 검색 방식
4. Docker Compose에서 API/FE를 분리 실행하는 방식
```
