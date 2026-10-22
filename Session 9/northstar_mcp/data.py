"""data.py: Northstar Pay mock data (fictional payment processor). Deterministic so answers are reproducible.

Answer key (verdict rules: >100% OVER_LIMIT, >90% NEAR_LIMIT, else OK):
  ACME: 6.2M EUR x 1.10 + 3.1M USD = 9.92M USD vs 9.5M USD  -> OVER_LIMIT (104.4%)
  BOLT: 1.5M USD / 1.30 + 2.0M GBP = 3.154M GBP vs 5M GBP   -> OK (63.1%)
  CRUX: 650M INR + 2M USD x 85 = 820M INR vs 800M INR       -> OVER_LIMIT (102.5%), chargeback watchlist
"""

MERCHANTS = {
    "ACME": {
        "name": "ACME Electronics Online (fictional)",
        "mcc": "5732",
        "channel": "e-commerce",
        "risk_tier": "Medium",
        "processing_limit": {"amount": 9_500_000, "currency": "USD", "period": "monthly"},
        "settlement_currency": "USD",
        "chargeback_ratio_pct": 0.6,
        "rolling_reserve_pct": 5,
        "mtd_volume": [
            {"batch_id": "B-1001", "method": "card_cnp", "amount": 4_200_000, "currency": "EUR"},
            {"batch_id": "B-1002", "method": "card_cnp", "amount": 3_100_000, "currency": "USD"},
            {"batch_id": "B-1003", "method": "wallet", "amount": 2_000_000, "currency": "EUR"},
        ],
        "kyb_notes": "Annual KYB review due 2026-11-30. No adverse media.",
    },
    "BOLT": {
        "name": "Bolt Travel Ltd (fictional)",
        "mcc": "4722",
        "channel": "e-commerce",
        "risk_tier": "Low",
        "processing_limit": {"amount": 5_000_000, "currency": "GBP", "period": "monthly"},
        "settlement_currency": "GBP",
        "chargeback_ratio_pct": 0.3,
        "rolling_reserve_pct": 0,
        "mtd_volume": [
            {"batch_id": "B-2001", "method": "card_cnp", "amount": 1_500_000, "currency": "USD"},
            {"batch_id": "B-2002", "method": "card_cnp", "amount": 2_000_000, "currency": "GBP"},
        ],
        "kyb_notes": "Enhanced due diligence completed 2026-06.",
    },
    "CRUX": {
        "name": "Crux Gaming Pvt Ltd (fictional)",
        "mcc": "7995",
        "channel": "e-commerce",
        "risk_tier": "High",
        "processing_limit": {"amount": 800_000_000, "currency": "INR", "period": "monthly"},
        "settlement_currency": "INR",
        "chargeback_ratio_pct": 1.2,
        "rolling_reserve_pct": 10,
        "mtd_volume": [
            {"batch_id": "B-3001", "method": "upi", "amount": 650_000_000, "currency": "INR"},
            {"batch_id": "B-3002", "method": "card_cnp", "amount": 2_000_000, "currency": "USD"},
        ],
        "kyb_notes": "Watchlist: chargeback ratio above scheme monitoring threshold (0.9%) since 2026-09.",
    },
}

# Spot rates: 1 unit of base -> quote.
FX = {
    ("EUR", "USD"): 1.10,
    ("GBP", "USD"): 1.30,
    ("USD", "INR"): 85.0,
    ("USD", "JPY"): 150.0,
    ("USD", "CHF"): 0.88,
}

AS_OF = "2026-10-02T16:00Z"


def fx_rate(base: str, quote: str) -> float:
    """Direct, inverted, or via-USD cross rate. Raises LookupError if impossible."""
    if base == quote:
        return 1.0
    if (base, quote) in FX:
        return FX[(base, quote)]
    if (quote, base) in FX:
        return round(1 / FX[(quote, base)], 8)
    if base != "USD" and quote != "USD":
        return round(fx_rate(base, "USD") * fx_rate("USD", quote), 8)
    raise LookupError(f"no rate for {base}/{quote}")


def expected_verdict(merchant_id: str) -> dict:
    """Ground truth used by tests and evals (Day 8)."""
    m = MERCHANTS[merchant_id]
    cur = m["processing_limit"]["currency"]
    total = sum(b["amount"] * fx_rate(b["currency"], cur) for b in m["mtd_volume"])
    pct = total / m["processing_limit"]["amount"] * 100
    verdict = "OVER_LIMIT" if pct > 100 else "NEAR_LIMIT" if pct > 90 else "OK"
    return {"merchant_id": merchant_id, "mtd_volume": round(total, 2), "currency": cur,
            "utilisation_pct": round(pct, 1), "verdict": verdict}


if __name__ == "__main__":
    for mid in MERCHANTS:
        print(expected_verdict(mid))