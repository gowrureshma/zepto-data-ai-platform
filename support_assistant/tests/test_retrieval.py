from support_assistant.retriever import build_retriever


def _build():
    return build_retriever()


def test_retrieve_returns_top_k():
    r = _build()
    res = r.retrieve("How do I report a damaged item?", k=3)
    assert len(res) == 3
    # cosine distance is in [0, 2]
    assert all(0.0 <= c["distance"] <= 2.0 for c in res)
    # distances non-decreasing (most similar first)
    assert [c["distance"] for c in res] == sorted(c["distance"] for c in res)
    top = res[0]
    assert top["source"] == "doc_06.txt"
    assert top["doc_id"] == "doc_06"
    assert top["chunk_id"] == "doc_06_p0"
    assert top["document"].strip() != ""


def test_retrieve_cancellation_routes_to_doc_05():
    r = _build()
    res = r.retrieve("How do I cancel my order before it is packed?", k=3)
    assert res[0]["source"] == "doc_05.txt"


def test_retrieve_delivery_routes_to_doc_01():
    r = _build()
    res = r.retrieve("Is delivery free on orders over 149?", k=3)
    assert res[0]["source"] == "doc_01.txt"


def test_collection_has_eight_chunks():
    r = _build()
    assert r.collection.count() == 8
