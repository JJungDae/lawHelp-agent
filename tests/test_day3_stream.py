from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_stream_normal_question_returns_token_and_done(monkeypatch):
    def fake_stream_text(prompt: str, system=None):
        yield "첫 "
        yield "답변"

    monkeypatch.setattr("app.api.chat.stream_text", fake_stream_text)

    response = client.post(
        "/chat/stream",
        json={"message": "월세 계약 전에 뭘 확인해야 하나요?"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: token\ndata: {"text": "첫 "}' in response.text
    assert 'event: token\ndata: {"text": "답변"}' in response.text
    assert "event: done\ndata: {}" in response.text


def test_chat_stream_blocked_question_returns_one_token_and_done(monkeypatch):
    def fail_stream_text(prompt: str, system=None):
        raise AssertionError("stream_text should not be called")

    monkeypatch.setattr("app.api.chat.stream_text", fail_stream_text)

    response = client.post(
        "/chat/stream",
        json={"message": "제가 소송하면 이길 수 있을까요? 소장 좀 써주세요"},
    )

    assert response.status_code == 200
    assert response.text.count("event: token") == 1
    assert "event: done\ndata: {}" in response.text
    assert "개별 사건의 승소 가능성 판단" in response.text


def test_chat_stream_no_result_returns_one_token_and_done(monkeypatch):
    def fail_stream_text(prompt: str, system=None):
        raise AssertionError("stream_text should not be called")

    monkeypatch.setattr("app.api.chat.stream_text", fail_stream_text)

    response = client.post(
        "/chat/stream",
        json={"message": "상속 포기 절차가 궁금해요"},
    )

    assert response.status_code == 200
    assert response.text.count("event: token") == 1
    assert "event: done\ndata: {}" in response.text
    assert "관련 정보를 충분히 찾지 못했습니다" in response.text


def test_chat_stream_llm_error_returns_error_event(monkeypatch):
    from app.core.llm import LLMError

    def fail_stream_text(prompt: str, system=None):
        raise LLMError("stream failed")
        yield ""

    monkeypatch.setattr("app.api.chat.stream_text", fail_stream_text)

    response = client.post(
        "/chat/stream",
        json={"message": "월세 계약 전에 뭘 확인해야 하나요?"},
    )

    assert response.status_code == 200
    assert 'event: error\ndata: {"message": "stream failed"}' in response.text
    assert "event: done" not in response.text
