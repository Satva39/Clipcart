from decimal import Decimal

from app import create_app
from app.extensions import db
from app.modules.accounts.models import Account
from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.admin.services import AdminNotificationService
from app.modules.payments.models import Payment
from app.modules.seller_verification.models import SellerVerification
from app.services.razorpay_service import RazorpayService
from app.core.business_rules import get_supplier_registration_fee


def _payment_matches(payment, order_id, expected_paise):
    return (
        payment.get("order_id") == order_id
        and payment.get("currency", "INR") == "INR"
        and int(payment.get("amount", 0)) == expected_paise
        and payment.get("status") == "captured"
    )


def main():
    app = create_app()
    with app.app_context():
        email = input("Supplier email to recover: ").strip().lower()
        if not email:
            raise SystemExit("Supplier email is required.")

        account = Account.query.filter_by(email=email).first()
        if account is None:
            raise SystemExit("No account found for that email.")
        if account.role != UserRole.SUPPLIER:
            raise SystemExit("The account is not a supplier account.")

        verification = SellerVerification.query.filter_by(account_id=account.id).first()
        if (
            account.status == UserStatus.ACTIVE
            and verification
            and verification.registration_fee_paid
        ):
            print("Supplier registration is already active. No changes made.")
            return

        payment_record = (
            Payment.query.filter_by(
                account_id=account.id,
                payment_type="SUPPLIER_REGISTRATION",
                gateway="RAZORPAY",
            )
            .filter(Payment.gateway_order_id.isnot(None))
            .order_by(Payment.created_at.desc())
            .first()
        )
        if payment_record is None:
            raise SystemExit(
                "No supplier registration payment order found for this account."
            )

        expected_paise = int(
            Decimal(str(get_supplier_registration_fee())) * Decimal("100")
        )
        order_id = payment_record.gateway_order_id
        order = RazorpayService.get_order(order_id)

        if (
            int(order.get("amount", 0)) != expected_paise
            or order.get("currency", "INR") != "INR"
        ):
            raise SystemExit(
                "The stored Razorpay order does not match the configured registration fee."
            )

        gateway_items = RazorpayService.get_order_payments(order_id).get("items", [])
        captured = [
            item
            for item in gateway_items
            if _payment_matches(item, order_id, expected_paise)
        ]

        if not captured:
            print("No captured ₹registration payment was found for the stored order.")
            print(f"Razorpay order: {order_id}")
            print("No account/payment changes were made.")
            return

        if len(captured) > 1:
            print(
                "More than one matching captured payment was found; recovery was stopped for safety."
            )
            print("No account/payment changes were made.")
            return

        gateway_payment = captured[0]
        payment_id = gateway_payment.get("id")
        print(f"Captured payment found: {payment_id}")
        print(f"Razorpay order: {order_id}")
        print(
            "Amount: INR 50.00 (or the currently configured supplier registration fee)"
        )

        duplicate = Payment.query.filter(
            Payment.transaction_id == payment_id,
            Payment.id != payment_record.id,
        ).first()
        if duplicate:
            raise SystemExit(
                "This Razorpay payment is already linked to another local payment record."
            )

        confirm = input(
            "Type RECOVER to activate this supplier without charging again: "
        ).strip()
        if confirm != "RECOVER":
            print("Recovery cancelled. No changes made.")
            return

        if verification is None:
            verification = SellerVerification(account_id=account.id)
            db.session.add(verification)

        payment_record.transaction_id = payment_id
        payment_record.status = "SUCCESS"
        payment_record.failure_message = None
        verification.registration_fee_paid = True
        verification.payment_id = payment_id
        verification.status = "VERIFIED"
        account.status = UserStatus.ACTIVE

        db.session.commit()
        try:
            AdminNotificationService.supplier_payment(account, payment_record.amount)
        except Exception:
            db.session.rollback()

        print("Supplier registration recovered successfully.")
        print(f"Supplier: {account.email}")
        print(f"Razorpay payment: {payment_id}")
        print("Account status: ACTIVE")


if __name__ == "__main__":
    main()
