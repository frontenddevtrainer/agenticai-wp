# hybrid.py — keyword search (BM25) + vector search, merged with Reciprocal Rank Fusion. Then measure it.
# Prereq: python ingest.py, pip install rank-bm25.   Run:  python hybrid.py
import re
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from eval_retrieval import score
from ingest import open_store

FILTER = {"is_current": True}
tokenize = lambda text: re.findall(r"[a-z0-9]+", text.lower())

def with_context(chunk: Document) -> str:
    """Contextual chunk header: the chunk's document title and section, prepended before indexing."""
    return f"{chunk.metadata.get('h1', chunk.metadata['source'])} › {chunk.metadata.get('section', '')}\n{chunk.page_content}"

def build(size: int = 150, contextual: bool = False):
    """Three search functions over the SAME chunks (one Chroma collection): vector, keyword and hybrid."""
    store = open_store(size)
    raw = store.get(where=FILTER)
    chunks = [Document(text, metadata=meta) for text, meta in zip(raw["documents"], raw["metadatas"])]
    bm25 = BM25Okapi([tokenize(with_context(c) if contextual else c.page_content) for c in chunks])

    def vector_search(question: str, k: int) -> list[Document]:
        return store.similarity_search(question, k=k, filter=FILTER)

    def keyword_search(question: str, k: int) -> list[Document]:   # exact words: 'MDR', '7995', '429', 'four-eyes'
        scores = bm25.get_scores(tokenize(question))
        return [chunks[i] for i in sorted(range(len(chunks)), key=lambda i: -scores[i])[:k]]

    def hybrid_search(question: str, k: int, depth: int = 10, c: int = 60) -> list[Document]:
        """Reciprocal Rank Fusion: score = sum of 1 / (c + rank) over both lists. It uses ranks, not raw scores,
        so two scoring scales that aren't comparable (cosine vs BM25) combine with no tuning."""
        fused: dict[str, tuple[float, Document]] = {}
        for results in (vector_search(question, depth), keyword_search(question, depth)):
            for rank, doc in enumerate(results, start=1):
                prev = fused.get(doc.page_content, (0.0, doc))[0]
                fused[doc.page_content] = (prev + 1 / (c + rank), doc)
        return [doc for _, doc in sorted(fused.values(), key=lambda x: -x[0])[:k]]

    return vector_search, keyword_search, hybrid_search

if __name__ == "__main__":
    vector, keyword, hybrid = build(150)
    print(f"{'method':>8} {'hit@1':>6} {'MRR':>5}")
    for name, search in [("vector", vector), ("keyword", keyword), ("hybrid", hybrid)]:
        m, misses = score(search)
        print(f"{name:>8} {m['hit@1']:>6.0%} {m['MRR']:>5.2f}   misses: {[q[:38] for q, _ in misses]}")