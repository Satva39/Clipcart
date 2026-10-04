import os
from decimal import Decimal

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.modules.accounts.models import Account
from app.shared.utils.api_response import success, error
from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.services import create_account, email_exists, login_account
from app.modules.accounts.repository import AccountRepository
from app.modules.accounts.decorators import supplier_required
from app.modules.payments.models import Payment
from app.modules.payouts.models import SupplierPayoutAccount
from app.modules.seller_verification.models import SellerVerification
from app.services.razorpay_service import RazorpayService
from app.core.business_rules import get_supplier_registration_fee
from app.modules.admin.services import AdminNotificationService

supplier_registration_bp = Blueprint(
    "supplier_registration",
    __name__,
    url_prefix="/api/supplier-registration",
)


def _registration_state(account):
    verification = SellerVerification.query.filter_by(account_id=account.id).first()
    paid = bool(verification and verification.registration_fee_paid)
    return {
        "account_status": account.status.value,
        "registration_fee_paid": paid,
        "registration_fee": float(get_supplier_registration_fee()),
        "business_verification_status": (
            verification.status if verification else "PENDING"
        ),
        "can_access_portal": account.status == UserStatus.ACTIVE,
    }


@supplier_registration_bp.post("/")
def register_supplier():
    data = request.get_json(silent=True) or {}

    full_name = str(data.get("name", "")).strip()
    business_name = str(data.get("business_name", data.get("company", ""))).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    phone = str(data.get("phone", "")).strip()
    gst_number = str(data.get("gst_number", "")).strip() or None

    holder_name = str(data.get("holder_name", full_name)).strip()
    bank_name = str(data.get("bank_name", "")).strip() or None
    account_number = str(data.get("account_number", "")).strip() or None
    ifsc = str(data.get("ifsc", "")).strip().upper() or None
    upi_id = str(data.get("upi_id", "")).strip().lower() or None

    if len(full_name) < 3:
        return error("Full name is required.", 400)
    if len(business_name) < 2:
        return error("Business name is required.", 400)
    if not email:
        return error("Email is required.", 400)
    if len(password) < 12:
        return error("Password must be at least 12 characters.", 400)
    if not phone:
        return error("Phone number is required.", 400)
    if not holder_name:
        return error("Payout account holder name is required.", 400)
    if not upi_id and not (account_number and ifsc):
        return error("Provide a UPI ID or a bank account number with IFSC.", 400)
    if email_exists(email):
        return error("Email already registered.", 409)

    account = create_account(
        full_name=full_name,
        email=email,
        password=password,
        role=UserRole.SUPPLIER,
    )
    account.phone = phone
    account.status = UserStatus.PENDING

    verification = SellerVerification.query.filter_by(account_id=account.id).first()
    if not verification:
        verification = SellerVerification(account_id=account.id)
        db.session.add(verification)
    verification.business_name = business_name
    verification.gst_number = gst_number

    payout = SupplierPayoutAccount.query.filter_by(account_id=account.id).first()
    if not payout:
        payout = SupplierPayoutAccount(account_id=account.id, holder_name=holder_name)
        db.session.add(payout)
    payout.holder_name = holder_name
    payout.bank_name = bank_name
    payout.account_number = account_number
    payout.ifsc = ifsc
    payout.upi_id = upi_id
    payout.is_verified = False

    db.session.commit()
    try:
        AdminNotificationService.supplier_registered(account)
    except Exception:
        db.session.rollback()

    result = login_account(email, password)

    return success(
        "Supplier account created. Complete the registration payment to activate access.",
        {
            "user": {
                "id": account.id,
                "full_name": account.full_name,
                "email": account.email,
                "role": account.role.value,
                "status": account.status.value,
            },
            "onboarding": _registration_state(account),
            **result["tokens"],
        },
        201,
    )


@supplier_registration_bp.get("/status")
@jwt_required()
@supplier_required
def registration_status():
    account = AccountRepository.get_by_id(int(get_jwt_identity()))
    if not account:
        return error("Account not found.", 404)
    return success("Supplier onboarding status loaded.", _registration_state(account))


