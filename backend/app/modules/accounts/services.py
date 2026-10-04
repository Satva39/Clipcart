from app.core.security import hash_password
from .models import Account
from .repository import AccountRepository
from app.core.security import verify_password
from app.core.jwt import generate_tokens


def create_account(full_name, email, password, role):

    account = Account(
        full_name=full_name,
        email=email.lower(),
        password_hash=hash_password(password),
        role=role,
    )

    return AccountRepository.create(account)


def get_account_by_email(email):
    return AccountRepository.get_by_email(email)


def email_exists(email):
    return get_account_by_email(email) is not None


def login_account(email, password):
    account = get_account_by_email(email)
    if account is None:
        return None
    if not verify_password(password, account.password_hash):
        return None
    if account.status.value in {"SUSPENDED", "DELETED"}:
        return None

    from datetime import datetime

    account.last_login = datetime.utcnow()
    from app.extensions import db

    db.session.commit()

    return {
        "account": account,
        "tokens": generate_tokens(account),
    }
