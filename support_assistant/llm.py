import json
import re
from typing import List

from .config import MOCK_LLM, REAL_MODEL
from .prompt import PROMPT_TEMPLATE
from .schemas import AnswerResponse


def build_prompt(question: str, retrieved: List[dict]) -> str:
    """Render the structured prompt with the retrieved CONTEXT and the question."""
    context = "\n\n".join(
        f"[{r['source']} | chunk {r['chunk_id']}] {r['document']}" for r in retrieved
    )
    return PROMPT_TEMPLATE.format(question=question, context=context)


def generate_answer(question: str, retrieved: List[dict]) -> AnswerResponse:
    """Generate an AnswerResponse. Uses MOCK_LLM unless MOCK_LLM=0."""
    if MOCK_LLM:
        return _mock_answer(question, retrieved)
    return _real_answer(question, retrieved)


def _mock_answer(question: str, retrieved: List[dict]) -> AnswerResponse:
    """Offline, policy-grounded response built ONLY from the top retrieved chunk.

    No paid/real LLM is called. The response is based on retrieved policy text,
    so it never fabricates policy information.
    """
    if not retrieved:
        return AnswerResponse(
            answer="I don't have a Zepto policy document that addresses this question.",
            sources=[],
            confidence=0.0,
        )
    top = retrieved[0]
    dist = float(top.get("distance") or 0.0)
    # Chroma cosine distance is in [0, 2]; similarity = 1 - distance, clamped to [0,1].
    similarity = max(0.0, min(1.0, 1.0 - dist))
    confidence = round(similarity, 3)
    answer = (
        "[MOCK_LLM response - generated offline from the top retrieved policy chunk; "
        "no paid LLM was used] "
        f"Per Zepto policy {top['source']} (chunk {top['chunk_id']}): {top['document']}"
    )
    sources = list(dict.fromkeys(r["source"] for r in retrieved))
    return AnswerResponse(answer=answer, sources=sources, confidence=confidence)


def direct_answer(question: str) -> AnswerResponse:
    """Fixed / direct answer for non-policy questions."""
    return AnswerResponse(
        answer=(
            "I am Zepto's Support Assistant and can only help with questions about Zepto's "
            "policies: delivery, returns and refunds, membership tiers, order tracking, "
            "order cancellation, damaged or missing items, gift cards, and customer "
            "support hours. Please ask a policy-related question."
        ),
        sources=[],
        confidence=0.4,
    )


def _real_answer(question: str, retrieved: List[dict]) -> AnswerResponse:
    """Real-LLM path. Only used when MOCK_LLM=0. Validates JSON output with Pydantic
    and retries up to 2 additional attempts."""
    prompt = build_prompt(question, retrieved)
    try:
        import openai  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "MOCK_LLM=0 selected but the 'openai' package is not installed. "
            "Install it (pip install openai) and set OPENAI_API_KEY, or run with "
            "MOCK_LLM=1 (the default)."
        ) from e

    client = openai.OpenAI()
    raw = ""
    for attempt in range(3):  # initial attempt + 2 retries
        resp = client.chat.completions.create(
            model=REAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or ""
        parsed = _parse_json_object(raw)
        if parsed is not None:
            try:
                return AnswerResponse(**parsed)
            except Exception:
                parsed = None  # malformed fields -> retry
    raise RuntimeError(
        "Real LLM did not return a valid AnswerResponse after 2 retries. "
        f"Last raw output: {raw}"
    )


def _parse_json_object(raw: str):
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    return None