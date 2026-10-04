# Clipcart Base Baseline

The base cleanup is the shared foundation for all later parts.

## Included now

- Four separate React/Vite portals remain intact.
- Flask app factory and backend configuration are centralized.
- CORS is environment-driven instead of hard-coded to a small set of development URLs.
- API JSON error handling is standardized.
- JWT generation now uses the account's real role instead of a hard-coded supplier role.
- Reusable backend role decorators exist for customer, supplier, admin and logistics-manager access.
- Admin identity is environment-configured instead of hard-coded in source.
- Admin portal no longer uses the stale Vite starter `App.jsx`.
- Admin portal client protection is role-based instead of email-hard-coded in frontend code.
- Supplier API clients are consolidated onto one environment-driven client.
- Customer app now has a single provider root with React Query + Cart context.
- Frontend API URLs are environment-driven across all portals.
- Real `.env` files and Python/Node dependency folders are excluded from the new clean baseline.
- Runtime/security/deployment conventions are documented.

## Intentionally deferred

The five implementation parts handle the actual business features. The base does not try to partially implement the customer, supplier, logistics or admin feature sets so those parts can be completed cleanly without having to undo half-finished work.
