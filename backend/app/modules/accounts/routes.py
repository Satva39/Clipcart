from flask import Blueprint, jsonify
from flask import request

from app.shared.utils.api_response import success, error
from app.modules.accounts.schemas import (
    RegisterSchema,
    LoginSchema,
)
from app.modules.accounts.services import (
    create_account,
    email_exists,
    login_account,
)
from app.core.jwt import portal_for_role
from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.decorators import customer_required

from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
)

from app.modules.accounts.repository import AccountRepository

accounts_bp = Blueprint(
    "accounts",
    __name__,
    url_prefix="/api/accounts",
)

from flask_jwt_extended import (
    get_jwt,
    create_access_token,
)


@accounts_bp.get("/health")
def health():
    return success("Accounts module working.")


@accounts_bp.post("/register")
def register():

    data = request.get_json()

    if data is None:
        return error(
            "Request body must be valid JSON.",
            415,
        )

    errors = RegisterSchema().validate(data)

    if errors:
        return error(errors, 400)

    if email_exists(data["email"]):
        return error("Email already registered.", 409)

    account = create_account(
        full_name=data["full_name"],
        email=data["email"],
        password=data["password"],
        role=UserRole.CUSTOMER,
    )

    # Customers have no separate verification/onboarding gate, so they should be
    # immediately usable after registration. Supplier onboarding remains pending
    # until its own payment/verification workflow completes.
    account.status = UserStatus.ACTIVE

    from app.extensions import db

    db.session.commit()

    return success(
        "Account created successfully.",
        {
            "id": account.id,
            "email": account.email,
            "full_name": account.full_name,
        },
        201,
    )


@accounts_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():

    account_id = get_jwt_identity()
    account = AccountRepository.get_by_id(account_id)

    if account is None:
        return error("Account not found.", 404)

    access_token = create_access_token(
        identity=str(account.id),
        additional_claims={
            "role": account.role.value,
            "status": account.status.value if account.status else None,
            "email": account.email,
            "portal": portal_for_role(account.role.value),
        },
    )

    return success(
        "Access token refreshed.",
        {
            "access_token": access_token,
        },
    )


@accounts_bp.post("/login")
def login():

    data = request.get_json(silent=True)

    if data is None:
        return error("Request body must be valid JSON.", 415)

    errors = LoginSchema().validate(data)

    if errors:
        return error(errors, 400)

    result = login_account(
        data["email"],
        data["password"],
    )

    if result is None:
        return error("Invalid email or password.", 401)

    account = result["account"]

    return success(
        "Login successful.",
        {
            "user": {
                "id": account.id,
                "full_name": account.full_name,
                "email": account.email,
                "role": account.role.value,
                "status": account.status.value if account.status else None,
            },
            **result["tokens"],
        },
    )


@accounts_bp.put("/me")
@customer_required
def update_current_user():
    account_id = int(get_jwt_identity())
    account = AccountRepository.get_by_id(account_id)
    if account is None:
        return error("Account not found.", 404)

    data = request.get_json(silent=True) or {}
    full_name = str(data.get("full_name", account.full_name)).strip()
    phone = data.get("phone", account.phone)

    if len(full_name) < 2:
        return error("Full name must contain at least 2 characters.", 400)

    if phone is not None:
        phone = str(phone).strip() or None
        if phone:
            duplicate = AccountRepository.get_by_phone(phone)
            if duplicate and duplicate.id != account.id:
                return error("Phone number is already registered.", 409)

    account.full_name = full_name
    account.phone = phone
    AccountRepository.save()

    return success(
        "Profile updated.",
        {
            "id": account.id,
            "full_name": account.full_name,
            "email": account.email,
            "phone": account.phone,
            "role": account.role.value,
            "profile_image": account.profile_image,
        },
    )


@accounts_bp.get("/me")
@jwt_required()
def current_user():

    account = AccountRepository.get_by_id(get_jwt_identity())

    if account is None:
        return error("Account not found.", 404)

    return success(
        "Profile loaded.",
        {
            "id": account.id,
            "full_name": account.full_name,
            "email": account.email,
            "phone": account.phone,
            "profile_image": account.profile_image,
            "role": account.role.value,
        },
    )
