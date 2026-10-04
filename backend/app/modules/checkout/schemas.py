from marshmallow import Schema, fields


class AddressSchema(Schema):
    address_id = fields.Int(required=True)


class CouponSchema(Schema):
    code = fields.Str(required=True)


class VerifyPaymentSchema(Schema):
    razorpay_order_id = fields.Str(required=True)
    razorpay_payment_id = fields.Str(required=True)
    razorpay_signature = fields.Str(required=True)