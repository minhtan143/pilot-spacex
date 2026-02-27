"""Pydantic v2 request/response schemas for admin endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


# ---- Requests ----


class ChangeRoleRequest(BaseModel):
    new_role: str


# ---- Responses ----


class ChangeRoleResponse(BaseModel):
    user_id: uuid.UUID
    new_role: str


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    action: str
    created_at: datetime
    user_id: uuid.UUID | None
    metadata: dict[str, object]
    ip_address: str | None


class ListAuditLogsResponse(BaseModel):
    logs: list[AuditLogResponse]
    total_returned: int
