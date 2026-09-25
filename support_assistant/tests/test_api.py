from fastapi.testclient import TestClient

from support_assistant.api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ask_policy_uses_retrieval():
    r = client.post("/ask", json={"query": "How long do I have to return an item?"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"answer", "sources", "confidence"}
    assert isinstance(body["sources"], list)
    assert 0.0 <= body["confidence"] <= 1.0
    assert len(body["answer"]) > 0


def test_ask_direct_question():
    r = client.post("/ask", json={"query": "Tell me a joke."})
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"answer", "sources", "confidence"}
    assert body["sources"] == []
    assert len(body["answer"]) > 0
