import hashlib
import json
import re
import threading
from datetime import datetime, timedelta
from decimal import Decimal

import requests
from flask import current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.modules.accounts.models import Account
from app.modules.cart.models import CartItem
from app.modules.notifications.enums import NotificationType
from app.modules.notifications.services import NotificationService
from app.modules.order_events.services import OrderEventService
from app.modules.order_items.models import OrderItem
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order
from app.modules.products.models import Product
from app.modules.seller_verification.models import SellerVerification
from app.modules.supplier_orders.enums import DeliveryStatus, PickupStatus
from app.modules.supplier_orders.models import DeliveryAssignment

from .models import Shipment


class ShiprocketError(RuntimeError):
    def __init__(self, message, *, code=None, status_code=None, retryable=False):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable


class ShiprocketService:
    _token = None
    _token_expires_at = None
    _token_lock = threading.Lock()

    STATUS_RANKS = {
        "PENDING": 0,
        "NEW": 1,
        "PICKUP GENERATED": 2,
        "PICKUP SCHEDULED": 3,
        "AWB ASSIGNED": 3,
        "MANIFEST GENERATED": 4,
        "PICKED UP": 5,
        "SHIPPED": 5,
        "IN TRANSIT": 6,
        "REACHED AT DESTINATION HUB": 7,
        "OUT FOR DELIVERY": 8,
        "DELIVERED": 9,
    }

    STATUS_MAP = {
        "PICKUP GENERATED": (
            PickupStatus.PENDING,
            DeliveryStatus.NOT_STARTED,
            "AWAITING_PICKUP",
        ),
        "PICKUP SCHEDULED": (
            PickupStatus.PENDING,
            DeliveryStatus.NOT_STARTED,
            "AWAITING_PICKUP",
        ),
        "AWB ASSIGNED": (
            PickupStatus.PENDING,
            DeliveryStatus.NOT_STARTED,
            "AWAITING_PICKUP",
        ),
        "MANIFEST GENERATED": (
            PickupStatus.PENDING,
            DeliveryStatus.NOT_STARTED,
            "AWAITING_PICKUP",
        ),
        "PICKED UP": (PickupStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT, "SHIPPED"),
        "SHIPPED": (PickupStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT, "SHIPPED"),
        "IN TRANSIT": (PickupStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT, "SHIPPED"),
        "REACHED AT DESTINATION HUB": (
            PickupStatus.PICKED_UP,
            DeliveryStatus.IN_TRANSIT,
            "SHIPPED",
        ),
        "OUT FOR DELIVERY": (
            PickupStatus.PICKED_UP,
            DeliveryStatus.OUT_FOR_DELIVERY,
            "OUT_FOR_DELIVERY",
        ),
        "DELIVERED": (
            PickupStatus.PICKED_UP,
            DeliveryStatus.OUT_FOR_DELIVERY,
            "DELIVERED",
        ),
    }

    FAILURE_MARKERS = (
        "CANCELLED",
        "CANCELED",
        "FAILED",
        "UNDELIVERED",
        "RTO",
        "RETURN TO ORIGIN",
        "LOST",
        "DAMAGED",
    )

    @classmethod
    def configured(cls):
        return bool(
            current_app.config.get("SHIPROCKET_EMAIL")
            and current_app.config.get("SHIPROCKET_PASSWORD")
            and current_app.config.get("SHIPROCKET_BASE_URL")
        )

    @classmethod
    def _headers(cls, token=None):
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @classmethod
    def _auth(cls, force=False):
        with cls._token_lock:
            if (
                not force
                and cls._token
                and cls._token_expires_at
                and cls._token_expires_at > datetime.utcnow() + timedelta(minutes=5)
            ):
                return cls._token

            if not cls.configured():
                raise ShiprocketError(
                    "Shiprocket integration is not configured.",
                    code="NOT_CONFIGURED",
                    retryable=False,
                )

            url = f"{current_app.config['SHIPROCKET_BASE_URL'].rstrip('/')}/auth/login"
            try:
                response = requests.post(
                    url,
                    json={
                        "email": current_app.config["SHIPROCKET_EMAIL"],
                        "password": current_app.config["SHIPROCKET_PASSWORD"],
                    },
                    headers=cls._headers(),
                    timeout=int(current_app.config.get("SHIPROCKET_TIMEOUT", 20)),
                )
            except requests.RequestException as exc:
                raise ShiprocketError(
                    "Shiprocket authentication is temporarily unavailable.",
                    code="AUTH_NETWORK_ERROR",
                    retryable=True,
                ) from exc

            if response.status_code >= 400:
                raise cls._response_error(response, "Shiprocket authentication failed.")

            try:
                payload = response.json()
            except ValueError as exc:
                raise ShiprocketError(
                    "Shiprocket authentication returned an invalid response.",
                    code="AUTH_INVALID_RESPONSE",
                    retryable=True,
                ) from exc

            token = str(payload.get("token") or "").strip()
            if not token:
                raise ShiprocketError(
                    "Shiprocket authentication did not return an access token.",
                    code="AUTH_NO_TOKEN",
                    retryable=True,
                )

            cls._token = token
            # Official API documentation states the token is valid for 10 days.
            cls._token_expires_at = datetime.utcnow() + timedelta(days=10)
            return token

    @staticmethod
    def _response_error(response, fallback):
        code = f"HTTP_{response.status_code}"
        retryable = (
            response.status_code in {408, 409, 425, 429} or response.status_code >= 500
        )
        try:
            body = response.json()
            message = str(body.get("message") or body.get("error") or fallback)
            details = body.get("errors") or body.get("error_details")
            if details:
                try:
                    detail_text = json.dumps(
                        details, ensure_ascii=False, sort_keys=True
                    )
                except TypeError:
                    detail_text = str(details)
                message = f"{message}: {detail_text}"
            if len(message) > 1000:
                message = message[:1000]
        except ValueError:
            message = fallback
        return ShiprocketError(
            message, code=code, status_code=response.status_code, retryable=retryable
        )

    @classmethod
    def _request(cls, method, path, *, json_body=None, params=None, allow_retry=True):
        token = cls._auth()
        url = f"{current_app.config['SHIPROCKET_BASE_URL'].rstrip('/')}/{path.lstrip('/')}"
        try:
            response = requests.request(
                method,
                url,
                json=json_body,
                params=params,
                headers=cls._headers(token),
                timeout=int(current_app.config.get("SHIPROCKET_TIMEOUT", 20)),
            )
        except requests.RequestException as exc:
            raise ShiprocketError(
                "Shiprocket request failed temporarily.",
                code="NETWORK_ERROR",
                retryable=True,
            ) from exc

        if response.status_code == 401 and allow_retry:
            token = cls._auth(force=True)
            try:
                response = requests.request(
                    method,
                    url,
                    json=json_body,
                    params=params,
                    headers=cls._headers(token),
                    timeout=int(current_app.config.get("SHIPROCKET_TIMEOUT", 20)),
                )
            except requests.RequestException as exc:
                raise ShiprocketError(
                    "Shiprocket request failed temporarily.",
                    code="AUTH_RETRY_NETWORK_ERROR",
                    retryable=True,
                ) from exc

        if response.status_code >= 400:
            app_logger = current_app.logger
            app_logger.error(
                "Shiprocket API request failed: %s %s -> HTTP %s",
                method.upper(),
                path,
                response.status_code,
            )
            raise cls._response_error(response, "Shiprocket API request failed.")

        current_app.logger.info(
            "Shiprocket API request succeeded: %s %s -> HTTP %s",
            method.upper(),
            path,
            response.status_code,
        )
        try:
            return response.json()
        except ValueError as exc:
            raise ShiprocketError(
                "Shiprocket returned an invalid response.",
                code="INVALID_RESPONSE",
                retryable=True,
            ) from exc

    @staticmethod
    def _pick(payload, *keys):
        if not isinstance(payload, dict):
            return None
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
        return None

    @staticmethod
    def _customer_name_parts(value):
        """Split Clipcart's single full-name field for Shiprocket's name fields.

        Shiprocket documents billing_customer_name as the first name and
        billing_last_name as the last name. Clipcart stores one full name, so
        use the first token as the first name and the remaining tokens as the
        last name. A single-name customer keeps an empty last-name value while
        still sending the required key because the live API validator requires
        the field to be present.
        """
        name = " ".join(str(value or "").split()).strip()
        if not name:
            return "Customer", ""
        parts = name.split(" ", 1)
        first = parts[0].strip()[:100] or "Customer"
        last = parts[1].strip()[:100] if len(parts) > 1 else ""
        return first, last

    @staticmethod
    def _supplier_address(supplier_id):
        supplier = (
            Account.query.options(joinedload(Account.seller_verification))
            .filter_by(id=supplier_id)
            .first()
        )
        if not supplier:
            raise ShiprocketError(
                "Supplier account not found.", code="SUPPLIER_NOT_FOUND"
            )
        verification = supplier.seller_verification
        if not verification:
            raise ShiprocketError(
                "Supplier pickup address is not configured in Clipcart.",
                code="SUPPLIER_PICKUP_MISSING",
            )

        values = {
            "business_name": (
                verification.business_name or supplier.full_name or ""
            ).strip(),
            "name": (supplier.full_name or verification.business_name or "").strip(),
            "email": (supplier.email or "").strip(),
            "phone": (supplier.phone or "").strip(),
            "address": (verification.return_address_line_1 or "").strip(),
            "address_2": " ".join(
                p.strip()
                for p in [
                    verification.return_address_line_2,
                    verification.return_landmark,
                ]
                if p and p.strip()
            ),
            "city": (verification.return_city or "").strip(),
            "state": (verification.return_state or "").strip(),
            "pin_code": (verification.return_postal_code or "").strip(),
            "country": (verification.return_country or "India").strip(),
        }
        missing = [
            label
            for label, key in (
                ("business/contact name", "business_name"),
                ("email", "email"),
                ("phone", "phone"),
                ("address", "address"),
                ("city", "city"),
                ("state", "state"),
                ("postal code", "pin_code"),
                ("country", "country"),
            )
            if not values[key]
        ]
        if missing:
            raise ShiprocketError(
                "Supplier pickup address is incomplete: " + ", ".join(missing) + ".",
                code="SUPPLIER_PICKUP_INCOMPLETE",
            )
        if (
            len(values["address"]) > 80
            or len(values["city"]) > 100
            or len(values["state"]) > 100
        ):
            raise ShiprocketError(
                "Supplier pickup address exceeds Clipcart field limits.",
                code="SUPPLIER_PICKUP_INVALID",
            )
        if values["country"].casefold() == "india" and not re.fullmatch(
            r"[1-9]\d{5}", values["pin_code"]
        ):
            raise ShiprocketError(
                "Supplier pickup postal code must be a valid 6-digit Indian pincode.",
                code="SUPPLIER_PICKUP_INVALID",
            )
        return values

    @classmethod
    def _pickup_fingerprint(cls, values):
        canonical = "|".join(
            str(values[key]).strip().casefold()
            for key in (
                "business_name",
                "address",
                "address_2",
                "city",
                "state",
                "pin_code",
                "country",
                "phone",
            )
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:10]

    @classmethod
    def _get_or_create_pickup(cls, supplier_id):
        values = cls._supplier_address(supplier_id)
        locations = cls._request("GET", "/settings/company/pickup")
        rows = []
        if isinstance(locations, dict):
            data = locations.get("data")
            if isinstance(data, dict):
                rows = (
                    data.get("shipping_address") or data.get("pickup_locations") or []
                )
            elif isinstance(data, list):
                rows = data
            else:
                rows = (
                    locations.get("shipping_address")
                    or locations.get("pickup_locations")
                    or []
                )
        elif isinstance(locations, list):
            rows = locations

        def norm(value):
            return " ".join(str(value or "").split()).casefold()

        expected = {
            "address": norm(values["address"]),
            "city": norm(values["city"]),
            "state": norm(values["state"]),
            "pin_code": norm(values["pin_code"]),
        }
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            if all(
                norm(cls._pick(row, key)) == expected[key]
                for key in ("address", "city", "state", "pin_code")
            ):
                return {
                    "id": str(cls._pick(row, "id", "pickup_id") or ""),
                    "name": str(cls._pick(row, "pickup_location") or "").strip(),
                }

        location_name = f"CC{int(supplier_id)}-{cls._pickup_fingerprint(values)}"[:36]
        payload = {
            "pickup_location": location_name,
            "name": values["name"],
            "email": values["email"],
            "phone": values["phone"],
            "address": values["address"],
            "address_2": values["address_2"],
            "city": values["city"],
            "state": values["state"],
            "country": values["country"],
            "pin_code": values["pin_code"],
        }
        response = cls._request(
            "POST", "/settings/company/addpickup", json_body=payload
        )
        nested = response.get("data") if isinstance(response, dict) else None
        nested = nested if isinstance(nested, dict) else {}
        return {
            "id": str(
                cls._pick(response, "pickup_id", "id")
                or cls._pick(nested, "pickup_id", "id")
                or ""
            ),
            "name": str(
                cls._pick(response, "pickup_location", "name")
                or cls._pick(nested, "pickup_location", "name")
                or location_name
            ).strip(),
        }

    @classmethod
    def _package_dimensions(cls, items):
        rows = []
        for item in items:
            product = item.product
            values = [
                (
                    getattr(item, "shipping_weight_kg_snapshot", None)
                    if getattr(item, "shipping_weight_kg_snapshot", None) is not None
                    else (product.shipping_weight_kg if product else None)
                ),
                (
                    getattr(item, "shipping_length_cm_snapshot", None)
                    if getattr(item, "shipping_length_cm_snapshot", None) is not None
                    else (product.shipping_length_cm if product else None)
                ),
                (
                    getattr(item, "shipping_width_cm_snapshot", None)
                    if getattr(item, "shipping_width_cm_snapshot", None) is not None
                    else (product.shipping_width_cm if product else None)
                ),
                (
                    getattr(item, "shipping_height_cm_snapshot", None)
                    if getattr(item, "shipping_height_cm_snapshot", None) is not None
                    else (product.shipping_height_cm if product else None)
                ),
            ]
            # CartItem does not persist order-line snapshots; OrderItem does.
            # Use the snapshot when available and otherwise use the live product name.
            display_name = getattr(item, "product_name_snapshot", None) or (
                product.name if product else "Product"
            )
            if any(value is None for value in values):
                raise ShiprocketError(
                    f"Shipping package data is missing for product '{display_name}'.",
                    code="PACKAGE_DATA_MISSING",
                )
            weight, length, width, height = [Decimal(str(value)) for value in values]
            if weight <= 0 or min(length, width, height) <= Decimal("0.5"):
                raise ShiprocketError(
                    f"Shipping package data is invalid for product '{product.name}'.",
                    code="PACKAGE_DATA_INVALID",
                )
            rows.append((weight, length, width, height))

        dimensions = {(x[1], x[2], x[3]) for x in rows}
        if len(dimensions) != 1:
            raise ShiprocketError(
                "This supplier order contains products with different package dimensions. Set one common shippable package profile per product before shipment creation.",
                code="PACKAGE_DIMENSIONS_MISMATCH",
            )
        weight = sum(
            (x[0] * Decimal(int(item.quantity or 0)) for x, item in zip(rows, items)),
            Decimal("0"),
        )
        length, width, height = next(iter(dimensions))
        return {
            "weight": float(weight),
            "length": float(length),
            "breadth": float(width),
            "height": float(height),
        }

    @classmethod
    def _build_payload(cls, order, supplier_id, items, pickup_name, shipment=None):
        postal_code = re.sub(r"\s+", "", str(order.delivery_postal_code or ""))
        if (
            order.delivery_country
            and str(order.delivery_country).strip().casefold() == "india"
            and not re.fullmatch(r"[1-9]\d{5}", postal_code)
        ):
            raise ShiprocketError(
                "Customer delivery postal code must be a valid 6-digit Indian pincode.",
                code="CUSTOMER_ADDRESS_INVALID",
            )
        try:
            pincode = int(postal_code)
        except (TypeError, ValueError):
            raise ShiprocketError(
                "Customer delivery postal code is invalid.",
                code="CUSTOMER_ADDRESS_INVALID",
            )
        if pincode <= 0:
            raise ShiprocketError(
                "Customer delivery postal code is invalid.",
                code="CUSTOMER_ADDRESS_INVALID",
            )
        if len((order.delivery_city or "").strip()) > 30:
            raise ShiprocketError(
                "Customer delivery city is too long for Shiprocket.",
                code="CUSTOMER_CITY_INVALID",
            )
        phone_digits = re.sub(r"\D", "", str(order.delivery_phone or ""))
        if phone_digits.startswith("91") and len(phone_digits) == 12:
            phone_digits = phone_digits[2:]
        if len(phone_digits) != 10:
            raise ShiprocketError(
                "Customer delivery phone must contain a valid 10-digit Indian mobile number.",
                code="CUSTOMER_PHONE_INVALID",
            )

        package = cls._package_dimensions(items)
        address_2 = " ".join(
            p.strip()
            for p in [order.delivery_address_line_2, order.delivery_landmark]
            if p and p.strip()
        )
        customer_first_name, customer_last_name = cls._customer_name_parts(
            order.delivery_full_name or order.customer_name
        )
        customer_address = (order.delivery_address_line_1 or "").strip()
        customer_city = (order.delivery_city or "").strip()
        customer_state = (order.delivery_state or "").strip()
        customer_country = (order.delivery_country or "India").strip()
        customer_email = (order.customer_email or "").strip()
        if len(customer_address) < 3:
            raise ShiprocketError(
                "Customer delivery address is too short for Shiprocket.",
                code="CUSTOMER_ADDRESS_INVALID",
            )
        if not customer_city or not customer_state or not customer_country:
            raise ShiprocketError(
                "Customer delivery city, state and country are required.",
                code="CUSTOMER_ADDRESS_INCOMPLETE",
            )
        if not customer_email:
            raise ShiprocketError(
                "Customer email is required for Shiprocket.",
                code="CUSTOMER_EMAIL_MISSING",
            )
        order_items = []
        supplier_subtotal = Decimal("0")
        for item in items:
            product = item.product
            variant = item.variant
            name = item.product_name_snapshot or (
                product.name if product else "Product"
            )
            variant_label = item.variant_value_snapshot or (
                variant.value if variant else None
            )
            if variant_label:
                name = f"{name} - {variant_label}"
            sku = variant.sku if variant else (product.sku if product else None)
            sku = sku or item.sku_snapshot or f"CLP-ITEM-{item.id}"
            order_items.append(
                {
                    "name": name[:255],
                    "sku": sku[:100],
                    "units": int(item.quantity),
                    "selling_price": float(item.unit_price),
                    "discount": 0,
                    "tax": 0,
                    "hsn": "",
                }
            )
            supplier_subtotal += Decimal(str(item.subtotal or 0))

        supplier_key = cls._supplier_key(order.id, supplier_id)
        order_subtotal = Decimal(str(order.subtotal or 0))
        supplier_discount = Decimal("0")
        if order_subtotal > 0 and order.discount:
            supplier_discount = (
                Decimal(str(order.discount)) * supplier_subtotal / order_subtotal
            ).quantize(Decimal("0.01"))
        order_tax = Decimal(str(order.tax or 0))
        order_marketing_fee = Decimal(str(order.marketing_fee or 0))
        tax_allocation = (
            (order_tax * supplier_subtotal / order_subtotal).quantize(Decimal("0.01"))
            if order_subtotal > 0
            else Decimal("0")
        )
        marketing_allocation = (
            (order_marketing_fee * supplier_subtotal / order_subtotal).quantize(
                Decimal("0.01")
            )
            if order_subtotal > 0
            else Decimal("0")
        )
        transaction_charges = marketing_allocation + tax_allocation
        shipping_charge = Decimal("0.00")
        if shipment is not None and shipment.quoted_shipping_charge is not None:
            shipping_charge = money(shipment.quoted_shipping_charge)
        elif isinstance(order.shipping_quote, dict):
            for quote in order.shipping_quote.get("suppliers", []):
                if int(quote.get("supplier_id") or 0) == int(supplier_id):
                    shipping_charge = money(quote.get("shipping_charge") or 0)
                    break
        comment = (
            "Clipcart supplier shipment allocation: "
            f"marketing fee ₹{marketing_allocation:.2f}, tax ₹{tax_allocation:.2f}."
        )
        payload = {
            "order_id": supplier_key,
            "order_date": (order.created_at or datetime.utcnow()).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "pickup_location": pickup_name,
            "billing_customer_name": customer_first_name,
            "billing_last_name": customer_last_name,
            "billing_address": customer_address[:255],
            "billing_address_2": address_2[:255],
            "billing_isd_code": "+91",
            "billing_city": customer_city,
            "billing_pincode": pincode,
            "billing_state": customer_state,
            "billing_country": customer_country,
            "billing_email": customer_email,
            "billing_phone": int(phone_digits),
            "shipping_is_billing": True,
            "shipping_customer_name": customer_first_name,
            "shipping_last_name": customer_last_name,
            "shipping_address": customer_address[:255],
            "shipping_address_2": address_2[:255],
            "shipping_city": customer_city,
            "shipping_pincode": pincode,
            "shipping_state": customer_state,
            "shipping_country": customer_country,
            "shipping_email": customer_email,
            "shipping_phone": int(phone_digits),
            "order_items": order_items,
            "payment_method": "Prepaid",
            "shipping_charges": float(shipping_charge),
            "giftwrap_charges": 0,
            "transaction_charges": float(transaction_charges),
            "total_discount": float(supplier_discount),
            "comment": comment,
            "sub_total": float(
                max(supplier_subtotal - supplier_discount, Decimal("0"))
            ),
            "length": package["length"],
            "breadth": package["breadth"],
            "height": package["height"],
            "weight": package["weight"],
        }
        if order.delivery_latitude is not None and order.delivery_longitude is not None:
            payload["latitude"] = float(order.delivery_latitude)
            payload["longitude"] = float(order.delivery_longitude)
        return payload

    @staticmethod
    def _supplier_key(order_id, supplier_id):
        # Shiprocket advises numeric channel order IDs for interoperability with
        # other order APIs. Keep the reference deterministic so retries are idempotent.
        order_id = int(order_id)
        supplier_id = int(supplier_id)
        return str(order_id * 10_000_000_000 + supplier_id)

    @classmethod
    def _repair_legacy_reference(cls, shipment):
        legacy = str(shipment.shiprocket_reference_id or "").strip()
        if not legacy.startswith("CC-"):
            return False
        try:
            _, order_id, supplier_id = legacy.split("-", 2)
            replacement = cls._supplier_key(int(order_id), int(supplier_id))
        except (ValueError, AttributeError):
            return False
        if replacement == legacy:
            return False
        conflict = Shipment.query.filter(
            Shipment.shiprocket_reference_id == replacement,
            Shipment.id != shipment.id,
        ).first()
        if conflict:
            raise ShiprocketError(
                "A conflicting Clipcart Shiprocket reference already exists.",
                code="REFERENCE_CONFLICT",
            )
        shipment.shiprocket_reference_id = replacement
        db.session.commit()
        return True

    @classmethod
    def _find_existing_order(cls, reference):
        """Reconcile an external order if the create request timed out after Shiprocket accepted it."""
        payload = cls._request(
            "GET",
            "/orders",
            params={
                "search": reference,
                "filter_by": "channel_order_id",
                "per_page": 15,
            },
        )
        rows = payload.get("data") if isinstance(payload, dict) else None
        for row in rows if isinstance(rows, list) else []:
            if str(row.get("channel_order_id") or "").strip() != reference:
                continue
            external_status = str(row.get("status") or "").strip().upper()
            shipment_rows = row.get("shipments") if isinstance(row, dict) else None
            external_shipment = (
                shipment_rows[0]
                if isinstance(shipment_rows, list) and shipment_rows
                else {}
            )
            return {
                "order_id": cls._pick(row, "id"),
                "shipment_id": cls._pick(external_shipment, "id"),
                "awb": cls._pick(external_shipment, "awb"),
                "courier": cls._pick(external_shipment, "courier"),
                "courier_company_id": cls._pick(
                    external_shipment, "courier_company_id"
                ),
                "pickup_scheduled_date": cls._pick(
                    external_shipment, "pickup_scheduled_date"
                ),
                "status": external_status,
            }
        return None

    @classmethod
    def _apply_reconciled_order(cls, shipment, existing):
        if (
            not existing
            or existing.get("order_id") is None
            or existing.get("shipment_id") is None
        ):
            return False
        if existing.get("status") in {"CANCELED", "CANCELLED"}:
            raise ShiprocketError(
                "A Shiprocket order with this Clipcart reference already exists in a cancelled state.",
                code="EXTERNAL_ORDER_CANCELLED",
            )
        shipment.shiprocket_order_id = int(existing["order_id"])
        shipment.shiprocket_shipment_id = int(existing["shipment_id"])
        shipment.awb_code = str(existing.get("awb") or "") or None
        shipment.courier_company_id = cls._int_or_none(
            existing.get("courier_company_id")
        )
        shipment.courier_name = str(existing.get("courier") or "") or None
        pickup_date = existing.get("pickup_scheduled_date")
        if pickup_date:
            parsed = cls._parse_datetime(pickup_date)
            shipment.pickup_scheduled_at = parsed or datetime.utcnow()
        shipment.status = str(existing.get("status") or "ORDER_CREATED").upper()
        shipment.failure_code = None
        shipment.failure_message = None
        shipment.last_synced_at = datetime.utcnow()
        db.session.commit()
        return True

    @classmethod
    def quote_checkout_shipping(cls, account_id, address):
        """Return the current Shiprocket delivery charge for the checkout cart.

        Clipcart creates one forward shipment per supplier, so the checkout quote
        is the sum of one selected courier quote per supplier. Shiprocket's own
        recommended courier is preferred; otherwise the lowest non-blocked rate
        is selected. The chosen courier is persisted so AWB assignment can target
        the same provider and keep the customer's quoted amount consistent.
        """
        if not current_app.config.get("SHIPROCKET_EMAIL") or not current_app.config.get(
            "SHIPROCKET_PASSWORD"
        ):
            raise ShiprocketError(
                "Shiprocket is not configured, so the delivery charge cannot be calculated.",
                code="SHIPROCKET_NOT_CONFIGURED",
                retryable=False,
            )
        if not address:
            raise ShiprocketError(
                "A delivery address is required before calculating the delivery charge.",
                code="DELIVERY_ADDRESS_REQUIRED",
                retryable=False,
            )

        items = (
            CartItem.query.options(
                joinedload(CartItem.product),
                joinedload(CartItem.variant),
            )
            .filter_by(account_id=int(account_id))
            .order_by(CartItem.id.asc())
            .all()
        )
        if not items:
            raise ShiprocketError("Cart is empty.", code="CART_EMPTY", retryable=False)

        supplier_items = {}
        for item in items:
            product = item.product
            if not product or product.status != "ACTIVE":
                continue
            variant = item.variant
            if item.variant_id is not None and (
                not variant or variant.product_id != product.id or not variant.is_active
            ):
                continue
            supplier_items.setdefault(int(product.seller_id), []).append(item)

        if not supplier_items:
            raise ShiprocketError(
                "No available supplier items are present in the cart.",
                code="NO_SHIPPABLE_ITEMS",
                retryable=False,
            )

        delivery_postcode = re.sub(r"\s+", "", str(address.postal_code or ""))
        if not re.fullmatch(r"[1-9]\d{5}", delivery_postcode):
            raise ShiprocketError(
                "The delivery pincode must be a valid 6-digit Indian pincode.",
                code="DELIVERY_PINCODE_INVALID",
                retryable=False,
            )

        breakdown = []
        total = Decimal("0.00")
        for supplier_id, supplier_cart_items in sorted(supplier_items.items()):
            pickup = cls._supplier_address(supplier_id)
            package = cls._package_dimensions(supplier_cart_items)
            supplier_subtotal = sum(
                (
                    money(item.variant.price if item.variant else item.product.price)
                    * int(item.quantity or 0)
                    for item in supplier_cart_items
                ),
                Decimal("0.00"),
            )
            try:
                pickup_postcode = int(re.sub(r"\s+", "", str(pickup["pin_code"])))
                delivery_pin = int(delivery_postcode)
            except (TypeError, ValueError):
                raise ShiprocketError(
                    "Both supplier and customer pincodes must be valid before payment.",
                    code="PINCODE_INVALID",
                    retryable=False,
                )

            response = cls._request(
                "GET",
                "/courier/serviceability/",
                params={
                    "pickup_postcode": pickup_postcode,
                    "delivery_postcode": delivery_pin,
                    "cod": 0,
                    "weight": package["weight"],
                    "length": package["length"],
                    "breadth": package["breadth"],
                    "height": package["height"],
                    "declared_value": float(supplier_subtotal),
                },
            )
            data = response.get("data") if isinstance(response, dict) else None
            data = data if isinstance(data, dict) else {}
            rows = (
                data.get("available_courier_companies")
                or data.get("available_courier")
                or []
            )
            if not isinstance(rows, list):
                rows = []

            eligible = []
            for row in rows:
                if not isinstance(row, dict) or row.get("blocked") in (1, "1", True):
                    continue
                courier_id = cls._int_or_none(
                    row.get("courier_company_id") or row.get("id")
                )
                rate_value = row.get("freight_charge")
                if rate_value in (None, ""):
                    rate_value = row.get("rate")
                try:
                    rate = Decimal(str(rate_value))
                except Exception:
                    continue
                if courier_id is None or rate < 0:
                    continue
                eligible.append((courier_id, rate, row))

            if not eligible:
                raise ShiprocketError(
                    f"Shiprocket has no usable delivery quote for supplier pincode {pickup_postcode} to {delivery_postcode}.",
                    code="NO_SERVICEABLE_COURIER",
                    retryable=False,
                )

            recommended_id = cls._int_or_none(
                data.get("recommended_courier_company_id")
                or data.get("shiprocket_recommended_courier_id")
            )
            selected = next(
                (item for item in eligible if item[0] == recommended_id),
                None,
            )
            if selected is None:
                selected = min(eligible, key=lambda item: item[1])

            courier_id, rate, row = selected
            rate = money(rate)
            total += rate
            breakdown.append(
                {
                    "supplier_id": supplier_id,
                    "pickup_postcode": str(pickup_postcode),
                    "delivery_postcode": delivery_postcode,
                    "shipping_charge": float(rate),
                    "courier_company_id": courier_id,
                    "courier_name": str(row.get("courier_name") or "").strip() or None,
                    "estimated_delivery_days": row.get("estimated_delivery_days"),
                    "etd": row.get("etd") or row.get("edd"),
                    "weight": package["weight"],
                }
            )

        total = money(total)
        current_app.logger.info(
            "Shiprocket checkout quote: account=%s address=%s suppliers=%s total=%s",
            account_id,
            address.id,
            len(breakdown),
            total,
        )
        return {
            "shipping_charge": float(total),
            "currency": "INR",
            "suppliers": breakdown,
        }

    @classmethod
    def _check_serviceability(cls, shipment, order, items):
        """Preflight courier availability for the real supplier/customer pincodes.

        Shiprocket's current courier serviceability API accepts pickup/delivery
        postcodes plus weight for prepaid/COD determination. This does not claim
        that a street address is GPS-verified; it only prevents obviously
        unserviceable postal routes from reaching order creation.
        """
        pickup = cls._supplier_address(shipment.supplier_id)
        package = cls._package_dimensions(items)
        try:
            pickup_postcode = int(pickup["pin_code"])
            delivery_postcode = int(
                re.sub(r"\s+", "", str(order.delivery_postal_code or ""))
            )
        except (TypeError, ValueError):
            raise ShiprocketError(
                "Both supplier and customer pincodes must be valid before shipment creation.",
                code="PINCODE_INVALID",
            )
        response = cls._request(
            "GET",
            "/courier/serviceability/",
            params={
                "pickup_postcode": pickup_postcode,
                "delivery_postcode": delivery_postcode,
                "cod": 0,
                "weight": package["weight"],
            },
        )
        rows = []
        data = response.get("data") if isinstance(response, dict) else None
        if isinstance(data, dict):
            rows = (
                data.get("available_courier_companies")
                or data.get("available_courier")
                or []
            )
        elif isinstance(data, list):
            rows = data
        if isinstance(rows, list) and not rows:
            raise ShiprocketError(
                "Shiprocket reports no serviceable courier for this supplier-to-customer route.",
                code="NO_SERVICEABLE_COURIER",
                retryable=False,
            )
        current_app.logger.info(
            "Shiprocket serviceability passed: order=%s supplier=%s pickup_pin=%s delivery_pin=%s couriers=%s",
            order.id,
            shipment.supplier_id,
            pickup_postcode,
            delivery_postcode,
            len(rows) if isinstance(rows, list) else 0,
        )
        # Serviceability can expose a preliminary ETD before an AWB exists.
        # Persist it as a provisional Shiprocket estimate; tracking data later
        # replaces it when a concrete shipment ETA is available.
        if isinstance(rows, list) and rows and not shipment.estimated_delivery_at:
            for row in rows:
                if not isinstance(row, dict):
                    continue
                etd = cls._parse_datetime(
                    cls._pick(
                        row,
                        "etd",
                        "edd",
                        "estimated_delivery_date",
                        "estimated_delivery_at",
                        "expected_delivery_date",
                    )
                )
                if etd:
                    shipment.estimated_delivery_at = etd
                    db.session.commit()
                    break
        return response

    @classmethod
    def _create_shiprocket_order(cls, shipment, order, supplier_id, items):
        # Recover any pre-existing external order before doing other remote calls.
        # This is important when an earlier create request succeeded remotely but
        # the response was lost.
        legacy_reference = str(shipment.shiprocket_reference_id or "").strip()
        existing = cls._find_existing_order(legacy_reference)
        if cls._apply_reconciled_order(shipment, existing):
            return
        cls._repair_legacy_reference(shipment)

        pickup = cls._get_or_create_pickup(supplier_id)
        shipment.pickup_location_id = pickup["id"] or None
        shipment.pickup_location = pickup["name"] or None
        db.session.commit()

        existing = cls._find_existing_order(shipment.shiprocket_reference_id)
        if cls._apply_reconciled_order(shipment, existing):
            return

        cls._check_serviceability(shipment, order, items)
        payload = cls._build_payload(order, supplier_id, items, pickup["name"])
        try:
            response = cls._request("POST", "/orders/create/adhoc", json_body=payload)
        except ShiprocketError as exc:
            if exc.status_code == 422 or exc.code == "HTTP_422":
                reconciled = cls._find_existing_order(shipment.shiprocket_reference_id)
                if cls._apply_reconciled_order(shipment, reconciled):
                    return
            raise
        shiprocket_order_id = cls._pick(response, "order_id", "id")
        shiprocket_shipment_id = cls._pick(response, "shipment_id")
        if shiprocket_order_id is None or shiprocket_shipment_id is None:
            reconciled = cls._find_existing_order(shipment.shiprocket_reference_id)
            if cls._apply_reconciled_order(shipment, reconciled):
                return
            raise ShiprocketError(
                "Shiprocket did not return the external order and shipment IDs.",
                code="CREATE_RESPONSE_INCOMPLETE",
                retryable=True,
            )
        shipment.shiprocket_order_id = int(shiprocket_order_id)
        shipment.shiprocket_shipment_id = int(shiprocket_shipment_id)
        shipment.status = "ORDER_CREATED"
        shipment.failure_code = None
        shipment.failure_message = None
        shipment.last_synced_at = datetime.utcnow()
        db.session.commit()

    @classmethod
    def _assign_awb(cls, shipment):
        if not shipment.shiprocket_shipment_id:
            raise ShiprocketError(
                "Cannot assign an AWB before shipment creation.",
                code="SHIPMENT_ID_MISSING",
            )
        awb_body = {"shipment_id": int(shipment.shiprocket_shipment_id)}
        if shipment.quoted_courier_company_id:
            awb_body["courier_id"] = int(shipment.quoted_courier_company_id)
        response = cls._request(
            "POST",
            "/courier/assign/awb",
            json_body=awb_body,
        )
        result = response.get("response") if isinstance(response, dict) else None
        data = result.get("data") if isinstance(result, dict) else None
        data = data if isinstance(data, dict) else {}
        if isinstance(response, dict) and response.get("awb_assign_status") in (
            0,
            "0",
            False,
        ):
            error_message = (
                cls._pick(data, "awb_assign_error", "message", "error")
                or "Shiprocket could not assign an AWB."
            )
            raise ShiprocketError(
                str(error_message),
                code="AWB_NOT_ASSIGNED",
                retryable=True,
            )
        awb = cls._pick(data, "awb_code") or cls._pick(response, "awb_code")
        if not awb:
            raise ShiprocketError(
                "Shiprocket did not return an AWB code.",
                code="AWB_NOT_ASSIGNED",
                retryable=True,
            )
        shipment.awb_code = str(awb)
        shipment.courier_company_id = cls._int_or_none(
            cls._pick(data, "courier_company_id")
            or cls._pick(response, "courier_company_id")
        )
        shipment.courier_name = cls._pick(data, "courier_name", "courier") or cls._pick(
            response, "courier_name", "courier"
        )
        shipment.awb_assigned_at = datetime.utcnow()
        shipment.status = "AWB ASSIGNED"
        shipment.failure_code = None
        shipment.failure_message = None
        shipment.last_synced_at = datetime.utcnow()
        db.session.commit()

    @classmethod
    def _generate_label(cls, shipment):
        if shipment.label_url:
            return shipment.label_url
        if not shipment.shiprocket_shipment_id:
            raise ShiprocketError(
                "Cannot generate a label before shipment creation.",
                code="SHIPMENT_ID_MISSING",
            )
        if not shipment.awb_code:
            raise ShiprocketError(
                "Cannot generate a label before AWB assignment.",
                code="AWB_REQUIRED_FOR_LABEL",
            )
        response = cls._request(
            "POST",
            "/courier/generate/label",
            json_body={"shipment_id": [int(shipment.shiprocket_shipment_id)]},
        )
        candidates = []
        if isinstance(response, dict):
            candidates.extend([response.get("label_url"), response.get("label")])
            data = response.get("data")
            if isinstance(data, dict):
                candidates.extend([data.get("label_url"), data.get("label")])
        label_url = next((str(v).strip() for v in candidates if v), None)
        if not label_url:
            raise ShiprocketError(
                "Shiprocket did not return a shipping label URL.",
                code="LABEL_NOT_GENERATED",
                retryable=True,
            )
        shipment.label_url = label_url
        shipment.last_synced_at = datetime.utcnow()
        shipment.failure_code = None
        shipment.failure_message = None
        db.session.commit()
        NotificationService.create(
            account_id=shipment.supplier_id,
            title="Shipping label ready",
            message=f"The shipping label for order #{shipment.order_id} is ready to print.",
            notification_type=NotificationType.ORDER,
            dedupe_key=f"order:{shipment.order_id}:supplier:{shipment.supplier_id}:label-ready",
        )
        current_app.logger.info(
            "Shiprocket label generated: order=%s supplier=%s shipment=%s",
            shipment.order_id,
            shipment.supplier_id,
            shipment.shiprocket_shipment_id,
        )
        return label_url

    @classmethod
    def _request_pickup(cls, shipment):
        if not shipment.shiprocket_shipment_id:
            raise ShiprocketError(
                "Cannot schedule pickup before shipment creation.",
                code="SHIPMENT_ID_MISSING",
            )
        response = cls._request(
            "POST",
            "/courier/generate/pickup",
            json_body={"shipment_id": [int(shipment.shiprocket_shipment_id)]},
        )
        result = response.get("response") if isinstance(response, dict) else None
        result = result if isinstance(result, dict) else {}
        pickup_status = cls._pick(response, "pickup_status")
        if pickup_status in (0, "0", False):
            raise ShiprocketError(
                str(
                    cls._pick(result, "data", "message", "error")
                    or "Shiprocket pickup request failed."
                ),
                code="PICKUP_REQUEST_FAILED",
                retryable=True,
            )
        pickup_date = cls._pick(result, "pickup_scheduled_date")
        if pickup_date:
            shipment.pickup_scheduled_at = (
                cls._parse_datetime(pickup_date) or datetime.utcnow()
            )
        shipment.status = "PICKUP SCHEDULED"
        shipment.failure_code = None
        shipment.failure_message = None
        shipment.last_synced_at = datetime.utcnow()
        db.session.commit()

    @classmethod
    def _generate_manifest(cls, shipment):
        if not shipment.shiprocket_shipment_id:
            raise ShiprocketError(
                "Cannot generate a manifest before shipment creation.",
                code="SHIPMENT_ID_MISSING",
            )
        cls._request(
            "POST",
            "/manifests/generate",
            json_body={"shipment_id": [int(shipment.shiprocket_shipment_id)]},
        )
        shipment.status = "MANIFEST GENERATED"
        shipment.last_synced_at = datetime.utcnow()
        db.session.commit()

    @classmethod
    def _refresh_tracking_internal(cls, shipment, payload):
        return cls._apply_external_status(shipment, payload, from_webhook=False)

    @classmethod
    def _apply_external_status(cls, shipment, payload, *, from_webhook):
        if not isinstance(payload, dict):
            raise ShiprocketError(
                "Invalid Shiprocket tracking payload.", code="INVALID_TRACKING_PAYLOAD"
            )
        status_text = (
            str(cls._pick(payload, "current_status", "shipment_status", "status") or "")
            .strip()
            .upper()
        )
        if not status_text:
            return False

        event_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        if from_webhook and shipment.last_webhook_hash == event_hash:
            return False

        previous = (shipment.status or "PENDING").strip().upper()
        previous_rank = cls.STATUS_RANKS.get(previous, -1)
        incoming_rank = cls.STATUS_RANKS.get(status_text, previous_rank)
        if status_text == previous and from_webhook:
            shipment.last_webhook_hash = event_hash
            shipment.last_webhook_at = datetime.utcnow()
            shipment.last_synced_at = datetime.utcnow()
            db.session.commit()
            return False
        if incoming_rank < previous_rank and not any(
            marker in status_text for marker in cls.FAILURE_MARKERS
        ):
            return False

        shipment.status = status_text
        shipment.status_id = cls._int_or_none(
            cls._pick(payload, "current_status_id", "shipment_status_id")
        )
        shipment.courier_name = (
            cls._pick(payload, "courier_name") or shipment.courier_name
        )
        shipment.awb_code = (
            str(cls._pick(payload, "awb") or shipment.awb_code or "") or None
        )
        shipment.last_synced_at = datetime.utcnow()
        if from_webhook:
            shipment.last_webhook_hash = event_hash
            shipment.last_webhook_at = datetime.utcnow()

        timestamp = cls._parse_datetime(
            cls._pick(payload, "current_timestamp", "timestamp")
        )
        if status_text == "DELIVERED":
            shipment.delivered_at = (
                timestamp or shipment.delivered_at or datetime.utcnow()
            )
        if (
            timestamp
            and status_text in {"PICKED UP", "SHIPPED", "IN TRANSIT"}
            and not shipment.awb_assigned_at
        ):
            shipment.awb_assigned_at = timestamp

        cls._sync_clipcart_state(shipment, status_text)
        db.session.commit()
        return True

    @staticmethod
    def _int_or_none(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        text = str(value).strip()
        # Shiprocket may return a relative ETD such as "2 days" from
        # serviceability. Convert that real provider value into a concrete
        # server-side estimate without inventing a delivery window.
        relative = re.fullmatch(r"(?i)(\d+)\s+days?", text)
        if relative:
            return datetime.utcnow() + timedelta(days=int(relative.group(1)))
        for fmt in (
            None,
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d %b %Y",
            "%b %d, %Y",
        ):
            try:
                if fmt:
                    return datetime.strptime(text, fmt)
                return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
            except ValueError:
                continue
        return None

    @classmethod
    def _sync_clipcart_state(cls, shipment, external_status):
        order = shipment.order
        assignment = DeliveryAssignment.query.filter_by(order_id=order.id).first()
        if not assignment:
            assignment = DeliveryAssignment(order_id=order.id)
            db.session.add(assignment)
            db.session.flush()

        normalized = external_status.upper()
        if any(marker in normalized for marker in cls.FAILURE_MARKERS):
            assignment.delivery_status = DeliveryStatus.FAILED
            assignment.failed_reason = f"Courier status: {external_status}"
            if order.status not in {OrderStatus.CANCELLED, OrderStatus.RETURNED}:
                # The external courier controls delivery state; preserve internal order unless cancelled.
                pass
            return

        mapped = cls.STATUS_MAP.get(normalized)
        if not mapped:
            return
        pickup_status, delivery_status, order_stage = mapped
        assignment.pickup_status = pickup_status
        if delivery_status != DeliveryStatus.NOT_STARTED:
            assignment.delivery_status = delivery_status

        if normalized in {
            "PICKED UP",
            "SHIPPED",
            "IN TRANSIT",
            "REACHED AT DESTINATION HUB",
        }:
            if order.status not in {
                OrderStatus.CANCELLED,
                OrderStatus.RETURNED,
                OrderStatus.OUT_FOR_DELIVERY,
                OrderStatus.DELIVERED,
            }:
                order.status = OrderStatus.SHIPPED
            if not assignment.pickup_time:
                assignment.pickup_time = shipment.last_synced_at or datetime.utcnow()
            if assignment.delivery_status == DeliveryStatus.IN_TRANSIT:
                assignment.next_action = "Awaiting courier delivery updates"
        elif normalized == "OUT FOR DELIVERY":
            if order.status not in {
                OrderStatus.CANCELLED,
                OrderStatus.RETURNED,
                OrderStatus.DELIVERED,
            }:
                order.status = OrderStatus.OUT_FOR_DELIVERY
            assignment.out_for_delivery_time = (
                shipment.last_synced_at or datetime.utcnow()
            )
            assignment.next_action = "Complete delivery with proof photo"
        elif normalized == "DELIVERED":
            # Shiprocket is authoritative for the customer's forward-delivery state.
            # A separate Clipcart proof photo may still be required to close the
            # internal logistics task, but it must not keep a genuinely delivered
            # customer order stuck in SHIPPED.
            all_shipments = Shipment.query.filter_by(order_id=order.id).all()
            all_delivered = bool(all_shipments) and all(
                (row.status or "").upper() == "DELIVERED" for row in all_shipments
            )
            if all_delivered:
                if order.status not in {OrderStatus.CANCELLED, OrderStatus.RETURNED}:
                    order.status = OrderStatus.DELIVERED
                assignment.delivery_time = (
                    assignment.delivery_time
                    or shipment.delivered_at
                    or datetime.utcnow()
                )
                if assignment.proof_of_delivery_image_url:
                    assignment.delivery_status = DeliveryStatus.DELIVERED
                    assignment.next_action = None
                else:
                    # Keep the internal proof-photo task pending without downgrading
                    # the customer-facing order status.
                    assignment.delivery_status = DeliveryStatus.OUT_FOR_DELIVERY
                    assignment.next_action = (
                        "Upload completion photo to finalize delivery"
                    )
            else:
                assignment.delivery_status = DeliveryStatus.OUT_FOR_DELIVERY
                assignment.next_action = "Awaiting remaining supplier shipment(s)"

        event_type = {
            "PICKED UP": "PICKED_UP",
            "SHIPPED": "SHIPPED",
            "OUT FOR DELIVERY": "OUT_FOR_DELIVERY",
            "DELIVERED": "COURIER_DELIVERED",
        }.get(normalized)
        if event_type and event_type != "COURIER_DELIVERED":
            OrderEventService.add(
                order,
                event_type,
                f"Courier status: {external_status}",
                f"Shiprocket updated order #{order.id} to {external_status.title()}.",
            )
        elif event_type == "COURIER_DELIVERED":
            NotificationService.create(
                account_id=order.account_id,
                title="Courier delivered your order",
                message=f"Courier delivery for order #{order.id} is confirmed. Delivery proof is being finalized in Clipcart.",
                notification_type=NotificationType.ORDER,
                dedupe_key=f"order:{order.id}:courier-delivered:{shipment.id}",
                commit=False,
            )
            NotificationService.notify_logistics(
                title="Courier marked shipment delivered",
                message=f"Order #{order.id} has a courier-delivered update. Complete Clipcart delivery with the required proof photo.",
                dedupe_key_prefix=f"order:{order.id}:courier-delivered",
            )

    @classmethod
    def _provision_shipment(cls, shipment):
        current_app.logger.info(
            "Starting Shiprocket provisioning for Clipcart order=%s supplier=%s ref=%s",
            shipment.order_id,
            shipment.supplier_id,
            shipment.shiprocket_reference_id,
        )
        order = (
            Order.query.options(
                selectinload(Order.items).joinedload(OrderItem.product),
                selectinload(Order.items).joinedload(OrderItem.variant),
            )
            .filter_by(id=shipment.order_id)
            .first()
        )
        if not order:
            raise ShiprocketError("Clipcart order not found.", code="ORDER_NOT_FOUND")
        if order.status in {OrderStatus.CANCELLED, OrderStatus.RETURNED}:
            return shipment
        if not shipment.shiprocket_order_id and order.status not in {
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.DELIVERED,
        }:
            raise ShiprocketError(
                "Supplier must start processing the paid order before Shiprocket shipment creation.",
                code="SUPPLIER_PROCESSING_REQUIRED",
            )

        items = [
            item
            for item in order.items
            if item.supplier_id_snapshot == shipment.supplier_id
            or (item.product and item.product.seller_id == shipment.supplier_id)
        ]
        if not items:
            raise ShiprocketError(
                "No items for this supplier were found in the order.",
                code="SUPPLIER_ITEMS_NOT_FOUND",
            )

        if not shipment.shiprocket_order_id:
            cls._create_shiprocket_order(shipment, order, shipment.supplier_id, items)
        if not shipment.awb_code:
            cls._assign_awb(shipment)
        if not shipment.label_url:
            cls._generate_label(shipment)
        if not shipment.pickup_scheduled_at:
            cls._request_pickup(shipment)
        if shipment.status != "MANIFEST GENERATED":
            cls._generate_manifest(shipment)
        current_app.logger.info(
            "Shiprocket provisioning completed for Clipcart order=%s supplier=%s sr_order=%s sr_shipment=%s awb=%s status=%s",
            shipment.order_id,
            shipment.supplier_id,
            shipment.shiprocket_order_id,
            shipment.shiprocket_shipment_id,
            shipment.awb_code,
            shipment.status,
        )
        return shipment

    @classmethod
    def ensure_supplier_shipment(cls, order_id, supplier_id, *, propagate=False):
        rows = cls.ensure_order_shipments(
            order_id, supplier_id=int(supplier_id), propagate=propagate
        )
        return rows[0] if rows else None

    @classmethod
    def ensure_order_shipments(cls, order_id, *, supplier_id=None, propagate=False):
        order = (
            Order.query.options(
                selectinload(Order.items).joinedload(OrderItem.product),
                selectinload(Order.items).joinedload(OrderItem.variant),
            )
            .filter_by(id=order_id)
            .first()
        )
        if not order:
            raise ShiprocketError("Clipcart order not found.", code="ORDER_NOT_FOUND")
        if order.status == OrderStatus.CANCELLED:
            return []
        if order.status != OrderStatus.PAID and order.status not in {
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.DELIVERED,
        }:
            return []

        if supplier_id is not None:
            requested_supplier = int(supplier_id)
            owns_items = any(
                item.product and item.product.seller_id == requested_supplier
                for item in order.items
            )
            if not owns_items:
                raise ShiprocketError(
                    "This supplier does not own any items in the order.",
                    code="SUPPLIER_ORDER_ACCESS_DENIED",
                )
            supplier_ids = [requested_supplier]
        else:
            # Admin/logistics retry only reconciles shipments that were already
            # started. It must not create shipments for suppliers who have not
            # clicked Start Processing yet.
            supplier_ids = sorted(
                {
                    row.supplier_id
                    for row in Shipment.query.filter_by(order_id=order.id).all()
                }
            )
        result = []
        for supplier_id in supplier_ids:
            reference = cls._supplier_key(order.id, supplier_id)
            shipment = (
                Shipment.query.filter_by(order_id=order.id, supplier_id=supplier_id)
                .with_for_update()
                .first()
            )
            if not shipment:
                shipment = Shipment(
                    order_id=order.id,
                    supplier_id=supplier_id,
                    shiprocket_reference_id=reference,
                    status="PENDING",
                )
                if isinstance(order.shipping_quote, dict):
                    for quote in order.shipping_quote.get("suppliers", []):
                        if int(quote.get("supplier_id") or 0) == int(supplier_id):
                            shipment.quoted_shipping_charge = money(
                                quote.get("shipping_charge") or 0
                            )
                            shipment.quoted_courier_company_id = cls._int_or_none(
                                quote.get("courier_company_id")
                            )
                            shipment.quoted_courier_name = (
                                str(quote.get("courier_name") or "").strip() or None
                            )
                            break
                try:
                    db.session.add(shipment)
                    db.session.flush()
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    shipment = (
                        Shipment.query.filter_by(
                            order_id=order.id, supplier_id=supplier_id
                        )
                        .with_for_update()
                        .first()
                    )
                    if not shipment:
                        raise
            if shipment.quoted_shipping_charge is None and isinstance(
                order.shipping_quote, dict
            ):
                for quote in order.shipping_quote.get("suppliers", []):
                    if int(quote.get("supplier_id") or 0) == int(supplier_id):
                        shipment.quoted_shipping_charge = money(
                            quote.get("shipping_charge") or 0
                        )
                        shipment.quoted_courier_company_id = cls._int_or_none(
                            quote.get("courier_company_id")
                        )
                        shipment.quoted_courier_name = (
                            str(quote.get("courier_name") or "").strip() or None
                        )
                        db.session.commit()
                        break
            try:
                cls._provision_shipment(shipment)
            except ShiprocketError as exc:
                current_app.logger.error(
                    "Shiprocket provisioning failed: order=%s supplier=%s ref=%s code=%s status=%s message=%s",
                    order.id,
                    supplier_id,
                    shipment.shiprocket_reference_id,
                    exc.code,
                    exc.status_code,
                    str(exc)[:500],
                )
                shipment.status = "FAILED"
                shipment.failure_code = exc.code or "SHIPROCKET_ERROR"
                shipment.failure_message = str(exc)[:1000]
                shipment.last_synced_at = datetime.utcnow()
                db.session.commit()
                if propagate:
                    raise
            except Exception as exc:
                current_app.logger.exception(
                    "Unexpected Shiprocket provisioning error: order=%s supplier=%s ref=%s",
                    order.id,
                    supplier_id,
                    shipment.shiprocket_reference_id,
                )
                db.session.rollback()
                shipment = Shipment.query.filter_by(
                    order_id=order.id, supplier_id=supplier_id
                ).first()
                if shipment:
                    shipment.status = "FAILED"
                    shipment.failure_code = "INTERNAL_ERROR"
                    shipment.failure_message = str(exc)[:1000]
                    shipment.last_synced_at = datetime.utcnow()
                    db.session.commit()
                if propagate:
                    raise
            result.append(shipment)
        current_app.logger.info(
            "Shiprocket ensure_order_shipments finished: order=%s shipments=%s",
            order.id,
            [
                {
                    "supplier_id": row.supplier_id,
                    "status": row.status,
                    "awb": row.awb_code,
                    "failure_code": row.failure_code,
                }
                for row in result
            ],
        )
        return result

    @classmethod
    def _extract_tracking_snapshot(cls, payload):
        """Normalize current Shiprocket tracking response into stable Clipcart fields."""
        if not isinstance(payload, dict):
            return {
                "raw": {},
                "status": "",
                "awb": None,
                "courier": None,
                "etd": None,
                "tracking_url": None,
                "timestamp": None,
                "events": [],
            }

        candidates = []
        for key in ("tracking_data", "data", "tracking"):
            value = payload.get(key)
            if isinstance(value, dict):
                candidates.append(value)
        candidates.append(payload)

        data = next((item for item in candidates if item), {})
        track_rows = (
            data.get("shipment_track")
            if isinstance(data.get("shipment_track"), list)
            else []
        )
        activities = (
            data.get("shipment_track_activities")
            if isinstance(data.get("shipment_track_activities"), list)
            else []
        )
        latest = track_rows[-1] if track_rows else {}
        merged = dict(data)
        if isinstance(latest, dict):
            merged.update(latest)

        etd = cls._pick(
            merged,
            "etd",
            "edd",
            "estimated_delivery_date",
            "estimated_delivery_at",
            "expected_delivery_date",
            "expected_delivery_at",
        )
        tracking_url = cls._pick(
            merged,
            "track_url",
            "tracking_url",
            "tracking_link",
            "tracking_url_text",
            "url",
        )
        status = cls._pick(
            merged,
            "current_status",
            "shipment_status",
            "status",
            "shipment_status_text",
        )
        awb = cls._pick(merged, "awb_code", "awb")
        courier = cls._pick(merged, "courier_name", "courier", "courier_company")
        timestamp = cls._pick(
            merged,
            "current_timestamp",
            "timestamp",
            "event_date",
            "delivered_date",
            "latest_status_date",
            "last_updated_at",
        )
        events = (
            activities or track_rows or merged.get("shipment_track_activities") or []
        )
        return {
            "raw": data,
            "status": str(status or "").strip().upper(),
            "awb": str(awb or "").strip() or None,
            "courier": str(courier or "").strip() or None,
            "etd": cls._parse_datetime(etd),
            "tracking_url": str(tracking_url or "").strip() or None,
            "timestamp": cls._parse_datetime(timestamp),
            "events": events if isinstance(events, list) else [],
        }

    @classmethod
    def track_shipment(cls, shipment):
        if not shipment.awb_code and not shipment.shiprocket_shipment_id:
            raise ShiprocketError(
                "Shipment has not been created in Shiprocket.",
                code="SHIPMENT_NOT_CREATED",
            )
        if shipment.awb_code:
            payload = cls._request("GET", f"/courier/track/awb/{shipment.awb_code}")
        else:
            payload = cls._request(
                "GET", f"/courier/track/shipment/{shipment.shiprocket_shipment_id}"
            )
        snapshot = cls._extract_tracking_snapshot(payload)
        if snapshot["status"]:
            cls._refresh_tracking_internal(
                shipment,
                {
                    **snapshot["raw"],
                    "current_status": snapshot["status"],
                    "awb": snapshot["awb"],
                    "courier_name": snapshot["courier"],
                },
            )
        shipment.awb_code = snapshot["awb"] or shipment.awb_code
        shipment.courier_name = snapshot["courier"] or shipment.courier_name
        shipment.tracking_url = snapshot["tracking_url"] or shipment.tracking_url
        shipment.estimated_delivery_at = (
            snapshot["etd"] or shipment.estimated_delivery_at
        )
        shipment.tracking_data = (
            snapshot["raw"] if isinstance(snapshot["raw"], dict) else None
        )
        shipment.tracking_events = (
            snapshot["events"] if isinstance(snapshot["events"], list) else None
        )
        if snapshot["timestamp"]:
            shipment.last_tracking_event_at = snapshot["timestamp"]
        shipment.last_synced_at = datetime.utcnow()
        db.session.commit()
        return shipment

    @classmethod
    def diagnostics(cls, order_id=None):
        result = {
            "configured": cls.configured(),
            "authentication": {"ok": False},
            "orders_api": {"ok": False},
            "pickup_api": {"ok": False, "count": 0},
            "order": None,
            "external_matches": [],
        }
        if not result["configured"]:
            result["error"] = (
                "Shiprocket credentials/base URL are not configured on the backend."
            )
            return result

        try:
            cls._auth()
            result["authentication"] = {"ok": True}
        except ShiprocketError as exc:
            result["authentication"] = {
                "ok": False,
                "code": exc.code,
                "status_code": exc.status_code,
                "message": str(exc),
            }
            result["error"] = "Shiprocket authentication failed."
            return result

        try:
            payload = cls._request(
                "GET",
                "/orders",
                params={"per_page": 1, "page": 1},
            )
            rows = payload.get("data") if isinstance(payload, dict) else None
            result["orders_api"] = {
                "ok": True,
                "sample_count": len(rows) if isinstance(rows, list) else 0,
            }
        except ShiprocketError as exc:
            result["orders_api"] = {
                "ok": False,
                "code": exc.code,
                "status_code": exc.status_code,
                "message": str(exc),
            }

        try:
            payload = cls._request("GET", "/settings/company/pickup")
            rows = []
            if isinstance(payload, dict):
                data = payload.get("data")
                if isinstance(data, dict):
                    rows = (
                        data.get("shipping_address")
                        or data.get("pickup_locations")
                        or []
                    )
                elif isinstance(data, list):
                    rows = data
                else:
                    rows = (
                        payload.get("shipping_address")
                        or payload.get("pickup_locations")
                        or []
                    )
            elif isinstance(payload, list):
                rows = payload
            result["pickup_api"] = {
                "ok": True,
                "count": len(rows) if isinstance(rows, list) else 0,
            }
        except ShiprocketError as exc:
            result["pickup_api"] = {
                "ok": False,
                "code": exc.code,
                "status_code": exc.status_code,
                "message": str(exc),
            }

        if order_id is None:
            return result

        order = Order.query.get(int(order_id))
        if not order:
            result["order"] = {"ok": False, "message": "Clipcart order not found."}
            return result

        shipments = (
            Shipment.query.filter_by(order_id=order.id).order_by(Shipment.id).all()
        )
        result["order"] = {
            "ok": True,
            "order_id": order.id,
            "order_status": order.status.value if order.status else None,
            "local_shipments": [
                {
                    "id": row.id,
                    "supplier_id": row.supplier_id,
                    "reference_id": row.shiprocket_reference_id,
                    "status": row.status,
                    "shiprocket_order_id": row.shiprocket_order_id,
                    "shiprocket_shipment_id": row.shiprocket_shipment_id,
                    "awb_code": row.awb_code,
                    "failure_code": row.failure_code,
                    "failure_message": row.failure_message,
                }
                for row in shipments
            ],
        }

        if not result["orders_api"]["ok"]:
            return result

        supplier_ids = sorted(
            {
                int(item.supplier_id_snapshot)
                for item in order.items
                if item.supplier_id_snapshot
            }
            | {
                int(item.product.seller_id)
                for item in order.items
                if item.product and item.product.seller_id
            }
        )
        for supplier_id in supplier_ids:
            reference = cls._supplier_key(order.id, supplier_id)
            try:
                external = cls._find_existing_order(reference)
                result["external_matches"].append(
                    {
                        "supplier_id": supplier_id,
                        "reference_id": reference,
                        "found": bool(external),
                        "shiprocket_order_id": (
                            external.get("order_id") if external else None
                        ),
                        "shiprocket_shipment_id": (
                            external.get("shipment_id") if external else None
                        ),
                        "awb_code": external.get("awb") if external else None,
                        "status": external.get("status") if external else None,
                    }
                )
            except ShiprocketError as exc:
                result["external_matches"].append(
                    {
                        "supplier_id": supplier_id,
                        "reference_id": reference,
                        "found": False,
                        "error_code": exc.code,
                        "status_code": exc.status_code,
                        "error": str(exc),
                    }
                )
        return result

    @classmethod
    def retry_order(cls, order_id):
        return cls.ensure_order_shipments(order_id, propagate=True)

    @classmethod
    def apply_webhook(cls, payload):
        order_ref = str(cls._pick(payload, "order_id") or "").strip()
        awb = str(cls._pick(payload, "awb") or "").strip()
        sr_order_id = cls._int_or_none(cls._pick(payload, "sr_order_id"))
        shipment = None
        if order_ref:
            shipment = Shipment.query.filter_by(
                shiprocket_reference_id=order_ref
            ).first()
        if not shipment and sr_order_id:
            shipment = Shipment.query.filter_by(shiprocket_order_id=sr_order_id).first()
        if not shipment and awb:
            shipment = Shipment.query.filter_by(awb_code=awb).first()
        if not shipment:
            raise ShiprocketError(
                "No Clipcart shipment matches this Shiprocket webhook.",
                code="WEBHOOK_SHIPMENT_NOT_FOUND",
            )

        snapshot = cls._extract_tracking_snapshot(payload)
        shipment.tracking_data = (
            snapshot["raw"] if isinstance(snapshot["raw"], dict) else None
        )
        shipment.tracking_events = (
            snapshot["events"] if isinstance(snapshot["events"], list) else None
        )
        shipment.tracking_url = snapshot["tracking_url"] or shipment.tracking_url
        shipment.estimated_delivery_at = (
            snapshot["etd"] or shipment.estimated_delivery_at
        )
        if snapshot["timestamp"]:
            shipment.last_tracking_event_at = snapshot["timestamp"]
        result = cls._apply_external_status(shipment, payload, from_webhook=True)
        if result:
            db.session.commit()
        return result

    @classmethod
    def _reconcile_order_status_from_shipments(cls, order):
        """Advance the customer order to DELIVERED when every forward shipment is delivered.

        This is deliberately independent from the internal logistics proof-photo
        task. Shiprocket confirms the physical courier delivery; Clipcart may still
        require its own proof workflow before the logistics assignment is closed.
        """
        rows = Shipment.query.filter_by(order_id=order.id).all()
        if not rows or order.status in {OrderStatus.CANCELLED, OrderStatus.RETURNED}:
            return False
        all_delivered = all(
            (row.status or "").strip().upper() == "DELIVERED" for row in rows
        )
        if all_delivered and order.status != OrderStatus.DELIVERED:
            order.status = OrderStatus.DELIVERED
            db.session.commit()
            return True
        return False

    @classmethod
    def get_customer_shipments(cls, order, *, force_refresh=False):
        rows = sorted(
            list(getattr(order, "shipments", None) or []), key=lambda row: row.id
        )
        now = datetime.utcnow()
        for shipment in rows:
            if not shipment.awb_code and not shipment.shiprocket_shipment_id:
                continue
            stale = (
                force_refresh
                or not shipment.last_synced_at
                or (now - shipment.last_synced_at).total_seconds() > 300
            )
            if stale:
                try:
                    cls.track_shipment(shipment)
                except ShiprocketError:
                    db.session.rollback()
        # Reconcile even when tracking data is already fresh. This fixes existing
        # orders that were marked SHIPPED before the delivered-status rule was corrected.
        cls._reconcile_order_status_from_shipments(order)
        return [
            cls._serialize_shipment(shipment, include_supplier=False)
            for shipment in rows
        ]

    @classmethod
    def get_supplier_shipments(cls, order, supplier_id):
        rows = [
            shipment
            for shipment in (getattr(order, "shipments", None) or [])
            if shipment.supplier_id == supplier_id
        ]
        rows.sort(key=lambda row: row.id)
        return [
            cls._serialize_shipment(shipment, include_supplier=False)
            for shipment in rows
        ]

    @classmethod
    def get_logistics_shipments(cls, order):
        rows = sorted(
            list(getattr(order, "shipments", None) or []), key=lambda row: row.id
        )
        return [
            cls._serialize_shipment(shipment, include_supplier=True)
            for shipment in rows
        ]

    @staticmethod
    def _serialize_shipment(shipment, include_supplier=False):
        data = {
            "id": shipment.id,
            "status": shipment.status,
            "status_id": shipment.status_id,
            "awb_code": shipment.awb_code,
            "courier_name": shipment.courier_name,
            "pickup_scheduled_at": shipment.pickup_scheduled_at,
            "awb_assigned_at": shipment.awb_assigned_at,
            "last_synced_at": shipment.last_synced_at,
            "last_tracking_event_at": shipment.last_tracking_event_at,
            "delivered_at": shipment.delivered_at,
            "tracking_available": bool(
                shipment.awb_code or shipment.shiprocket_shipment_id
            ),
            "tracking_reference": shipment.awb_code,
            "label_available": bool(shipment.label_url),
            "estimated_delivery_at": shipment.estimated_delivery_at,
            "tracking_url": shipment.tracking_url,
            "tracking_events": shipment.tracking_events or [],
        }
        if include_supplier:
            data["reference_id"] = shipment.shiprocket_reference_id
            data["shiprocket_order_id"] = shipment.shiprocket_order_id
            data["shiprocket_shipment_id"] = shipment.shiprocket_shipment_id
            data["pickup_location_id"] = shipment.pickup_location_id
            data["pickup_location"] = shipment.pickup_location
            data["label_available"] = bool(shipment.label_url)
            data["label_url_available"] = bool(shipment.label_url)
            supplier = shipment.supplier
            verification = supplier.seller_verification if supplier else None
            data["supplier"] = {
                "id": shipment.supplier_id,
                "business_name": verification.business_name if verification else None,
                "name": supplier.full_name if supplier else None,
            }
            data["failure"] = (
                {
                    "code": shipment.failure_code,
                    "message": shipment.failure_message,
                }
                if shipment.failure_code or shipment.failure_message
                else None
            )
        return data

    @classmethod
    def cancel_order_shipments(cls, order_id):
        # Clipcart does not expose cancellation as an external shipment state. For
        # shipments which have not reached pickup, request the official Shiprocket
        # order cancellation endpoint. Already-picked shipments are left to the
        # existing return/RTO workflow rather than inventing reverse behavior.
        rows = Shipment.query.filter_by(order_id=order_id).all()
        for shipment in rows:
            if not shipment.shiprocket_order_id:
                continue
            current = (shipment.status or "").upper()
            if current in {
                "PICKED UP",
                "SHIPPED",
                "IN TRANSIT",
                "OUT FOR DELIVERY",
                "DELIVERED",
            }:
                continue
            try:
                cls._request(
                    "POST",
                    "/orders/cancel",
                    json_body={"ids": [int(shipment.shiprocket_order_id)]},
                )
                shipment.status = "CANCELLED"
                shipment.last_synced_at = datetime.utcnow()
                shipment.failure_code = None
                shipment.failure_message = None
                db.session.commit()
            except ShiprocketError as exc:
                shipment.failure_code = exc.code or "CANCEL_ERROR"
                shipment.failure_message = str(exc)[:1000]
                shipment.last_synced_at = datetime.utcnow()
                db.session.commit()
