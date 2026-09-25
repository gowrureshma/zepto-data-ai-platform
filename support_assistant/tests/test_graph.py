from support_assistant.graph import run, route_question
from support_assistant.schemas import AnswerResponse
from support_assistant.config import MOCK_LLM


def test_policy_query_uses_retrieval_path():
    intent, matched = route_question("How do I report a damaged item?")
    assert intent == "policy"

    resp = run("How do I report a damaged item?")
    assert isinstance(resp, AnswerResponse)
    assert resp.answer and resp.answer.strip() != ""
    # Mock mode: response is grounded in the top retrieved chunk.
    assert "doc_06.txt" in resp.sources
    assert 0.0 <= resp.confidence <= 1.0


def test_direct_query_uses_direct_path():
    intent, matched = route_question("What is the capital of France?")
    assert intent == "direct"
    assert matched == []

    resp = run("What is the capital of France?")
    assert isinstance(resp, AnswerResponse)
    assert resp.sources == []
    assert resp.answer  # fixed direct answer present


def test_mock_llm_is_default():
    assert MOCK_LLM is True
