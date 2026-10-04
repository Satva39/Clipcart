# Clipcart Security Boundaries

## Roles

The backend recognizes four roles:

- `CUSTOMER`
- `SUPPLIER`
- `LOGISTICS_MANAGER`
- `ADMIN`

Authorization is enforced on the backend. Frontend route guards improve UX but are not the security boundary.

## Portal isolation

The customer, supplier, logistics and admin portals use separate session keys so a token from one portal is never assumed to be a valid portal session for another.

The backend still validates the JWT role on every protected operation.

## Admin identity

The private administrator identity is configured through `CLIPCART_ADMIN_EMAIL`. The email is not hard-coded in frontend source or backend code.

## Secrets

Real credentials must live only in untracked `.env` files or deployment secret stores. The repository contains `.env.example` templates only.

Never commit:

- Razorpay secret keys
- Database passwords/connection strings
- Cloudinary API secrets
- Email provider API keys
- JWT/Flask signing secrets

## Payment rule

Payment verification is server-side. A successful client-side Razorpay callback is never considered sufficient without signature verification against the server-side Razorpay credentials.

## Data visibility

The admin visibility contract intentionally excludes customer order history and supplier-specific product listings. Platform aggregate counts can be exposed without exposing those records.
