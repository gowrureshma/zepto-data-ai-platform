from pathlib import Path
import os

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # repository root

DOCS_DIR = HERE / "docs"

# Embedding model (local, no paid service).
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
TOP_K = 3

# ChromaDB persistence location.
CHROMA_DIR = HERE / "outputs" / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
COLLECTION_NAME = "zepto_policies"

# MOCK_LLM defaults to enabled. It is enabled for any of "", "1", "true".
# Set MOCK_LLM=0 (and install openai + set OPENAI_API_KEY) to use a real LLM.
_mock_env = os.environ.get("MOCK_LLM", "1").strip().lower()
MOCK_LLM = _mock_env in ("", "1", "true", "yes")

# Real LLM (only used when MOCK_LLM is False).
REAL_MODEL = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")

# The EXACT eight supplied Zepto policy documents. Ingestion must use these
# and only these as its knowledge source.
EXPECTED_POLICY_DOCS = [
    "doc_01.txt", "doc_02.txt", "doc_03.txt", "doc_04.txt",
    "doc_05.txt", "doc_06.txt", "doc_07.txt", "doc_08.txt",
]
