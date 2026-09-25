# Zepto Support Assistant (Module 3)

A Retrieval-Augmented (RAG-style) Support Assistant for Zepto's customer-support
policies, built with a **local** embedding model, **ChromaDB** vector store, a
**LangGraph** workflow, and a **FastAPI** API. The assistant runs entirely offline
by default (`MOCK_LLM=1`) — no paid LLM API is required for default execution.

## Knowledge source (the only source of truth)

The assistant uses **exactly these 8 supplied Zepto policy documents** located at
`support_assistant/docs/`:

| File | Topic |
|------|-------|
| `doc_01.txt` | Delivery Policy |
| `doc_02.txt` | Returns & Refunds |
| `doc_03.txt` | Membership Tiers |
| `doc_04.txt` | Order Tracking |
| `doc_05.txt` | Order Cancellation Policy |
| `doc_06.txt` | Damaged or Missing Items |
| `doc_07.txt` | Gift Cards |
| `doc_08.txt` | Customer Support Hours |

Policy text is **read verbatim** — it is not rewritten, paraphrased, or invented.

## Architecture

```
docs/ (8 policy .txt files)
      |
      ingestion.py  -> load_documents()  (exactly the 8 docs, source preserved)
            |
      ingestion.chunk_documents()  -> one chunk per doc, unique chunk_id per chunk
            |
      embedder.py  -> sentence-transformers all-MiniLM-L6-v2  (LOCAL, no paid service)
            |
      retriever.py  -> ChromaDB collection, cosine similarity, top-3 retrieval
            |
      prompt.py     -> structured ROLE/CONTEXT/TASK/FORMAT/LENGTH/negative/few-shot
            |
      classifier.py -> keyword heuristic intent classification (policy vs direct)
            |
      llm.py        -> MOCK_LLM (top-chunk grounded answer) | real-LLM fallback
            |
      graph.py      -> LangGraph StateGraph: classify_intent -> retrieve_and_answer
                                  |-> direct_answer, conditional routing
            |
      api.py        -> FastAPI POST /ask -> AnswerResponse
            |
      schemas.py    -> Pydantic AnswerResponse {answer, sources, confidence}
```

### Ingestion -> chunking -> embedding -> ChromaDB -> retrieval -> generation

1. **Ingestion** (`ingestion.py`): loads the 8 `doc_*.txt` files exactly as supplied.
2. **Chunking**: each document is split by paragraph (one chunk per document here,
   since each policy document is a single paragraph). Every chunk receives a unique
   `chunk_id` (`<doc_id>_p<index>`) and keeps its `source` document filename.
3. **Embeddings** (`embedder.py`): the local `sentence-transformers` model
   `all-MiniLM-L6-v2` (384-dim) encodes chunks and queries. No paid API.
4. **Vector DB** (`retriever.py`): a ChromaDB collection configured with
   `hnsw:space = cosine`. Chunk IDs, embeddings, documents, and
   `{doc_id, source}` metadata are stored. Queries return the **top 3** chunks by
   cosine similarity (lower distance = more similar).
5. **Retrieval**: `PolicyRetriever.retrieve(query, k=3)` returns ranked chunks with
   `chunk_id`, `doc_id`, `source`, `document`, and `distance`.
6. **Generation** (`llm.py`):
   - `MOCK_LLM=1` (default): produces a policy-grounded answer **only** from the top
     retrieved chunk — no real LLM is called. The response is clearly marked as a mock.
   - `MOCK_LLM=0`: renders the structured prompt and calls a real LLM (requires the
     `openai` package and `OPENAI_API_KEY`), parses JSON, validates with Pydantic, and
     retries parsing/validation up to 2 additional attempts.

### LangGraph routing

A `StateGraph` with a `TypedDict` state and three nodes:

- `classify_intent` — runs keyword/heuristic classification.
- `retrieve_and_answer` — retrieves top-3 and generates an answer (policy path).
- `direct_answer` — returns a fixed answer (direct/non-policy path).

Routing is **conditional** on the classified intent:
`classify_intent` -> `{policy: retrieve_and_answer, direct: direct_answer}` -> `END`.

### MOCK_LLM

`MOCK_LLM` defaults to **enabled**. It is on for any value of `""`, `"1"`, `"true"`, `"yes"`
(the default). Set `MOCK_LLM=0` (and provide `OPENAI_API_KEY` plus the `openai` package and
optionally `LLM_MODEL`) to use a real LLM. The application **always runs** without a paid
API because the mock path is the default.

## API usage

`MOCK_LLM=1` is the default, so the API works offline (no paid/external LLM). Questions
are sent as `{"query": "..."}`.

### Example 1 — policy/retrieval question

```
POST /ask
Content-Type: application/json

{"query": "How long do I have to return an item?"}

Response (200):
{
  "answer": "[MOCK_LLM response - generated offline from the top retrieved policy chunk; no paid LLM was used] Per Zepto policy doc_02.txt (chunk doc_02_p0): ...",
  "sources": ["doc_02.txt", "doc_06.txt", "doc_05.txt"],
  "confidence": 0.677
}
```

Policy questions (delivery, returns, cancellation, damaged items, gift cards, etc.) are
routed to the **retrieval path** and answered from the top-3 retrieved policy chunks.

### Example 2 — direct / non-policy question

```
POST /ask
Content-Type: application/json

{"query": "Tell me a joke."}

Response (200):
{
  "answer": "I am Zepto's Support Assistant and can only help with questions about Zepto's policies: ... Please ask a policy-related question.",
  "sources": [],
  "confidence": 0.4
}
```

Non-policy questions are routed to the **direct-answer path**, which returns a fixed
policy-scope message.

In a shell:

```bash
curl -X POST http://localhost:7860/ask -H 'Content-Type: application/json' -d '{"query":"Is delivery free?"}'
```

## Running locally

```bash
# (optional) install deps
pip install -r support_assistant/requirements.txt

# API (mock mode, port 7860)
python -m support_assistant.run_server
```

## Running tests

```bash
python -m pytest support_assistant/tests -q
```

Tests cover: ingestion (8 docs, unique IDs, source identity), retrieval (top-3, cosine
distances, correct doc routing), intent classification, LangGraph routing (policy + direct),
Pydantic validation, and `/ask` for both paths.

## Docker usage

```bash
docker build -t zepto-support-assistant support_assistant
docker run -p 7860:7860 -e MOCK_LLM=1 zepto-support-assistant
# then: curl -X POST http://localhost:7860/ask -H 'Content-Type: application/json' -d '{"query":"Is delivery free?"}'
```

The `Dockerfile` exposes port `7860`.

## Files

```
support_assistant/
├── docs/                 # the 8 supplied policy documents (read-only knowledge source)
├── ingestion.py          # load the 8 docs + chunking (unique IDs, source preserved)
├── embedder.py           # sentence-transformers all-MiniLM-L6-v2 (local embeddings)
├── retriever.py          # ChromaDB (cosine) + top-3 retrieval
├── prompt.py             # structured prompt template
├── classifier.py         # keyword/heuristic intent classification
├── llm.py                # MOCK_LLM grounded answer + real-LLM fallback (validated, retried)
├── graph.py              # LangGraph StateGraph workflow
├── api.py                # FastAPI app (POST /ask)
├── schemas.py            # Pydantic AnswerResponse
├── run_server.py         # uvicorn entrypoint (port 7860)
├── config.py             # paths, model name, MOCK_LLM default
├── tests/                # pytest suite
├── requirements.txt
├── Dockerfile
└── README.md
```
