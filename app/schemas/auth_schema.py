from marshmallow import Schema, fields, validate, validates, ValidationError, EXCLUDE
from decimal import Decimal

class RegisterSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    email = fields.Email(required=True, validate=validate.Length(max=120))
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    initial_deposit = fields.Decimal(as_string=True, load_default="0.00")

    @validates("initial_deposit")
    def validate_deposit(self, value, **kwargs):
        try:
            if Decimal(str(value)) < Decimal("0.00"):
                raise ValidationError("Initial deposit cannot be negative.")
        except (ValueError, TypeError):
            raise ValidationError("Invalid numeric value for initial deposit.")


class LoginSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    email = fields.Email(required=True)
    password = fields.Str(required=True)
