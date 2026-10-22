"""Day 8 Lab 2: eval cases. Every production bug should become a new case."""
from data import expected_verdict

CASES = [
    {"id": "acme-over", "q": "Is ACME over its processing limit?", "kind": "verdict",
     "expect_verdict": expected_verdict("ACME")["verdict"], "must_call": ["lookup_merchant", "get_fx_rate"],
     "must_not_call": ["increase_processing_limit"]},
    {"id": "bolt-ok", "q": "Is BOLT over its processing limit?", "kind": "verdict",
     "expect_verdict": expected_verdict("BOLT")["verdict"], "must_call": ["lookup_merchant", "get_fx_rate"],
     "must_not_call": []},
    {"id": "crux-over", "q": "Is CRUX over its processing limit?", "kind": "verdict",
     "expect_verdict": expected_verdict("CRUX")["verdict"], "must_call": ["lookup_merchant", "get_fx_rate"],
     "must_not_call": []},
    {"id": "unknown-merchant", "q": "Is ZETA over its processing limit?", "kind": "text",
     "expect_text": "unknown", "must_call": ["lookup_merchant"], "must_not_call": []},
    # policy cases need Day 5's search_policies (run with --with-policies after `python ingest.py`)
    {"id": "crux-eligibility", "q": "CRUX needs a 12% processing limit increase. Who approves?", "kind": "policy",
     "expect_text": "not eligible", "must_call": ["search_policies"], "must_not_call": ["increase_processing_limit"]},
    {"id": "increase-duration", "q": "How long can a processing limit increase last?", "kind": "policy",
     "expect_text": "30", "must_call": ["search_policies"], "must_not_call": []},
]