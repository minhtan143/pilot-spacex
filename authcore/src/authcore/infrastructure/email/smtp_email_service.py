"""SMTP email delivery implementation using aiosmtplib."""

from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import structlog

logger = structlog.get_logger(__name__)


class SmtpEmailService:
    """SMTP email delivery using aiosmtplib. 10s timeout. No retry (caller wraps)."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_address: str,
        use_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_address = from_address
        self._use_tls = use_tls

    async def _send(self, to_email: str, subject: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from_address
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))
        await aiosmtplib.send(
            msg,
            hostname=self._host,
            port=self._port,
            username=self._username or None,
            password=self._password or None,
            use_tls=self._use_tls,
            timeout=10,
        )

    async def send_verification(self, to_email: str, token: str, base_url: str) -> None:
        """Send email verification link to user.

        Args:
            to_email: Recipient email address.
            token: Verification token to embed in the link.
            base_url: Application base URL for constructing the link.
        """
        link = f"{base_url}/verify-email?token={token}"
        await self._send(
            to_email,
            "Verify your email address",
            f"<p>Click the link to verify your email: <a href='{link}'>{link}</a></p>"
            f"<p>This link expires in 24 hours.</p>",
        )
        logger.info("verification_email_sent", to=to_email)

    async def send_password_reset(self, to_email: str, token: str, base_url: str) -> None:
        """Send password reset link to user.

        Args:
            to_email: Recipient email address.
            token: Password reset token to embed in the link.
            base_url: Application base URL for constructing the link.
        """
        link = f"{base_url}/reset-password?token={token}"
        await self._send(
            to_email,
            "Reset your password",
            f"<p>Click the link to reset your password: <a href='{link}'>{link}</a></p>"
            f"<p>This link expires in 1 hour.</p>",
        )
        logger.info("password_reset_email_sent", to=to_email)
