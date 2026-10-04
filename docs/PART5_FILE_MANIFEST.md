# Clipcart Part 5 File Manifest

## Added
- `backend/app/modules/admin/models.py`
- `backend/app/modules/admin/authorization.py`
- `backend/app/modules/admin/services.py`
- `backend/migrations/versions/a5b6c7d8e9f0_part5_admin_controls.py`
- `backend/.env.example`
- `backend/tests/test_part5_security.py`
- `backend/tests/test_part5_static.py`
- `docs/PART5_DEPLOYMENT.md`
- `docs/PART5_SECURITY.md`
- `docs/PART5_TEST_PLAN.md`
- `docs/PART5_RELEASE.md`
- `docs/PART5_FILE_MANIFEST.md`

## Changed
- Backend: `app/__init__.py`, `config.py`, `core/business_rules.py`, `core/decorators.py`, `core/errors.py`, `core/jwt.py`, `core/security.py`, account login service, category/coupon/payment/payout/product/variant/store/supplier-order/supplier-registration/upload modules, health routes, invoice service, admin routes/services/models, auth model, communication email service, deployment/requirements.
- Customer frontend: admin-configured home banners/announcement integration, CSS, environment template.
- Supplier frontend: registration fee/password UI and environment template.
- Logistics frontend: environment template.
- Admin frontend: authentication/session layer, protected routing, dashboard, analytics, customer/supplier/logistics management, banners, settings, products, payouts, notifications, audit log, profile and styling.
- Deployment configs: Render and Vercel environment templates/configuration.

## Deleted
- `admin-frontend/src/pages/Orders.jsx`
- `admin-frontend/src/pages/OrderDetails.jsx`
- `admin-frontend/src/services/orderService.js`
- unused `backend/app/modules/product_wizard/` module
- local `.env` files from the release copy (credentials are not shipped)
