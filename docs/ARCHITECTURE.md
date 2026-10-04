# Clipcart Architecture

Clipcart is a four-portal marketplace backed by one Flask API and one PostgreSQL database.

```text
Clipcart/
├── frontend/             # Customer storefront
├── supplier-frontend/    # Supplier portal
├── logistics-frontend/   # Restricted delivery portal
├── admin-frontend/       # Private admin portal
├── backend/              # Shared Flask API
├── database/             # SQL reference/seed material
├── docs/                 # Architecture and delivery plan
└── README.md
```

## Runtime model

All four frontends call the same `/api` backend. The backend owns authentication, authorization, pricing rules, inventory, order state, payments, payouts, notifications and document generation.

The database is PostgreSQL (Neon in deployment) and Cloudinary is used for product media. Razorpay is the payment gateway for Clipcart-collected payments.

## Portal boundaries

**Customer** can browse the public catalog and access only their own account data, cart, wishlist, orders, invoices, notifications and reviews.

**Supplier** can access only their own catalog, variants, inventory, supplier orders, analytics and payout information.

**Logistics manager** is a restricted operational role. It can access delivery assignments and status transitions required for fulfillment, but not unrelated customer account administration.

**Admin** is private and role-protected. The admin portal is intended for platform-level counts, supplier/customer/dealer management, moderation/configuration and platform controls. Customer order history and supplier-specific product catalogs are not part of the admin visibility model.

## Source of truth

Business state is always read from PostgreSQL through the backend. Frontends do not invent order, inventory, payment or supplier state. Local storage is used only for client-side session tokens/user cache and temporary UI state.

## API conventions

All API endpoints use `/api`. Responses use:

```json
{
  "success": true,
  "message": "...",
  "data": {}
}
```

Errors use the same envelope with `success: false` and `data: null`.

Authentication uses JWT access/refresh tokens. The JWT role claim is derived from the account's actual role; clients must never hard-code a role into a token.
