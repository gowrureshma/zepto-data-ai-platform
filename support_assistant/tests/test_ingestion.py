from support_assistant.ingestion import load_documents, chunk_documents, build_chunks
from support_assistant.config import EXPECTED_POLICY_DOCS


def test_loads_all_eight_documents():
    docs = load_documents()
    assert len(docs) == 8
    sources = sorted(d["source"] for d in docs)
    assert sources == sorted(EXPECTED_POLICY_DOCS)


def test_each_document_non_empty_and_source_preserved():
    docs = load_documents()
    for d in docs:
        assert d["source"] in EXPECTED_POLICY_DOCS
        assert d["text"].strip() != ""
        assert d["path"].endswith(d["source"])


def test_chunks_have_unique_ids_and_source_identity():
    chunks = build_chunks()
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))  # unique
    # one chunk per doc (each doc is a single paragraph)
    assert len(chunks) == 8
    for c in chunks:
        assert c["source"] in EXPECTED_POLICY_DOCS
        assert c["chunk_id"].startswith(c["doc_id"])
