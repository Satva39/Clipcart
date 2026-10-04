import unittest
from datetime import timedelta
from uuid import uuid4

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.models import Account


class Part5TestConfig:
    TESTING = True
    SECRET_KEY = "part5-test-secret-" + uuid4().hex
    JWT_SECRET_KEY = "part5-jwt-secret-" + uuid4().hex
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=1)
    ADMIN_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    ADMIN_REFRESH_TOKEN_EXPIRES = timedelta(days=1)
    ADMIN_PASSWORD_RESET_TTL = 900
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = ["http://localhost:5176"]
    CLIPCART_ADMIN_EMAIL = "admin@example.com"
    CLIPCART_ADMIN_PORTAL_URL = "http://localhost:5176"
    RAZORPAY_KEY_ID = ""
    RAZORPAY_KEY_SECRET = ""
    RAZORPAY_WEBHOOK_SECRET = ""
    CLOUDINARY_CLOUD_NAME = ""
    CLOUDINARY_API_KEY = ""
    CLOUDINARY_API_SECRET = ""
    RESEND_API_KEY = ""
    FROM_EMAIL = ""
    JSON_SORT_KEYS = False


class Part5SecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(Part5TestConfig)

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        self.admin = Account(
            full_name="Test Admin",
            email="admin@example.com",
            password_hash=generate_password_hash("StrongAdminPass123!"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        self.customer = Account(
            full_name="Test Customer",
            email="customer@example.com",
            password_hash=generate_password_hash("StrongCustomerPass123!"),
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
        )
        self.supplier = Account(
            full_name="Test Supplier",
            email="supplier@example.com",
            password_hash=generate_password_hash("StrongSupplierPass123!"),
            role=UserRole.SUPPLIER,
            status=UserStatus.ACTIVE,
        )
        self.logistics = Account(
            full_name="Test Logistics",
            email="logistics@example.com",
            password_hash=generate_password_hash("StrongLogisticsPass123!"),
            role=UserRole.LOGISTICS_MANAGER,
            status=UserStatus.ACTIVE,
        )
        db.session.add_all([self.admin, self.customer, self.supplier, self.logistics])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def token(self, account, portal):
        return create_access_token(
            identity=str(account.id),
            additional_claims={
                "role": account.role.value,
                "email": account.email,
                "portal": portal,
            },
        )

    def headers(self, account, portal):
        return {"Authorization": f"Bearer {self.token(account, portal)}"}

    def test_admin_login_requires_configured_identity(self):
        response = self.client.post(
            "/api/admin/auth/login",
            json={
                "email": "customer@example.com",
                "password": "StrongCustomerPass123!",
            },
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.post(
            "/api/admin/auth/login",
            json={"email": "admin@example.com", "password": "StrongAdminPass123!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json["data"])

    def test_customer_cannot_access_admin_profile(self):
        response = self.client.get(
            "/api/admin/profile",
            headers=self.headers(self.customer, "customer"),
        )
        self.assertEqual(response.status_code, 403)

    def test_supplier_and_logistics_cannot_access_admin_profile(self):
        for account, portal in (
            (self.supplier, "supplier"),
            (self.logistics, "logistics"),
        ):
            response = self.client.get(
                "/api/admin/profile",
                headers=self.headers(account, portal),
            )
            self.assertEqual(response.status_code, 403)

    def test_admin_identity_and_status_are_database_validated(self):
        response = self.client.get(
            "/api/admin/profile",
            headers=self.headers(self.admin, "supplier"),
        )
        self.assertEqual(response.status_code, 403)

        self.admin.status = UserStatus.SUSPENDED
        db.session.commit()

        response = self.client.get(
            "/api/admin/profile",
            headers=self.headers(self.admin, "admin"),
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_read_customer_order_history(self):
        response = self.client.get(
            "/api/admin/orders",
            headers=self.headers(self.admin, "admin"),
        )
        self.assertEqual(response.status_code, 404)

    def test_logout_revokes_admin_access_token(self):
        response = self.client.post(
            "/api/admin/auth/login",
            json={"email": "admin@example.com", "password": "StrongAdminPass123!"},
        )
        token = response.json["data"]["access_token"]

        logout = self.client.post(
            "/api/admin/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(logout.status_code, 200)

        after = self.client.get(
            "/api/admin/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(after.status_code, 401)


if __name__ == "__main__":
    unittest.main()
