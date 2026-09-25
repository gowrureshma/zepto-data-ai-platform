# Zepto Data & AI Platform

A three-module capstone platform built around Zepto-style quick-commerce data:

- **Module 1 — Data Pipeline** (`data_pipeline/`): scrapes [books.toscrape.com](https://books.toscrape.com/),
  cleans the data, loads it into a normalized SQLite database, runs SQL queries, and
  verifies a SQL `JOIN` against an equivalent `pandas.merge`.
- **Module 2 — Analytics** (`analytics/`): EDA, classification, and regression on the
  Titanic dataset (survival prediction; `fare` regression).
- **Module 3 — Support Assistant** (`support_assistant/`): a retrieval-augmented
  policy assistant over the 8 Zepto policy documents, using local embeddings,
  ChromaDB, a LangGraph workflow, and a FastAPI API.

> The three modules are independent. Module 2 and Module 3 do not modify Module 1, and
> the EDA notebook does not modify the data pipeline.

## Repository structure

```
zepto-data-ai-platform/
├── README.md                 # this file
├── requirements.txt          # repository-level dependencies (union of all modules)
├── .gitignore
├── data_pipeline/            # Module 1
│   ├── pipeline.py           # orchestrator (entry point)
│   ├── scraper.py            # books.toscrape.com scraper
│   ├── cleaner.py            # cleaning + GBP->INR
│   ├── database.py           # normalized SQLite schema
│   ├── queries.py            # SQL queries + text output
│   ├── verify.py             # SQL JOIN vs pandas.merge verification
│   ├── config.py             # constants (URL, fixed rate, paths)
│   ├── requirements.txt      # requests, beautifulsoup4, pandas
│   ├── README.md             # Module 1 docs
│   └── output/               # generated (gitignored): raw_books.json, cleaned_books.csv, books.db, *.txt, *.json
├── analytics/                # Module 2
│   ├── 01_eda.ipynb          # EDA (loads titanic once, saves titanic.csv)
│   ├── 02_classification.ipynb
│   ├── 03_regression.ipynb
│   ├── 04_model_integration.ipynb
│   ├── titanic.csv           # saved dataset (tracked)
│   ├── requirements.txt       # Module 2 dependencies
│   └── outputs/              # generated (gitignored): metric CSVs, charts, joblib, recommendation
└── support_assistant/        # Module 3
    ├── docs/                 # the 8 supplied Zepto policy documents
    ├── api.py                # FastAPI app (POST /ask)
    ├── graph.py              # LangGraph StateGraph workflow
    ├── retriever.py          # ChromaDB (cosine) + top-3 retrieval
    ├── embedder.py           # sentence-transformers all-MiniLM-L6-v2
    ├── ingestion.py          # load + chunk the 8 policy docs
    ├── classifier.py         # keyword intent classification
    ├── prompt.py             # structured prompt template
    ├── llm.py                # MOCK_LLM grounded answer + real-LLM fallback
    ├── schemas.py            # Pydantic AnswerResponse
    ├── config.py             # paths, model, MOCK_LLM default
    ├── run_server.py         # uvicorn entrypoint (port 7860)
    ├── requirements.txt      # fastapi, uvicorn, pydantic, langgraph, chromadb, sentence-transformers, pytest, httpx
    ├── Dockerfile
    ├── README.md
    └── tests/                # pytest suite
```

## Installation / setup

A Python 3.10+ environment is required. The platform uses local models only by default;
no paid API key is needed to run anything.

```bash
# Repository-level dependencies (union of all modules)
python -m pip install -r requirements.txt

# Or install per module:
# python -m pip install -r data_pipeline/requirements.txt
# python -m pip install -r analytics/requirements.txt
# python -m pip install -r support_assistant/requirements.txt
```

The `sentence-transformers` model `all-MiniLM-L6-v2` is downloaded on first use by
Module 3 (cached locally afterward). `MOCK_LLM` is `1` by default, so no LLM API key
is required.

## Run Module 1 — Data Pipeline

```bash
python -m data_pipeline.pipeline
```

This scrapes the first 5 catalogue pages of books.toscrape.com (100 books, 29 categories),
cleans the data, builds the SQLite database, runs 7 SQL queries, and verifies the JOIN
against `pandas.merge`. Outputs are written under `data_pipeline/output/` (gitignored):
`raw_books.json`, `cleaned_books.csv`, `books.db`, `sql_query_outputs.txt`,
`join_comparison.json`.

**Design decisions**
- Source: `https://books.toscrape.com/`, first 5 pages (20 books/page) → 100 books (>= 60).
- Cleaning: `price_str` -> `price_gbp` (float), `star_rating` One..Five -> `rating` (int 1..5),
  availability -> `in_stock` (int 0/1); parse failures are coerced (no crash); rows missing
  essential fields are dropped.
- Currency: **1 GBP = 105.50 INR, fixed** (`config.GBP_TO_INR = 105.50`). `price_inr =
  price_gbp * 105.50`, rounded to 2 decimals. Not a live rate.
- Normalized schema: `categories(category_id PK, category_name UNIQUE)` and
  `books(..., category_id REFERENCES categories(category_id))`; `reset_schema` makes reruns
  deterministic.
- SQL verification: the JOIN is executed in SQL and reproduced with `pandas.merge`, then
  compared with `pd.testing.assert_frame_equal`; both return 100 equal rows.
- Latest verified run: 100 books, 29 categories, `join_comparison.json` `match=true`.

## Run Module 2 — Analytics (notebooks)

```bash
# Option A: run all notebooks end-to-end
for nb in analytics/01_eda.ipynb analytics/02_classification.ipynb analytics/03_regression.ipynb analytics/04_model_integration.ipynb; do
  jupyter nbconvert --to notebook --execute --inplace "$nb"
done

# Option B: open and run interactively
jupyter notebook analytics/
```

### Methodology & key results (Module 2)
- **EDA** (`01_eda.ipynb`): `sns.load_dataset("titanic")` called exactly once and saved
  immediately to `analytics/titanic.csv`; all later work reads that CSV. Missing-value rule
  is data-driven: <5% drop rows, 5–30% impute, >30% encode as its own category. Age imputed
  with the median within each `(sex, pclass)` group. IQR outlier counts for age and fare,
  fare mean/median/mode/skew (right-skewed), survival analyses, a 6-column correlation
  matrix `{survived,pclass,age,sibsp,parch,fare}` (excludes `adult_male`/`alone`), and a
  standardization sanity check (EDA-only).
- **Classification** (`02_classification.ipynb`): target `survived`; a single stratified
  80/20 split created *before* preprocessing and reused for all three models;
  `ColumnTransformer`+`Pipeline` (numeric median+StandardScaler, categorical
  most_frequent+OneHotEncoder) fit on train only; LR / Decision Tree / Random Forest;
  metrics accuracy/precision/recall/F1/ROC-AUC; confusion matrices + ROC curves;
  class-imbalance comparison (baseline / `class_weight="balanced"` / SMOTE trained on the
  training fold only) with an explicit leak check; `GridSearchCV` over
  `n_estimators`/`max_depth`/`max_features` with `RandomForestClassifier(oob_score=True)`.
- **Regression** (`03_regression.ipynb`): multivariate `LinearRegression` predicting `fare`;
  MAE/RMSE/R2/Adjusted R2; residual plot; heteroscedasticity diagnostic and conclusion.
- **Integration** (`04_model_integration.ipynb`): reads the existing result CSVs and writes
  `analytics/outputs/model_comparison.csv` (classification vs regression groups),
  `analytics/outputs/deployment_recommendation.txt`, and reloads the persisted pipeline on
  raw unprocessed input.
- Key metrics (from the saved outputs in `analytics/outputs/`):
  - Logistic Regression: accuracy 0.8258, F1 0.7559, ROC-AUC 0.8584 (best base model).
  - Decision Tree: F1 0.6880, ROC-AUC 0.8265.
  - Random Forest: F1 0.7068, ROC-AUC 0.8355.
  - Tuned Random Forest (best params `max_depth=10, max_features=0.5, n_estimators=200`):
    CV F1 0.7549, OOB 0.8200, test F1 0.7538, ROC-AUC 0.8417.
  - Imbalance: SMOTE lifts recall to 0.7500 (from 0.7059) with the best ROC-AUC 0.8620.
  - Regression: MAE 17.6887, RMSE 43.3258, R2 0.3642, Adjusted R2 0.3053 (n=178, p=15).
  - Saved pipeline: `analytics/outputs/titanic_classification_pipeline.joblib` (reloaded and
    executed on raw input → prediction returned; no manual preprocessing).

## Run Module 3 — Support Assistant

```bash
# API (MOCK_LLM=1 default; runs offline, no paid LLM)
python -m support_assistant.run_server      # serves on http://0.0.0.0:7860

# Tests
python -m pytest support_assistant/tests -q  # 18 tests
```

### Architecture: ingestion -> embedding -> retrieval -> generation
1. **Ingestion** (`support_assistant/ingestion.py`): loads exactly the 8 supplied policy
   documents from `support_assistant/docs/` (source = filename, verbatim — never rewritten).
2. **Chunking**: each document is split into paragraphs (one chunk per doc here); every chunk
   gets a unique `chunk_id` (`<doc_id>_p<index>`) and keeps its `source`.
3. **Embedding** (`embedder.py`): local `sentence-transformers` model `all-MiniLM-L6-v2`
   (384-dim). No paid/external embedding service.
4. **Vector store** (`retriever.py`): ChromaDB collection with `hnsw:space = cosine`;
   stores chunk IDs + `{doc_id, source}` metadata.
5. **Retrieval**: `PolicyRetriever.retrieve(query, k=3)` returns the **top 3** chunks by
   cosine similarity.
6. **Language/agent** (`graph.py`): LangGraph `StateGraph` with a `TypedDict` state and three
   nodes — `classify_intent` -> `retrieve_and_answer` (policy) | `direct_answer` (general) —
   with conditional routing. Generation (`llm.py`):
   - `MOCK_LLM=1` (default): a grounded answer built only from the top retrieved chunk (no real
     LLM network call; clearly tagged as a mock).
   - `MOCK_LLM=0`: renders the structured prompt (ROLE/CONTEXT/TASK/FORMAT/LENGTH/negative
     constraint/few-shot) and calls a real LLM (requires `openai` + `OPENAI_API_KEY`); the
     JSON output is validated with Pydantic and retried up to 2 additional attempts.
7. **API** (`api.py`): FastAPI `POST /ask` accepting `{"query": "..."}` and returning a
   validated `AnswerResponse {answer, sources, confidence}`.

### API examples (actual responses from the running server)

Policy/retrieval question:

```bash
curl -X POST http://localhost:7860/ask -H 'Content-Type: application/json' -d '{"query":"How long do I have to return an item?"}'
```
```json
{
  "answer": "[MOCK_LLM response - generated offline from the top retrieved policy chunk; no paid LLM was used] Per Zepto policy doc_02.txt (chunk doc_02_p0): ...",
  "sources": ["doc_02.txt", "doc_06.txt", "doc_05.txt"],
  "confidence": 0.677
}
```

Direct / non-policy question:

```bash
curl -X POST http://localhost:7860/ask -H 'Content-Type: application/json' -d '{"query":"Tell me a joke."}'
```
```json
{
  "answer": "I am Zepto's Support Assistant and can only help with questions about Zepto's policies... Please ask a policy-related question.",
  "sources": [],
  "confidence": 0.4
}
```

## Docker usage (Module 3)

```bash
docker build -t zepto-support-assistant support_assistant
docker run -p 7860:7860 -e MOCK_LLM=1 zepto-support-assistant
curl -X POST http://localhost:7860/ask -H 'Content-Type: application/json' -d '{"query":"Is delivery free?"}'
```

The `Dockerfile` uses `python:3.12-slim`, installs `support_assistant/requirements.txt`,
exposes **7860**, sets `MOCK_LLM=1`, and runs `python -m support_assistant.run_server`.

## Git workflow

Development happens on the `feature/zepto-capstone` branch:

```bash
git checkout -b feature/zepto-capstone   # from main, once main exists
git add <files>
git commit -m "..."
git push
```

The intended lifecycle is: create `main` from a stable base, do all work on
`feature/zepto-capstone`, then open a pull request and **merge into `main`** once review
passes. As of this audit the feature branch is complete and the working tree is clean; the
final merge into `main` has **not** been performed yet.

> NOTE (audit finding): at the time of this audit only `feature/zepto-capstone` existed;
> a `main` branch had not yet been created. The required fixes create `main` from the
> current HEAD and leave the final merge to a later PR step.
