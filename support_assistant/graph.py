from typing import List, TypedDict

from langgraph.graph import StateGraph, END

from .classifier import classify_intent
from .llm import generate_answer, direct_answer
from .retriever import get_retriever
from .schemas import AnswerResponse


class State(TypedDict, total=False):
    question: str
    intent: str
    matched_keywords: List[str]
    retrieved: List[dict]
    response: dict


def classify_intent_node(state: State) -> dict:
    intent, keywords = classify_intent(state["question"])
    return {
        "question": state["question"],
        "intent": intent,
        "matched_keywords": keywords,
    }


def retrieve_and_answer_node(state: State) -> dict:
    retriever = get_retriever()
    retrieved = retriever.retrieve(state["question"], k=3)
    resp = generate_answer(state["question"], retrieved)
    return {
        "retrieved": retrieved,
        "response": resp.model_dump(),
        "intent": "policy",
    }


def direct_answer_node(state: State) -> dict:
    resp = direct_answer(state["question"])
    return {
        "response": resp.model_dump(),
        "intent": "direct",
        "retrieved": [],
    }


def _route(state: State):
    intent = state.get("intent", "direct")
    return "policy" if intent == "policy" else "direct"


builder = StateGraph(State)
builder.add_node("classify_intent", classify_intent_node)
builder.add_node("retrieve_and_answer", retrieve_and_answer_node)
builder.add_node("direct_answer", direct_answer_node)
builder.add_conditional_edges(
    "classify_intent", _route, {"policy": "retrieve_and_answer", "direct": "direct_answer"}
)
builder.add_edge("retrieve_and_answer", END)
builder.add_edge("direct_answer", END)
builder.set_entry_point("classify_intent")

graph = builder.compile()


def run(question: str) -> AnswerResponse:
    """Run the LangGraph workflow on a question and return a validated AnswerResponse."""
    final = graph.invoke({"question": question})
    return AnswerResponse(**final["response"])


def route_question(question: str):
    """Public helper returning (intent, matched_keywords) for a question."""
    return classify_intent(question)
