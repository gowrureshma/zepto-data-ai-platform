from typing import List

import chromadb

from .config import COLLECTION_NAME, TOP_K
from .embedder import embed_text
from .ingestion import build_chunks


class PolicyRetriever:
    """ChromaDB vector store for the 8 policy documents.

    - Cosine similarity.
    - Stores chunk IDs plus source/doc metadata.
    - Retrieves the top-K chunks.
    """

    def __init__(self, collection_name: str = COLLECTION_NAME):
        self.client = chromadb.Client()
        # get_or_create + upsert make indexing idempotent across multiple
        # in-memory clients created within the same process.
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def index(self, chunks: List[dict]) -> "PolicyRetriever":
        if not chunks:
            return self
        self.collection.upsert(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=embed_text([c["text"] for c in chunks]),
            documents=[c["text"] for c in chunks],
            metadatas=[{"doc_id": c["doc_id"], "source": c["source"]} for c in chunks],
        )
        return self

    def retrieve(self, query: str, k: int = TOP_K) -> List[dict]:
        count = self.collection.count()
        if count == 0:
            raise RuntimeError("Collection is empty; call index() before retrieve().")
        n = min(k, count)
        query_vec = embed_text([query])[0]
        res = self.collection.query(query_embeddings=[query_vec], n_results=n)
        out = []
        for i, cid in enumerate(res["ids"][0]):
            md = res["metadatas"][0][i]
            out.append({
                "chunk_id": cid,
                "doc_id": md.get("doc_id"),
                "source": md.get("source"),
                "document": res["documents"][0][i],
                "distance": float(res["distances"][0][i]),  # cosine distance (1 - sim)
            })
        return out


def build_retriever() -> PolicyRetriever:
    """Build a fresh in-memory retriever indexed with the 8 policy docs."""
    r = PolicyRetriever()
    r.index(build_chunks())
    return r


# Lazily-built module singleton used by the API / graph.
_singleton: PolicyRetriever = None


def get_retriever() -> PolicyRetriever:
    global _singleton
    if _singleton is None:
        _singleton = build_retriever()
    return _singleton
