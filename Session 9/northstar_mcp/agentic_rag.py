"""Day 5 Lab 3: Agentic (corrective) RAG in LangGraph: retrieve -> grade -> rewrite/re-retrieve -> generate | give up.

Prereq: python ingest.py.   Run: python agentic_rag.py
"""
from typing import Literal

from langchain_core.documents import Document
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from classic_rag import format_docs
from ingest import open_store
from llm import MODEL_FAST, chat_model

llm = chat_model(max_tokens=8000) 
grader_llm = chat_model(MODEL_FAST, max_tokens=1000)          # cheap, narrow job (or a local ChatOllama)
retriever = open_store(500).as_retriever(search_kwargs={"k": 4, "filter": {"is_current": True}})
MAX_RETRIES = 2


class Grade(BaseModel):
    relevant: bool = Field(description="Do these chunks contain enough to answer the question?")
    missing: str = Field(description="What information is missing or ambiguous, if anything")


class Rewrite(BaseModel):
    query: str = Field(description="A better search query using Northstar's policy vocabulary")


class RAGState(TypedDict):
    question: str
    query: str
    docs: list[Document]
    retries: int
    grade: Grade | None
    answer: str


def retrieve(s: RAGState):
    return {"docs": retriever.invoke(s["query"])}


def grade_documents(s: RAGState):
    g = grader_llm.with_structured_output(Grade).invoke(
        f"Question: {s['question']}\n\nRetrieved chunks:\n{format_docs(s['docs'])}\n\n"
        "Be strict: chunks about API RATE limits or REFUND limits do not answer questions about merchant PROCESSING "
        "limits, and vice versa. If the question is ambiguous about which limit, say so in 'missing'.")
    return {"grade": g}


def decide(s: RAGState) -> Literal["generate", "rewrite", "give_up"]:
    if s["grade"].relevant:
        return "generate"
    return "rewrite" if s["retries"] < MAX_RETRIES else "give_up"


def rewrite(s: RAGState):
    r = llm.with_structured_output(Rewrite).invoke(
        f"Original question: {s['question']}\nPrevious query: {s['query']}\nWhat was missing: {s['grade'].missing}\n"
        "Rewrite the search query. Use internal terms like 'temporary processing limit increase', 'High risk tier', "
        "'MCC 7995 betting/gaming', 'rolling reserve', 'chargeback watchlist'.")
    print(f"  rewrite #{s['retries'] + 1}: {r.query}")
    return {"query": r.query, "retries": s["retries"] + 1}


def generate(s: RAGState):
    msg = llm.invoke(f"Answer using ONLY these sources and cite them in [brackets].\n\n{format_docs(s['docs'])}\n\n"
                     f"Question: {s['question']}")
    return {"answer": msg.text}


def give_up(s: RAGState):
    return {"answer": f"I couldn't find a reliable source for this in Northstar's documents (last search: "
                      f"'{s['query']}'). Missing: {s['grade'].missing}. Please clarify or contact Merchant Risk."}


b = StateGraph(RAGState)
for name, fn in [("retrieve", retrieve), ("grade_documents", grade_documents), ("rewrite", rewrite),
                 ("generate", generate), ("give_up", give_up)]:
    b.add_node(name, fn)
b.add_edge(START, "retrieve")
b.add_edge("retrieve", "grade_documents")
b.add_conditional_edges("grade_documents", decide)
b.add_edge("rewrite", "retrieve")
b.add_edge("generate", END)
b.add_edge("give_up", END)
rag_graph = b.compile()


def ask(question: str) -> dict:
    return rag_graph.invoke({"question": question, "query": question, "docs": [], "retries": 0,
                             "grade": None, "answer": ""})


@tool
def search_policies(question: str) -> str:
    """Search Northstar Pay's internal merchant risk policies, SOPs, chargeback & reserve rules, API limits and pricing.
    Returns a cited answer or an explicit 'not found'. Superseded policies are excluded."""
    return ask(question)["answer"]


if __name__ == "__main__":
    for q in ["What's the limit and who can raise it?", "What reserve applies to an iGaming merchant?",
              "How long can a limit increase last?"]:
        out = ask(q)
        print(f"Q: {q}\n  retries: {out['retries']}\n  -> {out['answer'][:400]}\n")

    # Plug into Meridian: the agent chooses when to read policy
    from meridian import build_agent
    from meridian import ALL_TOOLS
    agent = build_agent(tools=ALL_TOOLS + [search_policies])
    res = agent.invoke({"messages": [("user", "CRUX needs a 12% processing limit increase. Who must approve it?")]},
                       {"recursion_limit": 25})
    print("Meridian:", res["messages"][-1].text)