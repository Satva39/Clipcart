import unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.core.business_rules import get_supplier_registration_fee
from app.extensions import db
from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.models import Account
from app.modules.admin.services import PlatformSettingsService
from app.modules.payments.models import Payment
from app.modules.seller_verification.models import SellerVerification
from app.services.razorpay_service import RazorpayService


class SupplierRegistrationTestConfig:
    TESTING = True
    SECRET_KEY = "supplier-registration-test-secret-" + uuid4().hex
    JWT_SECRET_KEY = "supplier-registration-test-jwt-" + uuid4().hex
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
    CORS_ORIGINS = ["http://localhost:5174"]
    CLIPCART_ADMIN_EMAIL = "admin@example.com"
    CLIPCART_ADMIN_PORTAL_URL = "http://localhost:5176"
    RAZORPAY_KEY_ID = "rzp_test_registration_key"
    RAZORPAY_KEY_SECRET = "test_registration_secret"
    RAZORPAY_WEBHOOK_SECRET = ""
    SHIPROCKET_EMAIL = ""
    SHIPROCKET_PASSWORD = ""
    SHIPROCKET_BASE_URL = "https://apiv2.shiprocket.in/v1/external"
    SHIPROCKET_WEBHOOK_SECRET = ""
    CLOUDINARY_CLOUD_NAME = ""
    CLOUDINARY_API_KEY = ""
    CLOUDINARY_API_SECRET = ""
    RESEND_API_KEY = ""
    FROM_EMAIL = ""
    JSON_SORT_KEYS = False


class SupplierRegistrationOnboardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(SupplierRegistrationTestConfig)

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.supplier = Account(
            full_name="Pending Supplier",
            email="pending-supplier@example.com",
            password_hash=generate_password_hash("StrongSupplierPassword123!"),
            role=UserRole.SUPPLIER,
            status=UserStatus.PENDING,
        )
        db.session.add(self.supplier)
        db.session.flush()
        self.verification = SellerVerification(
            account_id=self.supplier.id,
            business_name="Test Business",
            registration_fee_paid=False,
            status="PENDING",
        )
        db.session.add(self.verification)
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def headers(self, account=None, portal="supplier"):
        account = account or self.supplier
        token = create_access_token(
            identity=str(account.id),
            additional_claims={
                "role": account.role.value,
                "email": account.email,
                "portal": portal,
            },
        )
        return {"Authorization": f"Bearer {token}"}

    def test_pending_supplier_can_load_registration_status(self):
        response = self.client.get(
            "/api/supplier-registration/status", headers=self.headers()
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()["data"]
        self.assertEqual(data["account_status"], "PENDING")
        self.assertEqual(data["registration_fee"], 50.0)
        self.assertFalse(data["can_access_portal"])

    def test_pending_supplier_still_cannot_access_main_supplier_portal(self):
        response = self.client.get(
            "/api/supplier/portal/profile", headers=self.headers()
        )
        self.assertEqual(response.status_code, 403)

    @patch.object(
        RazorpayService, "create_order", return_value={"id": "order_test_123"}
    )
    def test_pending_supplier_can_create_nonzero_registration_order(self, create_order):
        response = self.client.post(
            "/api/supplier-registration/payment/order", headers=self.headers()
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()["data"]
        self.assertEqual(data["order_id"], "order_test_123")
        self.assertEqual(data["amount"], 50.0)
        self.assertEqual(data["amount_paise"], 5000)
        self.assertEqual(data["key_id"], "rzp_test_registration_key")
        payment = Payment.query.filter_by(gateway_order_id="order_test_123").one()
        self.assertEqual(Decimal(str(payment.amount)), Decimal("50.00"))
        create_order.assert_called_once()

    def test_suspended_supplier_cannot_use_registration_payment_endpoints(self):
        self.supplier.status = UserStatus.SUSPENDED
        db.session.commit()
        response = self.client.get(
            "/api/supplier-registration/status", headers=self.headers()
        )
        self.assertEqual(response.status_code, 403)

    def test_zero_legacy_registration_fee_falls_back_to_default(self):
        with patch.object(
            PlatformSettingsService, "get_decimal", return_value=Decimal("0.00")
        ):
            fee = get_supplier_registration_fee()
        self.assertEqual(fee, Decimal("50.00"))

    @patch.object(RazorpayService, "verify_signature", return_value=True)
    @patch.object(
        RazorpayService,
        "get_payment",
        return_value={
            "order_id": "order_test_verify",
            "amount": 5000,
            "status": "captured",
        },
    )
    @patch.object(
        RazorpayService,
        "get_order",
        return_value={"amount": 5000, "currency": "INR"},
    )
    def test_successful_server_verified_payment_activates_supplier(
        self, get_order, get_payment, verify_signature
    ):
        db.session.add(
            Payment(
                account_id=self.supplier.id,
                amount=Decimal("50.00"),
                payment_type="SUPPLIER_REGISTRATION",
                gateway="RAZORPAY",
                gateway_order_id="order_test_verify",
                status="PENDING",
            )
        )
        db.session.commit()
        response = self.client.post(
            "/api/supplier-registration/payment/verify",
            headers=self.headers(),
            json={
                "razorpay_order_id": "order_test_verify",
                "razorpay_payment_id": "pay_test_verify",
                "razorpay_signature": "signature_test",
            },
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        db.session.refresh(self.supplier)
        db.session.refresh(self.verification)
        self.assertEqual(self.supplier.status, UserStatus.ACTIVE)
        self.assertTrue(self.verification.registration_fee_paid)
        self.assertEqual(self.verification.payment_id, "pay_test_verify")
        get_order.assert_called_once_with("order_test_verify")
        get_payment.assert_called_once_with("pay_test_verify")
        verify_signature.assert_called_once()


if __name__ == "__main__":
    unittest.main()
