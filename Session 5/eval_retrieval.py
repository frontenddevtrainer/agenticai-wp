# eval_retrieval.py — measure retrieval before you tune it. No LLM needed: just embeddings (Ollama).
# Prereq: python ingest.py (builds the 150 / 500 / 1500 collections).   Run:  python eval_retrieval.py
from golden import GOLDEN
from ingest import open_store

STALE = "merchant-risk-policy-2024-SUPERSEDED"

def score(search, k: int = 3):
    """hit@1: the right document is the FIRST result (what a 1-chunk prompt would see).
    MRR: mean of 1/rank of the first right document within the top k (1.0 = always first).
    stale@k: share of questions where the superseded policy is in the top k (a wrong answer waiting to happen)."""
    hit1, rr, stale, misses = 0, 0.0, 0, []
    for question, expected in GOLDEN:
        sources = [d.metadata["source"] for d in search(question, k)]
        rank = next((i + 1 for i, s in enumerate(sources) if s in expected), None)
        hit1 += rank == 1
        rr += 1 / rank if rank else 0
        stale += STALE in sources
        if rank != 1:
            misses.append((question, sources))
    n = len(GOLDEN)
    return {"hit@1": hit1 / n, "MRR": rr / n, "stale@3": stale / n}, misses

if __name__ == "__main__":
    print(f"{'chunks':>6} {'filter':>12} {'hit@1':>6} {'MRR':>5} {'stale@3':>8}")
    shown = None
    for size in (150, 500, 1500):
        store = open_store(size)
        for current_only in (False, True):
            flt = {"is_current": True} if current_only else None
            m, misses = score(lambda q, k: store.similarity_search(q, k=k, filter=flt))
            print(f"{size:>6} {'current only' if current_only else 'none':>12} {m['hit@1']:>6.0%} {m['MRR']:>5.2f} {m['stale@3']:>8.0%}")
            if size == 500 and current_only:
                shown = misses
    print("\nNot ranked first (500 chars, current only):")
    for question, got in shown or []:
        print(f"  ✗ {question}\n      top 3: {got}")