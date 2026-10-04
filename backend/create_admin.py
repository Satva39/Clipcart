# from getpass import getpass
from sqlalchemy import func

from app import create_app
from app.core.security import hash_password
from app.extensions import db
from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.models import Account


def main():
    app = create_app()
    with app.app_context():
        email = str(app.config.get("CLIPCART_ADMIN_EMAIL", "")).strip().lower()
        if not email:
            raise RuntimeError(
                "Set CLIPCART_ADMIN_EMAIL before creating the admin account."
            )

        full_name = input("Admin full name: ").strip()
        if len(full_name) < 2:
            raise ValueError("Admin full name is required.")

        password = input("Admin password (minimum 12 characters): ")
        if len(password) < 12:
            raise ValueError("Admin password must be at least 12 characters.")

        account = Account.query.filter(func.lower(Account.email) == email).first()

        if account:
            account.full_name = full_name
            account.role = UserRole.ADMIN
            account.status = UserStatus.ACTIVE
            account.password_hash = hash_password(password)
            db.session.commit()
            print("Admin account updated.")
            return

        account = Account(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.session.add(account)
        db.session.commit()
        print("Admin account created.")


if __name__ == "__main__":
    main()
