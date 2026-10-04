import hashlib
import json
import threading
from datetime import datetime, timedelta
from decimal import Decimal

import requests
from flask import current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.modules.accounts.models import Account
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
            "DELIVERED_PENDING_PROOF",
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
            if len(message) > 500:
                message = message[:500]
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
            raise cls._response_error(response, "Shiprocket API request failed.")

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
        if not values["pin_code"].isdigit():
            raise ShiprocketError(
                "Supplier pickup postal code must contain digits only.",
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
                rows = data.get("shipping_address") or data.get("data") or []
            else:
                rows = locations.get("shipping_address") or data or []
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

        location_name = f"CC-{supplier_id}-{cls._pickup_fingerprint(values)}"[:100]
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
        return {
            "id": str(cls._pick(response, "pickup_id", "id") or ""),
            "name": location_name,
        }

    @classmethod
    def _package_dimensions(cls, items):
        rows = []
        for item in items:
            product = item.product
            if not product:
                raise ShiprocketError(
                    "A purchased product is unavailable.", code="PRODUCT_NOT_FOUND"
                )
            values = [
                product.shipping_weight_kg,
                product.shipping_length_cm,
                product.shipping_width_cm,
                product.shipping_height_cm,
            ]
            if any(value is None for value in values):
                raise ShiprocketError(
                    f"Shipping package data is missing for product '{product.name}'.",
                    code="PACKAGE_DATA_MISSING",
                )
            weight, length, width, height = [Decimal(str(value)) for value in values]
            if min(weight, length, width, height) <= 0:
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
    def _build_payload(cls, order, supplier_id, items, pickup_name):
        if not order.delivery_postal_code.isdigit():
            raise ShiprocketError(
                "Customer delivery postal code must contain digits only.",
                code="CUSTOMER_ADDRESS_INVALID",
            )
        pincode = int(order.delivery_postal_code)
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

        package = cls._package_dimensions(items)
        address_2 = " ".join(
            p.strip()
            for p in [order.delivery_address_line_2, order.delivery_landmark]
            if p and p.strip()
        )
        order_items = []
        supplier_subtotal = Decimal("0")
        for item in items:
            product = item.product
            variant = item.variant
            name = item.product_name_snapshot or product.name
            variant_label = item.variant_value_snapshot or (
                variant.value if variant else None
            )
            if variant_label:
                name = f"{name} - {variant_label}"
            order_items.append(
                {
                    "name": name[:255],
                    "sku": (variant.sku if variant else product.sku)
                    or f"CLP-{product.id}",
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
        comment = f"Clipcart platform fee/tax allocated to supplier shipment: marketing fee ₹{marketing_allocation:.2f}, tax ₹{tax_allocation:.2f}."
        return {
            "order_id": supplier_key,
            "order_date": (order.created_at or datetime.utcnow()).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "pickup_location": pickup_name,
            "billing_customer_name": (
                order.delivery_full_name or order.customer_name or "Customer"
            ).strip()[:100],
            "billing_address": (order.delivery_address_line_1 or "").strip()[:255],
            "billing_address_2": address_2[:255],
            "billing_city": (order.delivery_city or "").strip(),
            "billing_pincode": pincode,
            "billing_state": (order.delivery_state or "").strip(),
            "billing_country": (order.delivery_country or "India").strip(),
            "billing_email": (order.customer_email or "").strip(),
            "billing_phone": (order.delivery_phone or "").strip(),
            "shipping_is_billing": True,
            "shipping_customer_name": (
                order.delivery_full_name or order.customer_name or "Customer"
            ).strip()[:100],
            "shipping_address": (order.delivery_address_line_1 or "").strip()[:255],
            "shipping_address_2": address_2[:255],
            "shipping_city": (order.delivery_city or "").strip(),
            "shipping_pincode": pincode,
            "shipping_state": (order.delivery_state or "").strip(),
            "shipping_country": (order.delivery_country or "India").strip(),
            "shipping_email": (order.customer_email or "").strip(),
            "shipping_phone": (order.delivery_phone or "").strip(),
            "order_items": order_items,
            "payment_method": "Prepaid",
            "shipping_charges": 0,
            "giftwrap_charges": 0,
            "transaction_charges": float(marketing_allocation),
            "total_discount": float(supplier_discount),
            "tax": float(tax_allocation),
            "comment": comment,
            "sub_total": float(
                max(supplier_subtotal - supplier_discount, Decimal("0"))
            ),
            "length": package["length"],
            "breadth": package["breadth"],
            "height": package["height"],
            "weight": package["weight"],
            "shipping_method": current_app.config.get(
                "SHIPROCKET_SHIPPING_METHOD", "SR"
            ),
        }

    @staticmethod
    def _supplier_key(order_id, supplier_id):
        # Shiprocket's custom-order documentation advises numeric source order IDs.
        # Fixed-width components keep this deterministic and collision-free for the
        # normal Clipcart integer ID ranges while staying well below 50 characters.
        return f"{int(order_id):08d}{int(supplier_id):08d}"

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
    def _create_shiprocket_order(cls, shipment, order, supplier_id, items):
        pickup = cls._get_or_create_pickup(supplier_id)
        shipment.pickup_location_id = pickup["id"] or None
        shipment.pickup_location = pickup["name"] or None
        db.session.commit()

        existing = cls._find_existing_order(shipment.shiprocket_reference_id)
        if cls._apply_reconciled_order(shipment, existing):
            return

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
        response = cls._request(
            "POST",
            "/courier/assign/awb",
            json_body={"shipment_id": int(shipment.shiprocket_shipment_id)},
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
        for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
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
            if order.status not in {OrderStatus.CANCELLED, OrderStatus.RETURNED}:
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
            # Clipcart has one delivery record per customer order, while Shiprocket
            # may hold one shipment per supplier. Final delivery is therefore only
            # safe when every supplier shipment has reached DELIVERED and the
            # existing Clipcart proof-photo requirement is satisfied.
            all_shipments = Shipment.query.filter_by(order_id=order.id).all()
            all_delivered = bool(all_shipments) and all(
                (row.status or "").upper() == "DELIVERED" for row in all_shipments
            )
            if all_delivered and assignment.proof_of_delivery_image_url:
                assignment.delivery_status = DeliveryStatus.DELIVERED
                assignment.delivery_time = (
                    assignment.delivery_time
                    or shipment.delivered_at
                    or datetime.utcnow()
                )
                order.status = OrderStatus.DELIVERED
                assignment.next_action = None
            elif all_delivered:
                assignment.delivery_status = DeliveryStatus.OUT_FOR_DELIVERY
                assignment.next_action = "Upload completion photo to finalize delivery"
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

        items = [
            item
            for item in order.items
            if item.product and item.product.seller_id == shipment.supplier_id
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
        if not shipment.pickup_scheduled_at:
            cls._request_pickup(shipment)
        if shipment.status != "MANIFEST GENERATED":
            cls._generate_manifest(shipment)
        return shipment

    @classmethod
    def ensure_order_shipments(cls, order_id, *, propagate=False):
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

        supplier_ids = sorted(
            {
                item.product.seller_id
                for item in order.items
                if item.product and item.product.seller_id
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
            try:
                # Failed pre-provision records may have the legacy reference format.
                # Re-key only records that never reached Shiprocket so a retry uses the
                # numeric reference expected by the current API contract.
                if (
                    not shipment.shiprocket_order_id
                    and shipment.shiprocket_reference_id != reference
                ):
                    shipment.shiprocket_reference_id = reference
                    db.session.commit()
                cls._provision_shipment(shipment)
            except ShiprocketError as exc:
                shipment.status = "FAILED"
                shipment.failure_code = exc.code or "SHIPROCKET_ERROR"
                shipment.failure_message = str(exc)[:1000]
                shipment.last_synced_at = datetime.utcnow()
                db.session.commit()
                if propagate:
                    raise
            except Exception as exc:
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
        return result

    @classmethod
    def track_shipment(cls, shipment):
        payload = None
        if shipment.awb_code:
            payload = cls._request("GET", f"/courier/track/awb/{shipment.awb_code}")
        elif shipment.shiprocket_shipment_id:
            payload = cls._request(
                "GET", f"/courier/track/shipment/{shipment.shiprocket_shipment_id}"
            )
        else:
            raise ShiprocketError(
                "Shipment has not been created in Shiprocket.",
                code="SHIPMENT_NOT_CREATED",
            )

        rows = payload.get("tracking_data") if isinstance(payload, dict) else None
        data = rows if isinstance(rows, dict) else payload
        if (
            isinstance(data, dict)
            and isinstance(data.get("shipment_track"), list)
            and data["shipment_track"]
        ):
            latest = data["shipment_track"][-1]
            merged = dict(data)
            if isinstance(latest, dict):
                merged.update(latest)
            data = merged
        cls._refresh_tracking_internal(shipment, data if isinstance(data, dict) else {})
        return shipment

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
        return cls._apply_external_status(shipment, payload, from_webhook=True)

    @classmethod
    def get_customer_shipments(cls, order):
        rows = sorted(
            list(getattr(order, "shipments", None) or []), key=lambda row: row.id
        )
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
            "delivered_at": shipment.delivered_at,
            "tracking_available": bool(
                shipment.awb_code or shipment.shiprocket_shipment_id
            ),
            "tracking_reference": shipment.awb_code,
        }
        if include_supplier:
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
