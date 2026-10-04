from flask_jwt_extended import create_access_token, create_refresh_token


def portal_for_role(role):
    return {
        "ADMIN": "admin",
        "SUPPLIER": "supplier",
        "CUSTOMER": "customer",
        "LOGISTICS_MANAGER": "logistics",
    }.get(str(role), "")


def generate_tokens(account):
    claims = {
        "role": account.role.value,
        "email": account.email,
        "portal": portal_for_role(account.role.value),
    }
    return {
        "access_token": create_access_token(
            identity=str(account.id),
            additional_claims=claims,
        ),
        "refresh_token": create_refresh_token(
            identity=str(account.id),
            additional_claims=claims,
        ),
    }
