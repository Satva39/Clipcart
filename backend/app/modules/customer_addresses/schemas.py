from marshmallow import Schema, fields, validate


class CustomerAddressSchema(Schema):

    full_name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=150),
    )

    phone = fields.String(required=True)

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

    is_default = fields.Boolean(
        load_default=False
    )