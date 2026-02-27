"""Domain exceptions for AuthCore.

Each exception maps directly to an HTTP status code and machine-readable error_code.
Used with RFC 7807 error handler in the API layer.
"""


class AuthCoreException(Exception):
    """Base exception for all AuthCore errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    title: str = "Internal Server Error"
    detail: str | None = None

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(self.title)


class EmailExistsError(AuthCoreException):
    status_code = 409
    error_code = "AUTH_EMAIL_EXISTS"
    title = "Email Already Registered"


class PasswordWeakError(AuthCoreException):
    status_code = 422
    error_code = "AUTH_PASSWORD_WEAK"
    title = "Password Too Weak"


class InvalidCredentialsError(AuthCoreException):
    status_code = 401
    error_code = "AUTH_INVALID_CREDENTIALS"
    title = "Invalid Credentials"


class EmailNotVerifiedError(AuthCoreException):
    status_code = 401
    error_code = "AUTH_EMAIL_NOT_VERIFIED"
    title = "Email Not Verified"


class AccountLockedError(AuthCoreException):
    status_code = 423
    error_code = "AUTH_ACCOUNT_LOCKED"
    title = "Account Locked"


class TokenInvalidError(AuthCoreException):
    status_code = 400
    error_code = "AUTH_TOKEN_INVALID"
    title = "Token Invalid"


class TokenExpiredError(AuthCoreException):
    status_code = 400
    error_code = "AUTH_TOKEN_EXPIRED"
    title = "Token Expired"


class TokenRevokedError(AuthCoreException):
    status_code = 401
    error_code = "AUTH_TOKEN_REVOKED"
    title = "Token Revoked"


class TokenFamilyRevokedError(AuthCoreException):
    status_code = 401
    error_code = "AUTH_TOKEN_FAMILY_REVOKED"
    title = "Session Compromised"


class AuthUnauthorizedError(AuthCoreException):
    status_code = 401
    error_code = "AUTH_UNAUTHORIZED"
    title = "Authentication Required"


class AuthForbiddenError(AuthCoreException):
    status_code = 403
    error_code = "AUTH_FORBIDDEN"
    title = "Insufficient Role"


class UserNotFoundError(AuthCoreException):
    status_code = 404
    error_code = "AUTH_USER_NOT_FOUND"
    title = "User Not Found"


class AlreadyVerifiedError(AuthCoreException):
    status_code = 400
    error_code = "AUTH_ALREADY_VERIFIED"
    title = "Already Verified"


class ResendRateLimitedError(AuthCoreException):
    status_code = 429
    error_code = "AUTH_RESEND_RATE_LIMITED"
    title = "Resend Limit Reached"


class LoginRateLimitedError(AuthCoreException):
    status_code = 429
    error_code = "AUTH_LOGIN_RATE_LIMITED"
    title = "Login Rate Limited"


class InvalidRoleError(AuthCoreException):
    status_code = 400
    error_code = "AUTH_INVALID_ROLE"
    title = "Invalid Role"


class PasswordMismatchError(AuthCoreException):
    status_code = 400
    error_code = "AUTH_PASSWORD_MISMATCH"
    title = "Current Password Wrong"


class ValidationError(AuthCoreException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    title = "Validation Failed"
