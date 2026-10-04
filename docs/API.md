# Clipcart API Documentation

## Base URL

Development:

```
http://127.0.0.1:5000/api
```

Production:

```
https://your-domain.com/api
```

---

## Authentication

* JWT Authentication
* Role-based access

  * Customer
  * Supplier
  * Admin

---

## Main API Groups

* Authentication
* Customers
* Suppliers
* Products
* Categories
* Search
* Cart
* Wishlist
* Orders
* Payments
* Reviews
* Notifications
* Reports
* Exports
* Admin

---

## Response Format

Success

```json
{
    "success": true,
    "message": "",
    "data": {}
}
```

Error

```json
{
    "success": false,
    "message": "",
    "errors": []
}
```
