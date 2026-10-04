from app import create_app
from app.extensions import db
from app.modules.accounts.models import Account
from app.modules.accounts.enums import UserRole, UserStatus
from app.core.security import hash_password


def reset_database_connection():
    try:
        db.session.rollback()
    except Exception:
        pass

    db.session.remove()

    try:
        db.engine.dispose()
    except Exception:
        pass


def main():
    app = create_app()

    with app.app_context():
        reset_database_connection()

        email = input("Enter logistics manager email: ").strip().lower()

        existing = Account.query.filter_by(email=email).first()

        if existing:
            existing.role = UserRole.LOGISTICS_MANAGER
            existing.status = UserStatus.ACTIVE

            password = input("Enter new password: ")

            existing.password_hash = hash_password(password)

            db.session.commit()

            print("Logistics manager account updated.")
            return

        full_name = input("Enter full name: ").strip()

        password = input("Enter password: ")

        account = Account(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.LOGISTICS_MANAGER,
            status=UserStatus.ACTIVE,
        )

        db.session.add(account)
        db.session.commit()

        print("Logistics manager account created.")


if __name__ == "__main__":
    main()
