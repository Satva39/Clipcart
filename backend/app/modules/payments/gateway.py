from app.services.razorpay_service import RazorpayService


class PaymentGateway:
    """Compatibility adapter used by older payment code."""

    @staticmethod
    def create_order(amount, receipt="clipcart_payment"):
        return RazorpayService.create_order(amount=amount, receipt=receipt)

    @staticmethod
    def verify_signature(order_id, payment_id, signature):
        return RazorpayService.verify_signature(
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
        )
