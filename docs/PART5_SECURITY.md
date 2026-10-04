# Clipcart Part 5 — Security Boundaries

## Private admin

Admin access is restricted by all of:

- configured `CLIPCART_ADMIN_EMAIL`
- JWT role `ADMIN`
- JWT portal claim `admin`
- database account role `ADMIN`
- database account status `ACTIVE`

Admin frontend stores its short-lived access and refresh tokens in `sessionStorage`, not persistent local storage. Protected requests are backend-validated, and logout revokes the active JWT.

Password reset links are signed, time-limited and invalidated after a password update because the account update timestamp changes. Reset tokens are never written to logs.

## Data boundaries

Admin endpoints return platform aggregates, permitted account-management fields and operational payout identifiers. They do not provide customer order history and do not provide unrestricted supplier catalog internals.

Platform products are isolated to products owned by the configured admin account.

## Uploads

The shared image upload endpoint is restricted to active suppliers or the authorized admin. Unsupported file types are rejected.

## Business settings

Marketing fee, tax threshold, tax rate, tax cap and supplier registration fee are database-backed platform settings. Frontends do not define those business rules.

## Payments

Checkout and supplier registration continue to verify Razorpay signatures, fetched gateway order/payment data, amount and currency. Payment records have unique gateway order/session/transaction relationships, and critical verification paths use database row locks.

## Inventory

Checkout locks the product/variant rows before stock deduction. Cancellation restores stock within the transaction. Database check constraints prevent negative stock values.

Supplier payout creation serializes on the payout-account row before checking available balance and creating a payout record.

## Audit

Important admin mutations create an `admin_audit_logs` row with:

- admin account ID
- action
- resource type
- resource ID
- non-secret metadata
- timestamp

No password, token, gateway secret or bank account number is written to the audit metadata.

## Production logging

Unexpected errors are logged as backend events without echoing raw exception text into API responses. Sensitive request bodies are not logged by the Part 5 code.
