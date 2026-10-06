from marshmallow import Schema, fields, validate


class CustomerAddressSchema(Schema):

    full_name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=150),
    )

    phone = fields.String(required=True, validate=validate.Length(min=10, max=20))

    address_line_1 = fields.String(required=True)

    address_line_2 = fields.String(
        load_default=""
    )

    landmark = fields.String(
        load_default=""
    )

    city = fields.String(required=True)

    state = fields.String(required=True)

    postal_code = fields.String(required=True)

    country = fields.String(
        load_default="India"
    )

    latitude = fields.Float(required=False, allow_none=True, validate=validate.Range(min=-90, max=90))
    longitude = fields.Float(required=False, allow_none=True, validate=validate.Range(min=-180, max=180))

    is_default = fields.Boolean(
        load_default=False
    )