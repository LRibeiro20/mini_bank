from typing import Any, Dict, Optional

class BankException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

class InvalidRequestException(BankException):
    def __init__(self, message: str = "Invalid request"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)

class UnauthorizedException(BankException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401)

class ForbiddenException(BankException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)

class AccountNotFoundException(BankException):
    def __init__(self, message: str = "Account not found"):
        super().__init__(code="ACCOUNT_NOT_FOUND", message=message, status_code=404)

class InsufficientFundsException(BankException):
    def __init__(self, message: str = "Insufficient funds"):
        super().__init__(code="INSUFFICIENT_FUNDS", message=message, status_code=400)

class DuplicateRequestException(BankException):
    def __init__(self, message: str = "Duplicate request"):
        super().__init__(code="DUPLICATE_REQUEST", message=message, status_code=409)

class TransferNotFoundException(BankException):
    def __init__(self, message: str = "Transfer not found"):
        super().__init__(code="TRANSFER_NOT_FOUND", message=message, status_code=404)

class AccountBlockedException(BankException):
    def __init__(self, message: str = "Account is blocked"):
        super().__init__(code="ACCOUNT_BLOCKED", message=message, status_code=403)
