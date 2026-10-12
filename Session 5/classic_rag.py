"""Day 5 Lab 2: textbook RAG chain in LCEL, and its failure modes.

Prereq: python ingest.py.   Run: python classic_rag.py
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from ingest import open_store
from llm import chat_model

vs = open_store(500)
retriever = vs.as_retriever(search_kwargs={"k": 3})          # no "current only" filter, on purpose


def format_docs(docs) -> str:
    return "\n\n".join(f"[{d.metadata['source']} §{d.metadata.get('section', '-')}]\n{d.page_content}" for d in docs)


prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer using ONLY the context. Cite sources in [brackets].\n\nContext:\n{context}"),
    ("human", "{question}"),
])
rag = ({"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | chat_model(max_tokens=4000) | StrOutputParser())

QUESTIONS = ["Who approves a 7% limit increase for a Low-risk-tier merchant?",   # should work
             "How long can a limit increase last?",                              # superseded-doc trap
             "What's the limit and who can raise it?",                           # AMBIGUOUS
             "What reserve applies to an iGaming merchant?"]                     # vocabulary gap

if __name__ == "__main__":
    for q in QUESTIONS:
        print("Q:", q, "\nA:", rag.invoke(q), "\n")