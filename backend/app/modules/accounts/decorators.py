"""Compatibility exports for account-level authorization decorators."""

from app.core.decorators import (
    admin_required,
    active_supplier_required,
    active_logistics_required,
    customer_or_supplier_required,
    customer_required,
    logistics_required,
    role_required,
    supplier_required,
)

__all__ = [
    "role_required",
    "active_supplier_required",
    "active_logistics_required",
    "customer_or_supplier_required",
    "customer_required",
    "supplier_required",
    "admin_required",
    "logistics_required",
]
