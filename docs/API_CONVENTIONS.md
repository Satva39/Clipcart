# Clipcart API Conventions

## Endpoint naming

Use nouns for resources and explicit actions only when the action cannot be represented as a normal resource state change.

Examples:

- `GET /api/products`
- `GET /api/products/:id`
- `POST /api/cart/items`
- `PATCH /api/cart/items/:id`
- `POST /api/checkout/sessions`
- `POST /api/orders`

## Authentication

Send:

```text
Authorization: Bearer <access_token>
```

Refresh tokens are used only to obtain a new access token.

## Response envelope

```json
{
  "success": true,
  "message": "Human readable message",
  "data": {}
}
```

Do not expose SQLAlchemy objects directly from routes. Return explicit JSON-safe DTOs.

## Money

Money is represented in INR and persisted using fixed-precision numeric database types. Do not use floating-point arithmetic for persisted monetary values or payment verification amounts.

## Idempotency

Payment capture and order creation must be idempotent. A repeated client retry must not create duplicate orders, duplicate payment records or duplicate inventory deductions.
