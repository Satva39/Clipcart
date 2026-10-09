import re

from .models import CustomerAddress
from .repository import CustomerAddressRepository


class CustomerAddressService:
    @staticmethod
    def _validate_and_normalize(data):
        country = str(data.get("country", "India") or "India").strip() or "India"
        postal_code = re.sub(r"\s+", "", str(data.get("postal_code", "") or ""))
        if country.casefold() == "india" and not re.fullmatch(
            r"[1-9]\d{5}", postal_code
        ):
            raise ValueError("Indian postal code must be a valid 6-digit pincode.")

        full_name = " ".join(str(data.get("full_name", "") or "").split()).strip()
        address_line_1 = " ".join(
            str(data.get("address_line_1", "") or "").split()
        ).strip()
        phone = " ".join(str(data.get("phone", "") or "").split()).strip()
        if len(full_name) < 2 or len(address_line_1) < 3:
            raise ValueError("Full name and address line 1 are required.")

        phone_digits = re.sub(r"\D", "", phone)
        if country.casefold() == "india":
            valid_phone = len(phone_digits) == 10 or (
                len(phone_digits) == 12 and phone_digits.startswith("91")
            )
            if not valid_phone:
                raise ValueError(
                    "Enter a valid 10-digit Indian mobile number, optionally prefixed with +91."
                )
        elif not 7 <= len(phone_digits) <= 15:
            raise ValueError("Enter a valid phone number with 7 to 15 digits.")

        latitude = data.get("latitude")
        longitude = data.get("longitude")
        if latitude is not None:
            try:
                latitude = float(latitude)
            except (TypeError, ValueError):
                raise ValueError("Latitude must be a valid number.")
            if not -90 <= latitude <= 90:
                raise ValueError("Latitude must be between -90 and 90.")
        if longitude is not None:
            try:
                longitude = float(longitude)
            except (TypeError, ValueError):
                raise ValueError("Longitude must be a valid number.")
            if not -180 <= longitude <= 180:
                raise ValueError("Longitude must be between -180 and 180.")
        if (latitude is None) != (longitude is None):
            raise ValueError("Latitude and longitude must be provided together.")

        cleaned = dict(data)
        cleaned.update(
            {
                "full_name": full_name,
                "phone": phone,
                "address_line_1": address_line_1,
                "address_line_2": " ".join(
                    str(data.get("address_line_2", "") or "").split()
                ).strip(),
                "landmark": " ".join(
                    str(data.get("landmark", "") or "").split()
                ).strip(),
                "city": " ".join(str(data.get("city", "") or "").split()).strip(),
                "state": " ".join(str(data.get("state", "") or "").split()).strip(),
                "postal_code": postal_code,
                "country": country,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
        if not cleaned["phone"] or not cleaned["city"] or not cleaned["state"]:
            raise ValueError("Phone, city and state are required.")
        return cleaned

    @staticmethod
    def _clear_default(account_id, exclude_id=None):
        CustomerAddressRepository.clear_default(account_id, exclude_id=exclude_id)

    @staticmethod
    def create(account_id, data):
        data = CustomerAddressService._validate_and_normalize(data)
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
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
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

        location_fields = {
            "address_line_1",
            "address_line_2",
            "landmark",
            "city",
            "state",
            "postal_code",
            "country",
        }
        address_changed = any(field in data for field in location_fields) and any(
            str(data.get(field, getattr(address, field, "")) or "").strip()
            != str(getattr(address, field, "") or "").strip()
            for field in location_fields
        )
        keep_existing_coordinates = not address_changed and not (
            {"latitude", "longitude"} & data.keys()
        )
        merged = {
            "full_name": data.get("full_name", address.full_name),
            "phone": data.get("phone", address.phone),
            "address_line_1": data.get("address_line_1", address.address_line_1),
            "address_line_2": data.get("address_line_2", address.address_line_2),
            "landmark": data.get("landmark", address.landmark),
            "city": data.get("city", address.city),
            "state": data.get("state", address.state),
            "postal_code": data.get("postal_code", address.postal_code),
            "country": data.get("country", address.country),
            "latitude": (
                address.latitude if keep_existing_coordinates else data.get("latitude")
            ),
            "longitude": (
                address.longitude
                if keep_existing_coordinates
                else data.get("longitude")
            ),
        }
        merged = CustomerAddressService._validate_and_normalize(merged)
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
            "latitude",
            "longitude",
        ):
            setattr(address, field, merged[field])

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
