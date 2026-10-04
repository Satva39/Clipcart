from .models import Payment
from .repository import PaymentRepository


class PaymentService:

    @staticmethod
    def create_payment(
        account_id,
        amount,
        payment_type,
    ):

        payment = Payment(
            account_id=account_id,
            amount=amount,
            payment_type=payment_type,
        )

        return PaymentRepository.create(payment)