from marshmallow import Schema, fields


class ProductWizardSchema(Schema):
    category_id = fields.Int(required=True)
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    brand = fields.Str(load_default=None)
    price = fields.Decimal(required=True)
    compare_price = fields.Decimal(load_default=None)
    sku = fields.Str(required=True)
    stock = fields.Int(required=True)

    images = fields.List(
        fields.Dict(),
        required=False,
    )

    variants = fields.List(
        fields.Dict(),
        required=False,
    )