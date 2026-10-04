# Clipcart Part 5 — Production Deployment

## Runtime topology

Customer frontend, supplier frontend, logistics frontend and private admin frontend are deployed as four independent Vercel projects. All four consume the same Flask API. PostgreSQL runs on Neon. Product media is stored in Cloudinary. Razorpay handles payments.

## Environment variables

Backend production variables:

- `FLASK_ENV=production`
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_URL`
- `CORS_ORIGINS` — comma-separated customer, supplier, logistics and admin Vercel origins
- `CLIPCART_ADMIN_EMAIL`
- `CLIPCART_ADMIN_PORTAL_URL`
- `ADMIN_PASSWORD_RESET_TTL`
- Razorpay credentials
- Cloudinary credentials
- Resend credentials
- optional DB pool sizing

Never commit `.env` files, secrets, passwords, Razorpay secrets or Cloudinary API secrets.

Frontend variables:

- `VITE_API_URL=https://<api-domain>/api`
- Customer frontend also needs its public Razorpay key ID.

## Database release

1. Create a Neon PostgreSQL database.
2. Set `DATABASE_URL`.
3. Run `flask db upgrade`.
4. Confirm the migration head is `a5b6c7d8e9f0`.
5. Create/update the private admin with `python create_admin.py` after setting `CLIPCART_ADMIN_EMAIL`.
6. Verify `/api/health` reports both API and database as healthy.

Do not reset the production database or recreate migrations on top of existing production data.

## Vercel

For each frontend project set the correct `VITE_API_URL` and use the repository subdirectory as the project root:

- `frontend/`
- `supplier-frontend/`
- `logistics-frontend/`
- `admin-frontend/`

Each Vercel project already contains an SPA rewrite to `index.html` so React Router deep links resolve.

## Render

Deploy the `backend/` directory as a Python web service with:

`pip install -r requirements.txt`

and:

`gunicorn --bind 0.0.0.0:$PORT run:app`

Health check:

`/api/health`

Run database migrations as an explicit release/deployment step before serving the new application version.

## Production verification

After deployment, verify:

- `GET /api/health` returns HTTP 200 and `database=ok`.
- Customer, supplier, logistics and admin origins are accepted by CORS.
- Admin login works only with the configured admin identity.
- Customer order history cannot be accessed from admin endpoints.
- Supplier catalog internals are not returned by admin product endpoints.
- A customer can complete a Razorpay test transaction in the configured test environment.
- Supplier registration fee is read from `platform_settings`.
- A banner created in admin appears on the customer home page.
- A public announcement created in admin appears on the customer home page.
- Admin settings change checkout calculations after the backend reload.
- React Router refreshes work on all four frontends.
- No production secrets appear in browser source, repository files or logs.

The chat/project environment does not have access to the user's Vercel, Render, Neon, Cloudinary or Razorpay accounts, so external deployment and live payment verification must be completed in those accounts.
