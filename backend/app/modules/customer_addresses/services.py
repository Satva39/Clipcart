from .models import CustomerAddress
from .repository import CustomerAddressRepository


class CustomerAddressService:
    @staticmethod
    def _clear_default(account_id, exclude_id=None):
        CustomerAddressRepository.clear_default(account_id, exclude_id=exclude_id)

    @staticmethod
    def create(account_id, data):
        if data.get("is_default"):
            CustomerAddressService._clear_default(account_id)

        address = CustomerAddress(
            account_id=account_id,
            full_name=data["full_name"],
            phone=data["phone"],
            address_line_1=data["address_line_1"],
            address_line_2=data.get("address_line_2"),
            landmark=data.get("landmark"),
            city=data["city"],
            state=data["state"],
            postal_code=data["postal_code"],
            country=data.get("country", "India"),
            is_default=data.get("is_default", False),
        )
        return CustomerAddressRepository.create(address)

    @staticmethod
    def get_all(account_id):
        return CustomerAddressRepository.get_all(account_id)

    @staticmethod
    def update(account_id, address_id, data):
        address = CustomerAddressRepository.get_by_id(address_id)
        if not address or address.account_id != account_id:
            raise ValueError("Address not found.")

        if data.get("is_default"):
            CustomerAddressService._clear_default(account_id, exclude_id=address.id)

        for field in (
            "full_name",
            "phone",
            "address_line_1",
            "address_line_2",
            "landmark",
            "city",
            "state",
            "postal_code",
            "country",
        ):
            if field in data:
                setattr(address, field, data[field])

        if "is_default" in data:
            address.is_default = bool(data["is_default"])

        CustomerAddressRepository.save()
        return address

    @staticmethod
    def set_default(account_id, address_id):
        address = CustomerAddressRepository.get_by_id(address_id)
        if not address or address.account_id != account_id:
            raise ValueError("Address not found.")

        CustomerAddressService._clear_default(account_id, exclude_id=address.id)
        address.is_default = True
        CustomerAddressRepository.save()
        return address

    @staticmethod
    def delete(account_id, address_id):
        address = CustomerAddressRepository.get_by_id(address_id)
        if not address or address.account_id != account_id:
            raise ValueError("Address not found.")

        was_default = address.is_default
        CustomerAddressRepository.delete(address)

        if was_default:
            remaining = CustomerAddressRepository.get_all(account_id)
            if remaining:
                remaining[0].is_default = True
                CustomerAddressRepository.save()
