---
doc_type: developer_guide
effective_date: 2026-01-01
owner: Platform Engineering
---
# Payments API Rate Limits
Each merchant API key is limited to 100 requests/second for payment creation and 20 requests/second for refunds.
Exceeding the limit returns HTTP 429. Rate limits are unrelated to merchant processing limits.
Refunds are also limited to the original captured amount (no over-refunds).