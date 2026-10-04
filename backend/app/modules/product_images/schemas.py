from marshmallow import Schema, fields, validate


class ProductImageCreateSchema(Schema):

    product_id = fields.Integer(required=True)

    image_url = fields.String(required=True)

    public_id = fields.String(required=True)

    variant_id = fields.Integer(
        required=False,
        allow_none=True,
    )

    is_thumbnail = fields.Boolean(
        required=False,
    )


class ReorderImagesSchema(Schema):

    image_ids = fields.List(
        fields.Integer(),
        required=True,
        validate=validate.Length(min=1),
    )