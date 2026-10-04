from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    full_name = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=150),
    )

    email = fields.Email(
        required=True,
    )

    password = fields.Str(
        required=True,
        validate=validate.Length(min=8),
    )


class LoginSchema(Schema):
    email = fields.Email(
        required=True,
    )

    password = fields.Str(
        required=True,
    )