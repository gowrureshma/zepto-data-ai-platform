from support_assistant.classifier import classify_intent


POLICY_QUERIES = [
    "How do I report a damaged item?",
    "Is delivery free on orders over INR 149?",
    "How do I cancel my order?",
    "What are the gift card denominations?",
    "Can I return a non-perishable item within 7 days?",
    "Where is my order?",
    "What are the Zepto Pass+ benefits?",
    "How do I track my order?",
]

DIRECT_QUERIES = [
    "What is the capital of France?",
    "Tell me a joke.",
    "What's the weather today?",
    "42",
    "Who won the match last night?",
]


def test_policy_intent_detected():
    for q in POLICY_QUERIES:
        intent, matched = classify_intent(q)
        assert intent == "policy"
        assert matched, f"expected matched terms for: {q}"


def test_direct_intent_detected():
    for q in DIRECT_QUERIES:
        intent, matched = classify_intent(q)
        assert intent == "direct"
        assert matched == []
