from .models import SellerVerification
from .repository import SellerVerificationRepository


class SellerVerificationService:

    @staticmethod
    def create(account_id):

        verification = SellerVerification(
            account_id=account_id,
        )

        return SellerVerificationRepository.create(verification)

    @staticmethod
    def is_verified(account_id):

        verification = SellerVerificationRepository.get_by_account(account_id)

        if not verification:
            return False

        return verification.registration_fee_paid and verification.status == "APPROVED"

    @staticmethod
    def update_business_details(
        account_id,
        business_name,
        gst_number,
    ):

        verification = SellerVerificationRepository.get_by_account(account_id)
        if not verification:
            verification = SellerVerification(account_id=account_id)

        verification.business_name = business_name
        verification.gst_number = gst_number

        return SellerVerificationRepository.update(verification)
