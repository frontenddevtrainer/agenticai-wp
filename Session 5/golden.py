# golden.py — questions with the document that MUST be retrieved to answer them correctly.
# Small on purpose: 12 good questions beat 500 vague ones. Add a case every time retrieval fails in real use.
GOLDEN = [
    ("Who approves a 10% limit increase for a High-tier merchant?", ["merchant-risk-policy-2026"]),
    ("How long can a temporary limit increase last?", ["merchant-risk-policy-2026"]),          # 2024 policy says 60 days: a trap
    ("What happens when a merchant goes above 100% of its limit?", ["merchant-risk-policy-2026"]),
    ("What reserve do we hold for a betting merchant?", ["rolling-reserve-rules"]),            # 'betting' vs 'MCC 7995'
    ("A merchant has a 1% chargeback ratio. What's its status?", ["chargeback-and-disputes-policy"]),
    ("How many days do we have to send dispute evidence?", ["chargeback-and-disputes-policy"]),
    ("How many refund requests per second can a merchant make?", ["api-rate-limits"]),
    ("What is the MDR on a domestic credit card payment?", ["pricing-sheet-2026-q4"]),
    ("What do we do after a limit increase is approved?", ["sop-limit-increase"]),
    ("Which FX rate is used to convert month-to-date volume?", ["merchant-risk-policy-2026"]),
    ("How much do we charge a merchant per chargeback?", ["pricing-sheet-2026-q4"]),          # chargeback fee lives in PRICING
    ("Can a merchant on the chargeback watchlist get a limit increase?", ["merchant-risk-policy-2026", "chargeback-and-disputes-policy"]),
]