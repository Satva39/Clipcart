from marshmallow import Schema, fields


class ProductCreateSchema(Schema):
    category_id = fields.Int(required=True)
    brand_id = fields.Int(load_default=None, allow_none=True)
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    highlights = fields.List(fields.Str(), load_default=list)
    specifications = fields.Dict(load_default=dict)
    price = fields.Decimal(required=True, as_string=False)
    compare_price = fields.Decimal(load_default=None, allow_none=True, as_string=False)
    stock = fields.Int(required=True)
    low_stock_threshold = fields.Int(load_default=5)
    sku = fields.Str(required=True)
    status = fields.Str(load_default="ACTIVE")
    is_featured = fields.Bool(load_default=False)
