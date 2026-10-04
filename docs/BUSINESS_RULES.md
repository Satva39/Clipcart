# Clipcart Business Rules

These rules are shared across all portals and should be implemented on the backend, never only in frontend calculations.

| Rule | Value |
| --- | ---: |
| Supplier registration fee | ₹50.00 |
| Marketing fee | ₹2.00 per customer order |
| Tax trigger | Order/taxable base strictly above ₹2,000.00 |
| Tax rate | 18% |
| Maximum tax | ₹500.00 |

The backend utility in `backend/app/core/business_rules.py` exposes these values using `Decimal` arithmetic. The checkout implementation must choose and document the exact taxable base and then use that utility consistently for checkout, payment amount, order records and invoice totals.

The supplier registration fee and customer order payments are separate payment flows and must have separate gateway receipts/idempotency keys.
