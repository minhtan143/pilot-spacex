"""Abstract protocol for email delivery in AuthCore."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AbstractEmailService(Protocol):
    """Email service Protocol. Implementations: SMTP, test stub."""

    async def send_verification(self, to_email: str, token: str, base_url: str) -> None:
        """Send email verification link to user.

        Args:
            to_email: Recipient email address.
            token: Verification token to embed in the link.
            base_url: Application base URL for constructing the link.
        """
        ...

    async def send_password_reset(self, to_email: str, token: str, base_url: str) -> None:
        """Send password reset link to user.

        Args:
            to_email: Recipient email address.
            token: Password reset token to embed in the link.
            base_url: Application base URL for constructing the link.
        """
        ...
