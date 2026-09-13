from marshmallow import Schema, fields, validate, validates, ValidationError
from decimal import Decimal

class CreateAccountSchema(Schema):
    initial_deposit = fields.Decimal(as_string=True, load_default="0.00")

    @validates("initial_deposit")
    def validate_deposit(self, value, **kwargs):
        try:
            if Decimal(str(value)) < Decimal("0.00"):
                raise ValidationError("Initial deposit must be non-negative.")
        except (ValueError, TypeError):
            raise ValidationError("Invalid numeric value for initial deposit.")


class UpdateAccountStatusSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(["ACTIVE", "FROZEN", "CLOSED"]))


class UpdateUserRoleSchema(Schema):
    role = fields.Str(required=True, validate=validate.OneOf(["CUSTOMER", "ADMIN"]))


class DepositSchema(Schema):
    amount = fields.Decimal(as_string=True, required=True)

    @validates("amount")
    def validate_amount(self, value, **kwargs):
        try:
            if Decimal(str(value)) <= Decimal("0.00"):
                raise ValidationError("Deposit amount must be greater than zero.")
        except (ValueError, TypeError):
            raise ValidationError("Invalid numeric value for deposit amount.")
