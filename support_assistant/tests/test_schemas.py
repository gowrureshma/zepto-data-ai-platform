import pytest
from pydantic import ValidationError

from support_assistant.schemas import AnswerResponse


def test_valid_answer():
    a = AnswerResponse(answer="hello", sources=["doc_01.txt"], confidence=0.9)
    assert a.answer == "hello"
    assert a.sources == ["doc_01.txt"]
    assert a.confidence == 0.9


def test_defaults():
    a = AnswerResponse(answer="hi")
    assert a.sources == []
    assert 0.0 <= a.confidence <= 1.0


def test_confidence_out_of_range():
    with pytest.raises(ValidationError):
        AnswerResponse(answer="x", sources=[], confidence=1.5)
    with pytest.raises(ValidationError):
        AnswerResponse(answer="x", sources=[], confidence=-0.1)
