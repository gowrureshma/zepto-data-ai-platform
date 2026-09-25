# Keyword/heuristic intent classification.
#
# A question is classified as a "policy" question when it contains one of the
# policy-specific terms below (covering the 8 policy documents). Otherwise it is
# classified as "direct" (non-policy). Matching is case-insensitive substring
# matching.

POLICY_TERMS = [
    # doc_01 Delivery Policy
    "delivery", "deliver", "free delivery",
    # doc_02 Returns & Refunds
    "return", "returns", "refund", "refunds",
    # doc_03 Membership Tiers
    "membership", "tier", "tiers", "zepto pass", "pass+", "pass tier",
    # doc_04 Order Tracking
    "track order", "track my order", "tracking", "order status", "where is my order", "track",
    # doc_05 Order Cancellation Policy
    "cancel", "cancellation", "cancel order",
    # doc_06 Damaged or Missing Items
    "damaged", "missing", "spoiled", "defect", "missing item",
    # doc_07 Gift Cards
    "gift card", "gift cards", "giftcard", "voucher",
    # doc_08 Customer Support Hours
    "support hours", "support available", "24 hours", "business days",
]


def classify_intent(question: str):
    """Return (intent, matched_terms).

    intent is "policy" when any policy term is present, otherwise "direct".
    """
    q = (question or "").lower()
    matched = [term for term in POLICY_TERMS if term in q]
    intent = "policy" if matched else "direct"
    return intent, matched
