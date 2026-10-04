# Clipcart

Clipcart is a multi-vendor e-commerce marketplace with four separate portals backed by one Flask API and one PostgreSQL database.

## Portals

1. `frontend/` — customer storefront
2. `supplier-frontend/` — supplier portal
3. `logistics-frontend/` — restricted logistics portal
4. `admin-frontend/` — private admin portal

## Backend

`backend/` is the single source of truth for authentication, authorization, catalog, inventory, cart, checkout, orders, payments, supplier payouts, delivery state, notifications and invoices.

## Stack

- React + Vite + JavaScript/JSX
- Flask + SQLAlchemy + Flask-Migrate + JWT
- Neon PostgreSQL
- Cloudinary for product media
- Razorpay for Clipcart-collected payments
- Vercel for frontends and Render/Railway for the API

## Local setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Populate `.env` with real development values before starting the backend.

### Customer frontend

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

### Supplier frontend

```powershell
cd supplier-frontend
npm install
copy .env.example .env
npm run dev
```

### Logistics frontend

```powershell
cd logistics-frontend
npm install
copy .env.example .env
npm run dev
```

### Admin frontend

```powershell
cd admin-frontend
npm install
copy .env.example .env
npm run dev
```

## Database migrations

The project keeps Flask-Migrate revision files under `backend/migrations`. Create/update the development database with the migration workflow used for the active environment; do not manually edit a production database to match frontend expectations.

## Delivery plan

See `docs/IMPLEMENTATION_PLAN.md` for the five implementation parts that follow this foundation.

See `docs/SECURITY_BOUNDARIES.md` for portal isolation and data-visibility rules.
