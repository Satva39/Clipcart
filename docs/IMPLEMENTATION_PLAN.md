# Clipcart 5-Part Implementation Plan

The foundation work in the current base is deliberately excluded from these five parts. Each part is intended to be completed in a separate chat against the same project.

## Part 1 — Customer Storefront

Customer registration/login, Amazon-style storefront structure, home sections, banners consumed from backend configuration, search, categories, filters, sorting, product details, variants, delivery estimate display, recommendations, recently viewed, wishlist, cart, save-for-later, profile, addresses and customer notifications.

## Part 2 — Checkout, Payments & Customer Orders

Cart-to-checkout flow, Razorpay checkout, exact Clipcart fee rules, coupon application, tax rule, order creation/idempotency, payment records, invoice generation/download, order history, current-order view, shipment tracking view, returns/cancellations, notify-me and product reviews/feedback.

Business rules supplied for this project:

- Marketing fee: ₹2 on every purchase.
- Tax: 18% on an order above ₹2,000.
- Maximum tax charged: ₹500.

## Part 3 — Supplier Portal

Supplier registration and ₹50 onboarding payment, business/UPI details, supplier authentication, product CRUD, product images, variant combinations, variant media, SKU management, stock operations, low-stock alerts, supplier order/PO flow, order fulfillment state, earnings, payouts, exports and detailed analytics with date/status/category filters.

## Part 4 — Logistics Portal

Restricted logistics access, instant operational alerts, delivery queue, assignment data, pickup workflow, shipment tracking, out-for-delivery state, delivery confirmation/failure, notes/proof fields and operational reporting.

## Part 5 — Admin Portal, Integration Hardening & Deployment

Private admin authentication, supplier/customer/dealer management, platform aggregates, banner/content management, platform settings, admin product creation, moderation, payout controls, platform notifications, audit logs, observability, automated tests, security review, production environment configuration, Vercel/Render deployment and cross-portal end-to-end verification.

## Completion gate

The project is considered 100% only after all five parts pass functional testing together against one PostgreSQL database and one backend, with real Razorpay test-mode payment verification and production-ready deployment configuration.
