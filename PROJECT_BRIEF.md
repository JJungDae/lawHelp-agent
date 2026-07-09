# PROJECT BRIEF

## 1. 프로젝트 한 줄 정의

법제처 「찾기쉬운 생활법령 백문백답」 공공데이터를 근거로, 사용자의 생활법률 질문에 단계별로 안내하는 도구 사용형 AI 에이전트를 Upstage API로 구현하고, 실제 실행 가능한 웹 서비스로 배포하는 프로젝트이다.

---

## 2. 서비스 한 줄 정의

법률 용어를 몰라도 사용자가 자기 상황을 평소 말로 질문하면, 법제처 백문백답 공공데이터를 근거로 확인해야 할 절차와 참고할 수 있는 생활법령 정보를 안내하는 생활법률 챗봇이다.

---

## 3. 핵심 문제

일반 국민은 전월세 계약, 근로 문제, 기초생활보장 같은 생활 속 법적 상황에서 어디서 무엇을 찾아야 하는지 알기 어렵다.

법령 원문은 어렵고, 인터넷 검색 결과는 광고·블로그·비공식 정보가 섞여 있어 신뢰하기 어렵다. 즉, 정보는 공개되어 있지만 정작 필요한 사람이 활용하지 못하는 접근성 격차가 핵심 문제다.

---

## 4. 대상 사용자

- 전월세 계약을 앞둔 청년·1인가구
- 임금체불, 해고 등 근로 문제를 겪는 직장인
- 기초생활보장·복지 제도 대상자
- 생활법률 정보를 빠르게 확인해야 하는 일반 국민

---

## 5. 핵심 가치

- 사용자가 정확한 법률 검색어를 몰라도 자연어로 질문할 수 있다.
- 백문백답 데이터를 기반으로 관련 가능성이 높은 정보를 쉬운 말로 정리한다.
- 법률 자문이 아니라 일반 정보 제공이라는 한계를 명확히 한다.
- 위험 요청은 Guardrail로 차단한다.

---

## 6. 최종 MVP 흐름

```text
사용자 질문 입력
→ 생활법률 범위 판단
→ ChromaDB 검색
→ Upstage Solar 근거 기반 답변 생성
→ LiteLLM Guardrail 적용
→ SSE로 Streamlit 출력
→ Docker Compose 실행
→ GCE 배포
→ GitHub Actions에서 Ruff/pytest 통과
```

---

## 7. 기술 스택

| 영역 | 기술 | 역할 |
|---|---|---|
| Agent Workflow | LangGraph | 범위 판단, 검색, 생성, 가드레일 흐름 구성 |
| LLM Gateway | LiteLLM wrapper | LLM 호출 통일, Guardrail, Retry/Fallback 확장 |
| LLM | Upstage Solar API | 답변 생성, 범위 판단 |
| Embedding | Upstage Embedding API | 백문백답 문서 벡터화 |
| Vector DB | ChromaDB | 로컬 persistent 벡터 검색 |
| Backend | FastAPI + Uvicorn | `/health`, `/chat/sync`, `/chat/stream` |
| Streaming | SSE | 실시간 응답 전송 |
| Frontend | Streamlit | 최소 채팅 UI |
| Logging | loguru | 오류 추적 |
| Container | Docker + Docker Compose | fe/api 실행 환경 통일 |
| Deploy | GCE VM | 공개 URL 배포 |
| CI/CD | GitHub Actions + Ruff + pytest | lint/test 자동 검증 |

---

## 8. 구현 우선순위

### P0: MVP 필수

- 백문백답 샘플 데이터 정리
- ChromaDB 적재 및 검색
- Upstage Solar 답변 생성
- LiteLLM wrapper 기반 Guardrail
- FastAPI sync/stream API
- SSE 스트리밍
- Streamlit UI
- Docker Compose
- GCE 배포
- GitHub Actions + Ruff + pytest

### P1: 안정화 확장

- Retry/Fallback
- LLM 실패 1회 재시도
- 검색 결과 부족 시 fallback 응답

### P2: 선택 확장

- 명확화 되묻기
- 대표 시나리오 1개에만 적용

---

## 9. Out of Scope

이번 MVP에서는 다음을 구현하지 않는다.

- 답변별 출처 인용 UI 표시
- 판례 전문 검색
- 소장, 고소장, 계약서 등 법률문서 작성
- 개별 사건의 승소 가능성 판단
- 개인정보 수집 및 저장
- 로그인/회원관리
- 장기 기억
- 대화 이력 DB 저장
- Supabase 연동
- LiteLLM Proxy/Admin UI 기반 운영

---

## 10. Definition of Done

MVP 완료 기준은 다음과 같다.

- 배포 URL에서 기본 시나리오가 끝까지 동작한다.
- Guardrail 차단 시나리오가 1회 이상 재현된다.
- 검색 결과 부족 또는 LLM 실패 상황이 오류 없이 fallback으로 처리된다.
- GitHub Actions에서 Ruff/pytest가 통과한다.
- README를 보고 제3자가 로컬 실행 흐름을 이해할 수 있다.
