"""Pydantic v2 request/response schemas for auth endpoints."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


# ---- Requests ----


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ResendVerificationRequest(BaseModel):
    """Resend email verification — caller must be authenticated."""


# ---- Responses ----


class RegisterResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    verification_sent: bool


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: uuid.UUID
    role: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: uuid.UUID


class MessageResponse(BaseModel):
    """Generic success response."""

    message: str


class VerifyEmailResponse(BaseModel):
    user_id: uuid.UUID
    email: str
