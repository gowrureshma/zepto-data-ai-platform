from pathlib import Path
from typing import Callable, List

from .config import DOCS_DIR, EXPECTED_POLICY_DOCS


def _doc_path(doc_name: str) -> Path:
    p = DOCS_DIR / doc_name
    if not p.exists():
        raise FileNotFoundError(f"Required policy document missing: {p}")
    return p


def load_documents() -> List[dict]:
    """Load exactly the 8 supplied policy documents.

    Each document preserves its source identity (filename = source).
    Does NOT load, rewrite, or invent any other policy text.
    """
    docs = []
    for name in EXPECTED_POLICY_DOCS:
        p = _doc_path(name)
        text = p.read_text(encoding="utf-8").strip()
        docs.append({
            "id": p.stem,
            "source": p.name,
            "text": text,
            "path": str(p),
        })
    return docs


def _split_paragraphs(text: str) -> List[str]:
    """Split a document into paragraphs on blank lines.

    Each supplied policy document is a single paragraph, so this yields one
    chunk per document (one chunk per document is acceptable per the spec).
    """
    paras = [pg.strip() for pg in text.split("\n\n") if pg.strip()]
    return paras if paras else [text]


def chunk_documents(docs: List[dict], splitter: Callable = _split_paragraphs) -> List[dict]:
    """Chunk documents.

    - One chunk per paragraph (one chunk per doc for these documents).
    - Every chunk gets a unique ID (``<doc_id>_p<index>``).
    - Source document identity is preserved on every chunk.
    """
    chunks = []
    for doc in docs:
        for i, part in enumerate(splitter(doc["text"])):
            chunks.append({
                "chunk_id": f"{doc['id']}_p{i}",
                "doc_id": doc["id"],
                "source": doc["source"],
                "text": part,
            })
    return chunks


def build_chunks() -> List[dict]:
    return chunk_documents(load_documents())
