# Clipcart Deployment Baseline

The deployment target is one backend plus four independent frontend deployments.

## Frontends

Deploy each of these folders as its own Vercel project:

- `frontend`
- `supplier-frontend`
- `logistics-frontend`
- `admin-frontend`

Each contains a `vercel.json` SPA rewrite so React Router deep links resolve to `index.html`.

Set `VITE_API_URL` to the production backend API URL. The customer portal also requires `VITE_RAZORPAY_KEY_ID`.

## Backend

`backend/render.yaml` provides the Render service baseline. Configure all secrets through the hosting provider's environment variables rather than committing a `.env` file.

At minimum configure:

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_URL`
- `CORS_ORIGINS` with all four production frontend origins
- `CLIPCART_ADMIN_EMAIL`
- Razorpay credentials
- Cloudinary credentials
- email provider credentials

## Production checks

1. Run database migrations against the production database.
2. Confirm `/api/health` returns a successful response.
3. Confirm every frontend points to the same API.
4. Confirm Vercel deep links work for customer, supplier, logistics and admin routes.
5. Use Razorpay test mode until Part 2/3 payment flows are fully verified.
6. Enable production secrets only through environment configuration.
