"""Unit tests for SmtpEmailService with mocked aiosmtplib."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from authcore.infrastructure.email.smtp_email_service import SmtpEmailService


@pytest.fixture
def smtp_service() -> SmtpEmailService:
    return SmtpEmailService(
        host="localhost",
        port=587,
        username="user",
        password="pass",
        from_address="noreply@test.com",
        use_tls=True,
    )


class TestSmtpEmailService:
    async def test_send_verification_calls_aiosmtplib(
        self, smtp_service: SmtpEmailService
    ) -> None:
        with patch("authcore.infrastructure.email.smtp_email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await smtp_service.send_verification("user@example.com", "tok123", "http://localhost")
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["hostname"] == "localhost"
            assert call_kwargs["port"] == 587
            assert call_kwargs["use_tls"] is True

    async def test_send_verification_embeds_token_in_link(
        self, smtp_service: SmtpEmailService
    ) -> None:
        captured: list[str] = []

        async def fake_send(msg, **kwargs):  # type: ignore[no-untyped-def]
            captured.append(msg.get_payload(0).get_payload())

        with patch("authcore.infrastructure.email.smtp_email_service.aiosmtplib.send", side_effect=fake_send):
            await smtp_service.send_verification("user@example.com", "mytoken", "http://app")
            assert "mytoken" in captured[0]
            assert "http://app/verify-email" in captured[0]

    async def test_send_password_reset_embeds_token(
        self, smtp_service: SmtpEmailService
    ) -> None:
        captured: list[str] = []

        async def fake_send(msg, **kwargs):  # type: ignore[no-untyped-def]
            captured.append(msg.get_payload(0).get_payload())

        with patch("authcore.infrastructure.email.smtp_email_service.aiosmtplib.send", side_effect=fake_send):
            await smtp_service.send_password_reset("user@example.com", "resettoken", "http://app")
            assert "resettoken" in captured[0]
            assert "http://app/reset-password" in captured[0]

    async def test_send_no_credentials_passes_none(self) -> None:
        svc = SmtpEmailService(
            host="localhost",
            port=25,
            username="",
            password="",
            from_address="no@test.com",
            use_tls=False,
        )
        with patch("authcore.infrastructure.email.smtp_email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await svc.send_verification("u@x.com", "t", "http://x")
            call_kwargs = mock_send.call_args.kwargs
            # Empty username/password should be passed as None
            assert call_kwargs["username"] is None
            assert call_kwargs["password"] is None
