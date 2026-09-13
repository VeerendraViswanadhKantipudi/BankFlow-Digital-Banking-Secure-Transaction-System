"""
Domain Exceptions for BankFlow.
The service layer raises domain exceptions only, keeping it independent of HTTP/Flask.
"""

class BankFlowError(Exception):
    """Base domain exception for BankFlow."""
    def __init__(self, message="A banking system error occurred"):
        self.message = message
        super().__init__(self.message)


class TransferError(BankFlowError):
    """Base exception for all transfer engine errors."""
    pass


class InsufficientBalanceError(TransferError):
    """Raised when sender account has insufficient funds to execute the transfer."""
    pass


class AccountNotFoundError(TransferError):
    """Raised when one or both accounts participating in the transfer do not exist."""
    pass


class AccountInactiveError(TransferError):
    """Raised when an account is FROZEN, CLOSED, or not in ACTIVE status."""
    pass


class InvalidTransferError(TransferError):
    """Raised when transfer parameters are invalid (e.g. self-transfer, non-positive amount)."""
    pass


class IdempotencyKeyConflictError(TransferError):
    """Raised when an idempotency key is reused with different transaction parameters."""
    pass


class AuthenticationError(BankFlowError):
    """Raised on invalid credentials or authentication failures."""
    pass


class ResourceNotFoundError(BankFlowError):
    """Raised when a generic resource is not found or not accessible."""
    pass


class AccountError(BankFlowError):
    """General account domain exception."""
    pass


class ForbiddenError(BankFlowError):
    """Raised when an action is not authorized."""
    pass


class ValidationError(BankFlowError):
    """Raised when input validation fails."""
    pass
