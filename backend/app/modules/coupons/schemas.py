from marshmallow import Schema, fields, validate


class CouponCreateSchema(Schema):

    code = fields.String(required=True)

    discount_type = fields.String(
        required=True,
        validate=validate.OneOf(
            ["PERCENTAGE", "FIXED"]
        ),
    )

    discount_value = fields.Float(
        required=True,
    )

    minimum_order = fields.Float(
        load_default=0,
    )

    maximum_discount = fields.Float(
        allow_none=True,
        load_default=None,
    )

    usage_limit = fields.Integer(
        load_default=0,
    )

    expires_at = fields.DateTime(
        allow_none=True,
        load_default=None,
    )

    is_active = fields.Boolean(
        load_default=True,
    )