@supplier_registration_bp.post("/payment/order")
@jwt_required()
@supplier_required
def create_registration_payment():
    account_id = int(get_jwt_identity())
    account = Account.query.filter_by(id=account_id).with_for_update().first()

    if account is None:
        return error("Account not found.", 404)
    if account.status == UserStatus.ACTIVE:
        return error("Supplier registration is already completed.", 409)

    verification = SellerVerification.query.filter_by(account_id=account.id).first()
    if verification and verification.registration_fee_paid:
        if account.status != UserStatus.ACTIVE:
            account.status = UserStatus.ACTIVE
            db.session.commit()
        return error("Registration fee is already paid.", 409)

    existing = (
        Payment.query.filter_by(
            account_id=account.id, payment_type="SUPPLIER_REGISTRATION"
        )
        .filter(Payment.status == "PENDING")
        .order_by(Payment.created_at.desc())
        .first()
    )

    key_id = os.getenv("RAZORPAY_KEY_ID") or ""
    if not key_id:
        return error("Razorpay Key ID is not configured.", 500)

    registration_fee = get_supplier_registration_fee()

    if existing and existing.gateway_order_id:
        return success(
            "Registration payment order already initialized.",
            {
                "order_id": existing.gateway_order_id,
                "amount": float(registration_fee),
                "currency": "INR",
                "key_id": key_id,
            },
        )

    receipt = f"supplier_registration_{account.id}"
    try:
        order = RazorpayService.create_order(
            amount=registration_fee,
            receipt=receipt,
        )
    except RuntimeError as exc:
        return error(str(exc), 500)
    except Exception:
        return error("Unable to initialize Razorpay payment.", 502)

    payment = Payment(
        account_id=account.id,
        amount=registration_fee,
        payment_type="SUPPLIER_REGISTRATION",
        gateway="RAZORPAY",
        gateway_order_id=order["id"],
        status="PENDING",
    )
    db.session.add(payment)
    try:
        db.session.commit()
    except Exception as exc:
        # The unique supplier-registration payment index turns concurrent calls into
        # one durable payment record. Re-read the winning pending record and return it.
        db.session.rollback()
        if "uq_supplier_registration_payment_account" in str(exc):
            existing = (
                Payment.query.filter_by(
                    account_id=account.id, payment_type="SUPPLIER_REGISTRATION"
                )
                .filter(Payment.status == "PENDING")
                .order_by(Payment.created_at.desc())
                .first()
            )
            if existing and existing.gateway_order_id:
                return success(
                    "Registration payment order already initialized.",
                    {
                        "order_id": existing.gateway_order_id,
                        "amount": float(registration_fee),
                        "currency": "INR",
                        "key_id": key_id,
                    },
                )
        return error("Unable to persist the registration payment order.", 500)

    return success(
        "Registration payment order created.",
        {
            "order_id": order["id"],
            "amount": float(registration_fee),
            "currency": "INR",
            "key_id": key_id,
        },
    )


@supplier_registration_bp.post("/payment/verify")
@jwt_required()
@supplier_required
def verify_registration_payment():
    account_id = int(get_jwt_identity())
    account = AccountRepository.get_by_id(account_id)
    if account is None:
        return error("Account not found.", 404)

    verification = SellerVerification.query.filter_by(account_id=account.id).first()
    if verification and verification.registration_fee_paid:
        return success(
            "Supplier registration is already active.", {"status": account.status.value}
        )

    data = request.get_json(silent=True) or {}
    razorpay_order_id = str(data.get("razorpay_order_id", "")).strip()
    razorpay_payment_id = str(data.get("razorpay_payment_id", "")).strip()
    razorpay_signature = str(data.get("razorpay_signature", "")).strip()

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return error("Incomplete payment verification data.", 400)

    payment_record = (
        Payment.query.filter_by(gateway_order_id=razorpay_order_id)
        .with_for_update()
        .first()
    )
    if (
        not payment_record
        or payment_record.account_id != account.id
        or payment_record.payment_type != "SUPPLIER_REGISTRATION"
    ):
        return error("Registration payment order is invalid.", 400)
    if payment_record.status == "SUCCESS" and verification.registration_fee_paid:
        return success(
            "Supplier registration is already active.", {"status": account.status.value}
        )
    if (
        payment_record.transaction_id
        and payment_record.transaction_id != razorpay_payment_id
    ):
        return error(
            "This registration order is already associated with another payment.", 409
        )

    try:
        gateway_order = RazorpayService.get_order(razorpay_order_id)
        gateway_payment = RazorpayService.get_payment(razorpay_payment_id)

        expected_paise = int(get_supplier_registration_fee() * Decimal("100"))
        if (
            int(gateway_order.get("amount", 0)) != expected_paise
            or gateway_order.get("currency", "INR") != "INR"
        ):
            raise ValueError("Invalid registration payment amount.")
        if gateway_payment.get("order_id") != razorpay_order_id:
            raise ValueError("Payment does not belong to the registration order.")
        if int(gateway_payment.get("amount", 0)) != expected_paise:
            raise ValueError("Invalid registration payment amount.")
        if gateway_payment.get("status") != "captured":
            raise ValueError("Payment has not been captured.")

        RazorpayService.verify_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except Exception:
        return error("Payment verification failed.", 400)

    duplicate_transaction = Payment.query.filter(
        Payment.transaction_id == razorpay_payment_id,
        Payment.id != payment_record.id,
    ).first()
    if duplicate_transaction:
        return error("This payment is already associated with another account.", 409)

    if verification is None:
        verification = SellerVerification(account_id=account.id)
        db.session.add(verification)

    payment_record.transaction_id = razorpay_payment_id
    payment_record.status = "SUCCESS"
    payment_record.failure_message = None

    verification.registration_fee_paid = True
    verification.payment_id = razorpay_payment_id
    verification.status = "VERIFIED"
    account.status = UserStatus.ACTIVE

    db.session.commit()
    try:
        AdminNotificationService.supplier_payment(
            account,
            payment_record.amount,
        )
    except Exception:
        db.session.rollback()

    return success(
        "Supplier registration completed.",
        {
            "payment_id": payment_record.id,
            "razorpay_payment_id": razorpay_payment_id,
            "status": account.status.value,
        },
    )
