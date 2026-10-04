from marshmallow import Schema, fields

class SellerVerificationSchema(Schema):
    business_name = fields.Str(required=True)
    gst_number = fields.Str(load_default=None)