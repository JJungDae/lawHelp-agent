# DAY2 MVP PLAN

## 1. Day2 목표

마일스톤 기준 목표는 다음과 같다.

```text
에이전트 백엔드 MVP 구현 (1)
Tool Schema · ReAct Loop
Mock으로 1개 시나리오 성공
```

우리 프로젝트 기준으로 바꾸면 다음과 같다.

```text
Mock 데이터 기반으로
사용자 질문 → 범위 판단 → 검색 Tool 호출 → 답변 생성
흐름을 1회 성공시킨다.
```

Day2의 핵심은 검색 품질이나 UI 완성도가 아니라, Agent backend의 전체 흐름을 얇게 관통시키는 것이다.

---

## 2. Day2 완료 기준

아래 항목이 끝나면 Day2 목표를 달성한 것으로 본다.

- 프로젝트 폴더 구조 생성
- Pydantic Schema 정의
- Mock 백문백답 데이터 준비
- Mock 검색 함수 구현
- Agent flow 구현
- `/chat/sync` endpoint 구현
- curl 또는 Swagger에서 1개 시나리오 성공
- 각자 수정한 파일과 연결 흐름 설명 가능

---

## 3. 오늘 만들 최소 흐름

```text
POST /chat/sync
→ ChatRequest 검증
→ scope_check
→ retrieve mock documents
→ generate mock answer
→ output_guardrail
→ ChatResponse 반환
```

---

## 4. 추천 폴더 구조

```text
app/
  api/
    chat.py
  agents/
    workflow.py
    nodes.py
  core/
    config.py
    llm.py
  repositories/
    mock_law_repository.py
  schemas/
    chat.py
    document.py
data/
  mock_law_qa.json
scripts/
frontend/
tests/
docs/
```

처음부터 완벽한 구조를 만들 필요는 없다. 다만 책임별 폴더는 나누어 둔다.

---

## 5. Step 1: Schema 정의

최소 스키마만 먼저 만든다.

```python
class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
```

```python
class RetrievedDocument(BaseModel):
    id: str
    question: str
    answer: str
    category: str
```

```python
class ChatResponse(BaseModel):
    answer: str
    category: str
    guardrail_blocked: bool = False
```

스키마는 API, Agent, 검색 함수 사이의 계약이므로 함께 확인한다.

---

## 6. Step 2: Mock 데이터 준비

Day2에서는 실제 ChromaDB가 없어도 된다. 먼저 mock 데이터로 흐름을 성공시킨다.

예시:

```json
[
  {
    "id": "rent_001",
    "category": "임대차",
    "question": "전월세 계약 전 확인할 사항은 무엇인가요?",
    "answer": "등기부등본 확인, 계약 당사자 확인, 전입신고와 확정일자 확인이 필요합니다."
  },
  {
    "id": "labor_001",
    "category": "근로",
    "question": "임금이 밀리면 어떻게 해야 하나요?",
    "answer": "임금체불이 발생한 경우 사업주에게 지급을 요청하고, 해결되지 않으면 고용노동부 진정 절차를 확인할 수 있습니다."
  }
]
```

---

## 7. Step 3: Mock 검색 함수 구현

처음에는 ChromaDB 없이 keyword 기반으로 구현해도 된다.

```python
def search_law_qa(query: str) -> list[RetrievedDocument]:
    ...
```

목표는 검색 품질이 아니라 “검색 Tool이 호출되고 문서가 반환되는 흐름”을 확인하는 것이다.

---

## 8. Step 4: Agent Flow 구현

Day2의 최소 Agent flow는 다음과 같다.

```text
scope_check
→ retrieve
→ generate
→ output_guardrail
```

각 노드의 역할은 다음과 같다.

| 노드 | 역할 |
|---|---|
| `scope_check` | 생활법률 범위인지 간단히 판단 |
| `retrieve` | mock search tool 호출 |
| `generate` | 검색 결과로 mock 답변 생성 |
| `output_guardrail` | 법률 자문 아님 고지 부착 |

Day2에서는 실제 LLM이 없어도 된다. Mock 답변으로 흐름을 먼저 성공시킨다.

---

## 9. Step 5: FastAPI `/chat/sync` 구현

요청 예시:

```http
POST /chat/sync
Content-Type: application/json

{
  "message": "월세 계약 전에 뭘 확인해야 하나요?"
}
```

응답 예시:

```json
{
  "answer": "월세 계약 전에는 등기부등본, 계약 당사자, 전입신고와 확정일자를 확인해 보세요. 이 답변은 일반 정보 제공이며 법률 자문이 아닙니다.",
  "category": "임대차",
  "guardrail_blocked": false
}
```

---

## 10. Step 6: 테스트 방법

### FastAPI 실행

```bash
uvicorn app.main:app --reload
```

### health 확인

```bash
curl http://localhost:8000/health
```

### chat sync 확인

```bash
curl -X POST http://localhost:8000/chat/sync \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"월세 계약 전에 뭘 확인해야 하나요?\"}"
```

---

## 11. Day2 역할 분배 기준

개인 이름을 고정하기보다, 충돌이 적은 작업 단위로 나눈다.

### 파트 A: API / Agent 흐름

담당 내용:

```text
- ChatRequest / ChatResponse schema
- /chat/sync endpoint
- scope_check
- generate mock answer
```

관련 파일:

```text
app/api/
app/agents/
app/schemas/
```

### 파트 B: 데이터 / 검색 흐름

담당 내용:

```text
- Mock 백문백답 데이터 작성
- search_law_qa 함수
- ChromaDB 적재 준비
```

관련 파일:

```text
data/
scripts/
app/repositories/
```

### 같이 봐야 하는 파트

```text
app/schemas/
README.md
.env.example
```

스키마는 API와 검색 사이의 계약이므로 반드시 함께 정한다.

---

## 12. 15~16시 통합 시간에 할 일

각자 개발한 내용을 바로 merge하지 않고, 먼저 설명한다.

```text
1. 어떤 파일을 수정했는가?
2. 이 코드는 어떤 입력을 받는가?
3. 이 코드는 어떤 출력을 만드는가?
4. 다른 파일과 어디에서 연결되는가?
```

그 다음 통합한다.

통합 후에는 반드시 `/chat/sync`를 실행해 1개 시나리오가 끝까지 성공하는지 확인한다.

---

## 13. Day3 확장 방향

Day2에서 Mock 흐름이 성공했다면, Day3에서는 아래 순서로 확장한다.

```text
Mock search
→ ChromaDB 실제 검색

Mock generate
→ LiteLLM wrapper
→ Upstage Solar 호출

/chat/sync
→ /chat/stream SSE
```

Day3 목표는 다음과 같다.

```text
SSE 스트리밍 + 실제 LLM 연동 + 실패 케이스 1개 처리
```

---

## 14. Day3 실패 케이스 추천

우선 하나만 구현한다.

추천 실패 케이스:

```text
검색 결과 부족
→ “관련 정보를 충분히 찾지 못했습니다. 질문을 조금 더 구체적으로 입력해 주세요.”
```

LLM timeout이나 rate limit은 재현이 번거로울 수 있으므로, 첫 실패 케이스는 검색 결과 부족으로 잡는 것이 좋다.

---

## 15. 내일 작업 원칙

```text
오늘은 Mock으로 흐름을 성공시키는 날이다.
실제 LLM, 실제 ChromaDB, SSE, Docker는 Day2 흐름이 성공한 뒤 붙인다.
설명할 수 없는 코드는 merge하지 않는다.
기능을 많이 만들기보다 하나의 질문이 끝까지 지나가게 만든다.
```
