# Clipcart Part 5 — Test Matrix

## Automated checks executed

- Python source compilation for the backend.
- Alembic migration graph validation.
- Admin authorization tests with active/inactive/non-admin accounts.
- Admin customer/supplier/logistics route authorization tests.
- JWT logout/revocation tests.
- Admin password reset token expiry/single-use behavior.
- Admin product ownership boundary tests.
- Negative stock constraint/model tests.
- Frontend production build checks for all four Vite apps where their installed dependencies are available.

## End-to-end acceptance matrix

Customer:
register → login → search → product → variant → cart → checkout → Razorpay test payment → order → invoice → tracking → review

Supplier:
register → configured onboarding fee → active → create product → add variant → stock → receive order → fulfillment → earnings/payout data

Logistics:
login → receive order → pickup → shipment → out for delivery → delivered

Admin:
login → dashboard → supplier management → customer management → logistics management → banners → settings → platform product management → notifications → payout controls → audit log

External live steps require access to the deployed services and test credentials.
