from marshmallow import Schema, fields, validate


class AssignAgentSchema(Schema):
    agent_name = fields.String(required=True, validate=validate.Length(min=2, max=150))
    agent_phone = fields.String(required=True, validate=validate.Length(min=6, max=30))


class DeliveryUpdateSchema(Schema):
    notes = fields.String(load_default="", validate=validate.Length(max=5000))
    customer_delivery_notes = fields.String(
        load_default="", validate=validate.Length(max=5000)
    )
    proof_of_delivery_reference = fields.String(
        load_default="", validate=validate.Length(max=500)
    )


class DeliveryNotesSchema(Schema):
    notes = fields.String(
        load_default="",
        validate=validate.Length(max=5000),
    )
    customer_delivery_notes = fields.String(
        load_default="",
        validate=validate.Length(max=5000),
    )
    proof_of_delivery_reference = fields.String(
        load_default="",
        validate=validate.Length(max=500),
    )


class DeliveryAttemptSchema(Schema):
    reason = fields.String(required=True, validate=validate.Length(min=3, max=1000))
    notes = fields.String(load_default="", validate=validate.Length(max=5000))


class FailedDeliverySchema(DeliveryAttemptSchema):
    next_action = fields.String(required=True, validate=validate.Length(min=2, max=255))
