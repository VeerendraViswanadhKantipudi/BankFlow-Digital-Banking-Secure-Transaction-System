from marshmallow import Schema, fields, validate, validates, ValidationError
from decimal import Decimal

class TransferRequestSchema(Schema):
    sender_account_id = fields.Int(required=True)
    receiver_account_id = fields.Int(required=True)
    amount = fields.Decimal(as_string=True, required=True)
    idempotency_key = fields.Str(required=False, allow_none=True, validate=validate.Length(max=128))

    @validates("amount")
    def validate_amount(self, value, **kwargs):
        if value <= Decimal("0.00"):
            raise ValidationError("Transfer amount must be strictly greater than zero.")


class TransactionFilterSchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=10, validate=validate.Range(min=1, max=100))
    status = fields.Str(required=False, validate=validate.OneOf(["PENDING", "COMPLETED", "FAILED"]))
    type = fields.Str(required=False, validate=validate.OneOf(["ALL", "SENT", "RECEIVED"]))
