"""Pure domain service for password complexity validation.

No I/O. No external dependencies.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordPolicyResult:
    """Result of password policy validation.

    Attributes:
        is_valid: True if the password passes all rules.
        failures: Human-readable messages for each failed rule.
    """

    is_valid: bool
    failures: tuple[str, ...]


class PasswordPolicy:
    """Validates password complexity rules.

    Rules:
    - Minimum 8 characters
    - Maximum 128 characters
    - At least one uppercase letter
    - At least one digit
    """

    MIN_LENGTH: int = 8
    MAX_LENGTH: int = 128

    def validate(self, password: str) -> PasswordPolicyResult:
        """Validate a password against all complexity rules.

        Args:
            password: Plaintext password to validate.

        Returns:
            PasswordPolicyResult with is_valid flag and any failure messages.
        """
        failures: list[str] = []
        if len(password) < self.MIN_LENGTH:
            failures.append(f"Password must be at least {self.MIN_LENGTH} characters")
        if len(password) > self.MAX_LENGTH:
            failures.append(f"Password must be at most {self.MAX_LENGTH} characters")
        if not re.search(r"[A-Z]", password):
            failures.append("Password must contain at least one uppercase letter")
        if not re.search(r"\d", password):
            failures.append("Password must contain at least one digit")
        return PasswordPolicyResult(is_valid=len(failures) == 0, failures=tuple(failures))
