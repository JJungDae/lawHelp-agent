import pytest

from app.repositories.mock_law_repository import search_law_qa as mock_search_law_qa


@pytest.fixture(autouse=True)
def use_mock_search_for_chat_flow(monkeypatch):
    monkeypatch.setattr("app.agents.nodes._search_law_qa", mock_search_law_qa)
