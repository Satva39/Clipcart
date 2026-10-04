from flask import Blueprint, request

from app.core.decorators import active_supplier_required
from app.modules.admin.authorization import admin_authorized, get_authorized_admin
from app.modules.admin.services import AdminAuditService

from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt,
)

from app.utils.response import (
    success_response,
    error_response,
)

from .models import (
    SupplierPayoutAccount,
    SupplierPayout,
)

from .services import PayoutService

payouts_bp = Blueprint(
    "payouts",
    __name__,
    url_prefix="/api/payouts",
)


@payouts_bp.get("/account")
@jwt_required()
@active_supplier_required
def get_payout_account():

    account_id = int(get_jwt_identity())

    account = PayoutService.get_account(account_id)

    if not account:
        return success_response(data=None)

    return success_response(
        data={
            "id": account.id,
            "holder_name": account.holder_name,
            "bank_name": account.bank_name,
            "account_number": (
                "••••••••" + account.account_number[-4:]
                if account.account_number
                else None
            ),
            "ifsc": account.ifsc,
            "upi_id": account.upi_id,
            "is_verified": account.is_verified,
        }
    )


@payouts_bp.post("/account")
@jwt_required()
@active_supplier_required
def save_payout_account():

    account_id = int(get_jwt_identity())

    data = request.get_json(silent=True) or {}

    try:
        account = PayoutService.save_account(
            account_id,
            data,
        )
    except ValueError as e:
        return error_response(
            message=str(e),
            status_code=400,
        )

    return success_response(
        message="Payout account saved.",
        data={
            "id": account.id,
            "holder_name": account.holder_name,
            "is_verified": account.is_verified,
        },
    )


@payouts_bp.get("/balance")
@jwt_required()
@active_supplier_required
def payout_balance():

    account_id = int(get_jwt_identity())

    available = PayoutService.get_available_balance(account_id)

    return success_response(
        data={
            "available_balance": round(
                available,
                2,
            )
        }
    )


@payouts_bp.post("/request")
@jwt_required()
@active_supplier_required
def request_payout():

    account_id = int(get_jwt_identity())

    data = request.get_json(silent=True) or {}

    try:
        payout = PayoutService.create_payout(
            account_id,
            data.get("amount"),
        )
    except ValueError as e:
        return error_response(
            message=str(e),
            status_code=400,
        )

    return success_response(
        message="Payout request submitted.",
        data={
            "id": payout.id,
            "amount": float(payout.amount),
            "status": payout.status,
        },
        status_code=201,
    )


@payouts_bp.get("/history")
@jwt_required()
@active_supplier_required
def payout_history():

    account_id = int(get_jwt_identity())

    payouts = PayoutService.get_payouts(account_id)

    return success_response(
        data=[
            {
                "id": payout.id,
                "amount": float(payout.amount),
                "status": payout.status,
                "reference_id": payout.reference_id,
                "created_at": payout.created_at,
                "processed_at": payout.processed_at,
            }
            for payout in payouts
        ]
    )


@payouts_bp.get("/admin/accounts")
@admin_authorized
def admin_payout_accounts():

    accounts = SupplierPayoutAccount.query.order_by(
        SupplierPayoutAccount.created_at.desc()
    ).all()

    return success_response(
        data=[
            {
                "id": account.id,
                "account_id": account.account_id,
                "holder_name": account.holder_name,
                "bank_name": account.bank_name,
                "account_number": account.account_number or None,
                "ifsc": account.ifsc,
                "upi_id": account.upi_id,
                "is_verified": account.is_verified,
                "created_at": account.created_at,
            }
            for account in accounts
        ]
    )


@payouts_bp.put("/admin/accounts/<int:payout_account_id>/verify")
@admin_authorized
def admin_verify_payout_account(payout_account_id):

    try:
        account = PayoutService.verify_account(payout_account_id)
    except ValueError as e:
        return error_response(
            message=str(e),
            status_code=400,
        )

    AdminAuditService.record(
        get_authorized_admin().id,
        "PAYOUT_ACCOUNT_VERIFIED",
        "SUPPLIER_PAYOUT_ACCOUNT",
        account.id,
    )

    return success_response(
        message="Payout account verified.",
        data={
            "id": account.id,
            "is_verified": account.is_verified,
        },
    )


@payouts_bp.get("/admin/requests")
@admin_authorized
def admin_payout_requests():

    payouts = SupplierPayout.query.order_by(SupplierPayout.created_at.desc()).all()

    return success_response(
        data=[
            {
                "id": payout.id,
                "account_id": payout.account_id,
                "payout_account_id": (payout.payout_account_id),
                "amount": float(payout.amount),
                "status": payout.status,
                "reference_id": payout.reference_id,
                "created_at": payout.created_at,
                "processed_at": payout.processed_at,
            }
            for payout in payouts
        ]
    )


@payouts_bp.put("/admin/requests/<int:payout_id>/status")
@admin_authorized
def admin_update_payout(payout_id):

    data = request.get_json(silent=True) or {}

    try:
        payout = PayoutService.process_payout(
            payout_id,
            data.get("status"),
        )
    except ValueError as e:
        return error_response(
            message=str(e),
            status_code=400,
        )

    return success_response(
        message="Payout status updated.",
        data={
            "id": payout.id,
            "status": payout.status,
            "reference_id": payout.reference_id,
            "processed_at": payout.processed_at,
        },
    )
