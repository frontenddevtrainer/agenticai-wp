# grounded.py — answers you can check: numbered sources, citations verified in code, and a groundedness grader.
# Prereq: python ingest.py.   Run:  python grounded.py
from pydantic import BaseModel, Field
from hybrid import build
from llm import MODEL_FAST, chat_model

class CitedAnswer(BaseModel):
    answer: str = Field(description="The answer, or exactly 'NOT FOUND' if the sources don't contain it")
    citations: list[int] = Field(description="Numbers of the sources that support the answer, e.g. [1, 3]")

class Groundedness(BaseModel):
    grounded: bool = Field(description="True only if EVERY claim in the answer is stated in the cited sources")
    unsupported: list[str] = Field(description="Claims in the answer that the sources don't support")

# 500-character chunks: big enough to keep a table row with its header (150 splits them; see Lab 4).
_, _, hybrid_search = build(500)

writer = chat_model(max_tokens=2000).with_structured_output(CitedAnswer)
judge = chat_model(MODEL_FAST, max_tokens=1000).with_structured_output(Groundedness)   # a different, cheaper model

def ask(question: str) -> dict:
    docs = hybrid_search(question, k=4)
    sources = "\n\n".join(f"[{i}] ({d.metadata['source']})\n{d.page_content}" for i, d in enumerate(docs, start=1))
    
    # [1] (abc.docx) this is the page content
    # [2] (abc.docx) this is the page content
    
    out = writer.invoke(
        "Answer the question using ONLY the numbered sources. Cite the numbers you used. "
        "If the sources don't contain the answer, reply exactly NOT FOUND with no citations.\n\n"
        f"{sources}\n\nQuestion: {question}")

    # 1. Check in CODE: every citation must point at a source we actually gave the model.
    valid = [c for c in out.citations if 1 <= c <= len(docs)]
    if out.answer.strip() == "NOT FOUND":
        return {"answer": "I couldn't find this in Northstar's documents.", "status": "not found", "sources": []}
    if not valid:
        return {"answer": out.answer, "status": "REJECTED: no valid citations", "sources": []}

    # 2. Check with a JUDGE: is each claim supported by the cited text?
    cited = "\n\n".join(f"[{c}] {docs[c - 1].page_content}" for c in valid)
    # Give the judge the QUESTION too: a short answer like "Head of Merchant Risk" is only checkable in context.
    verdict = judge.invoke(f"Sources:\n{cited}\n\nQuestion: {question}\nAnswer: {out.answer}\n\n"
                           "As an answer to this question, is every claim supported by the sources?")
    status = "grounded" if verdict.grounded else f"NOT GROUNDED: {verdict.unsupported}"
    return {"answer": out.answer, "status": status, "sources": sorted({docs[c - 1].metadata["source"] for c in valid})}

if __name__ == "__main__":
    for q in ["Who approves a 40% limit increase for a High-tier merchant?",
              "How long can a temporary limit increase last?",
              "What is Northstar's limit for UPI refunds in Japan?"]:          # not in any document
        r = ask(q)
        print(f"Q: {q}\nA: {r['answer']}\n   [{r['status']}] {r['sources']}\n")