"""Integration tests for the FastAPI chat and health endpoints."""

from fastapi.testclient import TestClient
from unittest.mock import patch
from src.app.main import app

client = TestClient(app)

def test_health_check():
    """Check that the /health endpoint returns a 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("src.app.main.chat_agent.invoke")
def test_chat_endpoint_success(mock_invoke):
    """Verify a successful chat response with database retrieval."""
    mock_invoke.return_value = {
        "answer": "Inception is about dreams.",
        "requires_retrieval": True,
    }

    payload = {"query": "Tell me about Inception"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Inception is about dreams."
    assert data["intent"] == "retrieve"
    assert data["retrieved_movies"] == ["Executed DB Query"]

@patch("src.app.main.chat_agent.invoke")
def test_chat_endpoint_no_retrieval(mock_invoke):
    """Verify a chat response with no database retrieval (history-based answer)."""
    mock_invoke.return_value = {
        "answer": "I am a movie agent.",
        "requires_retrieval": False,
    }

    payload = {"query": "Who are you?"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "I am a movie agent."
    assert data["intent"] == "chat"
    assert data["retrieved_movies"] == []

@patch("src.app.main.chat_agent.invoke")
def test_chat_endpoint_fallback(mock_invoke):
    """Verify the fallback reply when the agent returns no answer key."""
    mock_invoke.return_value = {}

    payload = {"query": "Something weird"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "I could not generate an answer."

def test_chat_endpoint_invalid_payload():
    """Verify that a missing required field returns HTTP 422."""
    response = client.post("/chat", json={"invalid": "payload"})
    assert response.status_code == 422

@patch("src.app.main.chat_agent.invoke")
def test_chat_endpoint_agent_failure(mock_invoke):
    """Verify that an agent exception returns HTTP 503."""
    mock_invoke.side_effect = RuntimeError("Ollama unavailable")

    payload = {"query": "Who directed Inception?"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 503
    assert response.json()["detail"] == "Agent temporarily unavailable"
