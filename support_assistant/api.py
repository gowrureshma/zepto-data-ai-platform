from fastapi import FastAPI
from pydantic import BaseModel

from .graph import run
from .schemas import AnswerResponse

app = FastAPI(
    title="Zepto Support Assistant",
    description="Policy-only support assistant over the 8 Zepto policy documents.",
    version="0.1.0",
)


class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok", "mock_llm": True}


@app.post("/ask", response_model=AnswerResponse)
def ask(req: AskRequest):
    return run(req.question)
