"""Domain entity representing an audit log entry."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


def _empty_metadata() -> dict[str, object]:
    return {}


@dataclass
class AuditLogEntity:
    """Immutable domain entity for an audit log entry.

    Represents a single auth event. Created once, never updated.
    """

    id: uuid.UUID
    action: str
    created_at: datetime
    user_id: uuid.UUID | None = None
    metadata: dict[str, object] = field(default_factory=_empty_metadata)
    ip_address: str | None = None
