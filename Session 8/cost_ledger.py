"""Day 8 Lab 3 (Part B): per-run cost ledger with a budget (fails fast when exceeded).

Usage: ledger = CostLedger(budget_usd=0.50); graph.invoke(..., config={"callbacks": [ledger]}); ledger.print_report()
"""
from langchain_core.callbacks import BaseCallbackHandler

PRICES = {  # USD per 1M tokens, OpenRouter model ids (verified 2026-10-05; re-check openrouter.ai/models)
    "anthropic/claude-opus-5.5": {"in": 4.00, "out": 20.00, "cache_read": 0.20},
    "anthropic/claude-sonnet-5.5": {"in": 2.00, "out": 10.00, "cache_read": 0.20},
    "anthropic/claude-haiku-4.5": {"in": 1.00, "out": 5.00, "cache_read": 0.10},
}


class BudgetExceeded(RuntimeError):
    pass


class CostLedger(BaseCallbackHandler):
    def __init__(self, budget_usd: float = 1.00):
        self.rows, self.total, self.budget = [], 0.0, budget_usd

    def on_llm_end(self, response, **kwargs):
        for gen in response.generations:
            for g in gen:
                msg = getattr(g, "message", None)
                if not msg or not getattr(msg, "usage_metadata", None):
                    continue
                meta = msg.response_metadata or {}
                model = meta.get("model_name") or meta.get("model") or "?"
                price = next((v for k, v in PRICES.items() if str(model).startswith(k)), None)
                u = msg.usage_metadata
                cache = (u.get("input_token_details") or {}).get("cache_read", 0) or 0
                cost = 0.0 if price is None else (
                    (u["input_tokens"] - cache) * price["in"] + cache * price["cache_read"]
                    + u["output_tokens"] * price["out"]) / 1e6
                self.rows.append({"model": model, "in": u["input_tokens"], "cache_read": cache,
                                  "out": u["output_tokens"], "usd": round(cost, 5),
                                  "priced": price is not None})
                self.total += cost
                if self.total > self.budget:
                    raise BudgetExceeded(f"Run budget exceeded: ${self.total:.3f} > ${self.budget:.2f}")

    def print_report(self) -> None:
        for r in self.rows:
            print(r)
        unpriced = {r["model"] for r in self.rows if not r["priced"]}
        print(f"TOTAL ${self.total:.4f} over {len(self.rows)} LLM calls"
              + (f"  (no price for: {sorted(unpriced)} -> counted as $0, e.g. local models)" if unpriced else ""))