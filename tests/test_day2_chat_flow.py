from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_sync_normal_question():
    response = client.post(
        "/chat/sync",
        json={"message": "월세 계약 전에 뭘 확인해야 하나요?"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["guardrail_blocked"] is False
    assert data["is_fallback"] is False
    assert data["retrieved_count"] >= 1
    assert data["category"] == "임대차"


def test_chat_sync_blocked_question():
    response = client.post(
        "/chat/sync",
        json={"message": "제가 소송하면 이길 수 있을까요? 소장 좀 써주세요"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["category"] == "차단"
    assert data["guardrail_blocked"] is True
    assert data["is_fallback"] is False
    assert data["retrieved_count"] == 0


def test_chat_sync_should_not_overblock_contract_question():
    response = client.post(
        "/chat/sync",
        json={"message": "전세 계약서에서 뭘 확인해야 하나요?"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["guardrail_blocked"] is False


def test_chat_sync_no_result_fallback():
    response = client.post(
        "/chat/sync",
        json={"message": "상속 포기 절차가 궁금해요"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["category"] == "기타"
    assert data["guardrail_blocked"] is False
    assert data["is_fallback"] is True
    assert data["retrieved_count"] == 0