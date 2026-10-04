from decimal import Decimal, ROUND_HALF_UP
import hmac
import hashlib

import razorpay
from flask import current_app


class RazorpayService:
    """Gateway adapter; secrets remain server-side."""

    @classmethod
    def _client(cls):
        key_id = current_app.config.get("RAZORPAY_KEY_ID")
        key_secret = current_app.config.get("RAZORPAY_KEY_SECRET")
        if not key_id or not key_secret:
            raise RuntimeError("Razorpay credentials are not configured.")
        return razorpay.Client(auth=(key_id, key_secret))

    @classmethod
    def create_order(cls, amount, receipt):
        normalized = Decimal(str(amount)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        amount_paise = int(
            (normalized * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP)
        )
        return cls._client().order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": str(receipt),
                "payment_capture": 1,
            }
        )

    @classmethod
    def get_order(cls, razorpay_order_id):
        return cls._client().order.fetch(razorpay_order_id)

    @classmethod
    def get_payment(cls, razorpay_payment_id):
        return cls._client().payment.fetch(razorpay_payment_id)

    @classmethod
    def get_order_payments(cls, razorpay_order_id):
        return cls._client().order.payments(razorpay_order_id)

    @classmethod
    def refund_payment(cls, razorpay_payment_id, amount):
        normalized = Decimal(str(amount)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        amount_paise = int(
            (normalized * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP)
        )
        return cls._client().payment.refund(
            razorpay_payment_id, {"amount": amount_paise}
        )

    @classmethod
    def verify_signature(
        cls, razorpay_order_id, razorpay_payment_id, razorpay_signature
    ):
        cls._client().utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        return True

    @staticmethod
    def verify_webhook_signature(payload, signature, secret):
        if not secret or not signature:
            raise ValueError("Razorpay webhook secret is not configured.")
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Razorpay webhook signature.")
        return True
