from typing import List

from sentence_transformers import SentenceTransformer

from .config import EMBEDDING_MODEL

_model = None


def get_model() -> SentenceTransformer:
    """Lazy-load the local sentence-transformers model (no paid service)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_text(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts with the local model. Returns a list of vectors."""
    return get_model().encode(
        texts, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=False
    ).tolist()
