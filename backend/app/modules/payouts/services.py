from app.extensions import db
from app.modules.orders.models import Order
from app.modules.order_items.models import OrderItem
from app.modules.products.models import Product
from app.modules.notifications.enums import NotificationType
from app.modules.notifications.services import NotificationService

from .models import (
    SupplierPayoutAccount,
    SupplierPayout,
)

from datetime import datetime
from uuid import uuid4
from sqlalchemy import func


class PayoutService:

    @staticmethod
    def get_account(account_id):
        return SupplierPayoutAccount.query.filter_by(account_id=account_id).first()

    @staticmethod
    def save_account(account_id, data):

        payout_account = PayoutService.get_account(account_id)

        if payout_account is None:
            payout_account = SupplierPayoutAccount(account_id=account_id)

            db.session.add(payout_account)

        payout_account.holder_name = str(
            data.get("holder_name", payout_account.holder_name or "")
        ).strip()
        payout_account.bank_name = (
            str(data.get("bank_name", payout_account.bank_name or "")).strip() or None
        )

        # The GET endpoint returns only a masked account number. An empty account_number
        # on update therefore means "leave the stored value unchanged", not "erase it".
        if "account_number" in data:
            incoming_account = str(data.get("account_number") or "").strip()
            if incoming_account:
                payout_account.account_number = incoming_account
        if "ifsc" in data:
            incoming_ifsc = str(data.get("ifsc") or "").strip().upper()
            if incoming_ifsc:
                payout_account.ifsc = incoming_ifsc
        if "upi_id" in data:
            incoming_upi = str(data.get("upi_id") or "").strip().lower()
            if incoming_upi:
                payout_account.upi_id = incoming_upi

        payout_account.is_verified = False

        if not payout_account.holder_name:
            raise ValueError("Account holder name is required.")

        if not payout_account.account_number and not payout_account.upi_id:
            raise ValueError("Bank account or UPI ID is required.")
        if payout_account.account_number and not payout_account.ifsc:
            raise ValueError("IFSC is required when a bank account is provided.")

        db.session.commit()

        return payout_account

    @staticmethod
    def get_available_balance(account_id):
        delivered_sales = (
            db.session.query(func.coalesce(func.sum(OrderItem.subtotal), 0))
            .join(Product, Product.id == OrderItem.product_id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(
                Product.seller_id == account_id,
                Order.status == "DELIVERED",
            )
            .scalar()
        ) or 0

        allocated = (
            db.session.query(func.coalesce(func.sum(SupplierPayout.amount), 0))
            .filter(
                SupplierPayout.account_id == account_id,
                SupplierPayout.status.in_(["PENDING", "PROCESSING", "PAID"]),
            )
            .scalar()
        ) or 0

        return max(0.0, float(delivered_sales) - float(allocated))

    @staticmethod
    def create_payout(account_id, amount):

        payout_account = (
            SupplierPayoutAccount.query.filter_by(account_id=account_id)
            .with_for_update()
            .first()
        )

        if not payout_account:
            raise ValueError("Please add payout account details first.")

        if not payout_account.is_verified:
            raise ValueError("Payout account is not verified yet.")

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValueError("Invalid payout amount.")

        if amount <= 0:
            raise ValueError("Payout amount must be greater than zero.")

        available = PayoutService.get_available_balance(account_id)

        if amount > available:
            raise ValueError("Requested payout exceeds your available balance.")

        payout = SupplierPayout(
            account_id=account_id,
            payout_account_id=payout_account.id,
            amount=amount,
            status="PENDING",
        )

        db.session.add(payout)
        db.session.flush()
        NotificationService.create(
            account_id=account_id,
            title="Payout request submitted",
            message=f"Your payout request for ₹{amount:,.2f} is pending processing.",
            notification_type=NotificationType.PAYMENT,
            dedupe_key=f"supplier-payout:{payout.id}:submitted",
            commit=False,
        )
        db.session.commit()

        return payout

    @staticmethod
    def get_payouts(account_id):

        return (
            SupplierPayout.query.filter_by(account_id=account_id)
            .order_by(SupplierPayout.created_at.desc())
            .all()
        )

    @staticmethod
    def verify_account(payout_account_id):

        account = SupplierPayoutAccount.query.filter_by(id=payout_account_id).first()

        if not account:
            raise ValueError("Payout account not found.")

        account.is_verified = True

        db.session.commit()

        return account

    @staticmethod
    def process_payout(
        payout_id,
        status,
    ):
        payout = SupplierPayout.query.filter_by(id=payout_id).with_for_update().first()

        if not payout:
            raise ValueError("Payout request not found.")

        status = str(status).upper()

        if status not in {
            "PROCESSING",
            "PAID",
            "FAILED",
        }:
            raise ValueError("Invalid payout status.")

        if payout.status == "PAID":
            raise ValueError("This payout has already been completed.")

        if status == "PAID":
            payout.reference_id = (
                payout.reference_id or f"CLP-PAY-{uuid4().hex[:12].upper()}"
            )

            payout.processed_at = datetime.utcnow()

        payout.status = status

        NotificationService.create(
            account_id=payout.account_id,
            title="Payout updated",
            message=f"Payout ₹{float(payout.amount):,.2f} is now {status.lower()}.",
            notification_type=NotificationType.PAYMENT,
            dedupe_key=f"supplier-payout:{payout.id}:status:{status}",
            commit=False,
        )
        db.session.commit()

        return payout
