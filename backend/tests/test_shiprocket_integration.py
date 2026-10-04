import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from app.extensions import db
from app.modules.shiprocket.service import ShiprocketService


class ShiprocketResponseContractTests(unittest.TestCase):
    def setUp(self):
        self.shipment = SimpleNamespace(
            shiprocket_shipment_id=16090109,
            awb_code=None,
            courier_company_id=None,
            courier_name=None,
            awb_assigned_at=None,
            status="ORDER_CREATED",
            failure_code=None,
            failure_message=None,
            pickup_scheduled_at=None,
            last_synced_at=None,
        )

    @patch.object(db.session, "commit")
    @patch.object(
        ShiprocketService,
        "_request",
        return_value={
            "awb_assign_status": 1,
            "response": {
                "data": {
                    "courier_company_id": 142,
                    "awb_code": "321055706540",
                    "courier_name": "Amazon Surface",
                    "pickup_scheduled_date": "2022-11-25 14:00:00",
                }
            },
        },
    )
    def test_awb_response_is_read_from_nested_data(self, request, commit):
        ShiprocketService._assign_awb(self.shipment)
        self.assertEqual(self.shipment.awb_code, "321055706540")
        self.assertEqual(self.shipment.courier_company_id, 142)
        self.assertEqual(self.shipment.courier_name, "Amazon Surface")
        self.assertEqual(self.shipment.status, "AWB ASSIGNED")

    @patch.object(db.session, "commit")
    @patch.object(
        ShiprocketService,
        "_request",
        return_value={
            "pickup_status": 1,
            "response": {
                "pickup_scheduled_date": "2021-12-10 12:39:54",
                "status": 3,
            },
        },
    )
    def test_pickup_response_is_read_from_nested_response(self, request, commit):
        ShiprocketService._request_pickup(self.shipment)
        self.assertEqual(self.shipment.status, "PICKUP SCHEDULED")
        self.assertIsInstance(self.shipment.pickup_scheduled_at, datetime)

    @patch.object(
        ShiprocketService,
        "_request",
        return_value={
            "data": [
                {
                    "id": 16161616,
                    "channel_order_id": "1200000000004",
                    "status": "NEW",
                    "shipments": [
                        {
                            "id": 15151515,
                            "awb": "1091208940593",
                            "courier": "Amazon Surface",
                        }
                    ],
                }
            ]
        },
    )
    def test_external_order_reconciliation_uses_clipcart_reference(self, request):
        result = ShiprocketService._find_existing_order("1200000000004")
        self.assertEqual(result["order_id"], 16161616)
        self.assertEqual(result["shipment_id"], 15151515)
        self.assertEqual(result["awb"], "1091208940593")

    @patch.object(
        ShiprocketService,
        "_request",
        return_value={
            "data": {
                "shipping_address": [
                    {
                        "id": 1856901,
                        "pickup_location": "Casa Moderna",
                        "address": "1900 GF, Sector 45",
                        "city": "Ahmedabad",
                        "state": "Gujarat",
                        "pin_code": "380001",
                    }
                ]
            }
        },
    )
    @patch.object(
        ShiprocketService,
        "_supplier_address",
        return_value={
            "business_name": "Casa Moderna",
            "name": "Owner",
            "email": "owner@example.com",
            "phone": "9876543210",
            "address": "1900 GF, Sector 45",
            "address_2": "",
            "city": "Ahmedabad",
            "state": "Gujarat",
            "pin_code": "380001",
            "country": "India",
        },
    )
    def test_pickup_list_nested_under_data_shipping_address(
        self, supplier_address, request
    ):
        result = ShiprocketService._get_or_create_pickup(10)
        self.assertEqual(result["id"], "1856901")
        self.assertEqual(result["name"], "Casa Moderna")

    def test_numeric_supplier_reference(self):
        self.assertEqual(ShiprocketService._supplier_key(10, 15), "100000000015")


if __name__ == "__main__":
    unittest.main()
