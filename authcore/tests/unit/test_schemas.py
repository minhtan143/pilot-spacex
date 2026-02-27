"""Unit tests for Pydantic v2 request/response schemas."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from authcore.api.v1.schemas.admin import (
    AuditLogResponse,
    ChangeRoleRequest,
    ChangeRoleResponse,
    ListAuditLogsResponse,
)
from authcore.api.v1.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    VerifyEmailResponse,
)


class TestAuthRequestSchemas:
    def test_register_request_valid(self) -> None:
        r = RegisterRequest(email="user@example.com", password="Secure123!")
        assert r.email == "user@example.com"
        assert r.password == "Secure123!"

    def test_register_request_password_too_short(self) -> None:
        with pytest.raises(Exception):
            RegisterRequest(email="user@example.com", password="short")

    def test_login_request(self) -> None:
        r = LoginRequest(email="user@example.com", password="any")
        assert r.email == "user@example.com"

    def test_refresh_request(self) -> None:
        r = RefreshRequest(refresh_token="raw-token")
        assert r.refresh_token == "raw-token"

    def test_change_password_request(self) -> None:
        r = ChangePasswordRequest(current_password="old", new_password="NewPass123!")
        assert r.current_password == "old"

    def test_forgot_password_request(self) -> None:
        r = ForgotPasswordRequest(email="user@example.com")
        assert r.email == "user@example.com"

    def test_reset_password_request(self) -> None:
        r = ResetPasswordRequest(token="tok", new_password="NewPass123!")
        assert r.token == "tok"

    def test_resend_verification_request(self) -> None:
        r = ResendVerificationRequest()
        assert r is not None


class TestAuthResponseSchemas:
    def test_register_response(self) -> None:
        uid = uuid.uuid4()
        r = RegisterResponse(user_id=uid, email="x@x.com", verification_sent=True)
        assert r.user_id == uid
        assert r.verification_sent is True

    def test_login_response(self) -> None:
        uid = uuid.uuid4()
        r = LoginResponse(
            access_token="access",
            refresh_token="refresh",
            token_type="bearer",
            user_id=uid,
            role="member",
        )
        assert r.token_type == "bearer"

    def test_refresh_response(self) -> None:
        uid = uuid.uuid4()
        r = RefreshResponse(
            access_token="a", refresh_token="r", token_type="bearer", user_id=uid
        )
        assert r.access_token == "a"

    def test_message_response(self) -> None:
        r = MessageResponse(message="ok")
        assert r.message == "ok"

    def test_verify_email_response(self) -> None:
        uid = uuid.uuid4()
        r = VerifyEmailResponse(user_id=uid, email="x@x.com")
        assert r.user_id == uid


class TestAdminSchemas:
    def test_change_role_request(self) -> None:
        r = ChangeRoleRequest(new_role="admin")
        assert r.new_role == "admin"

    def test_change_role_response(self) -> None:
        uid = uuid.uuid4()
        r = ChangeRoleResponse(user_id=uid, new_role="guest")
        assert r.new_role == "guest"

    def test_audit_log_response(self) -> None:
        uid = uuid.uuid4()
        log_id = uuid.uuid4()
        now = datetime.now(tz=UTC)
        r = AuditLogResponse(
            id=log_id,
            action="LOGIN",
            created_at=now,
            user_id=uid,
            metadata={},
            ip_address="1.2.3.4",
        )
        assert r.action == "LOGIN"

    def test_audit_log_response_nullable_fields(self) -> None:
        r = AuditLogResponse(
            id=uuid.uuid4(),
            action="REGISTER",
            created_at=datetime.now(tz=UTC),
            user_id=None,
            metadata={"key": "val"},
            ip_address=None,
        )
        assert r.user_id is None
        assert r.ip_address is None

    def test_list_audit_logs_response(self) -> None:
        r = ListAuditLogsResponse(logs=[], total_returned=0)
        assert r.total_returned == 0
        assert r.logs == []
