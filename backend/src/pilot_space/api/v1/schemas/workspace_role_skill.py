"""Pydantic v2 request/response schemas for workspace role skill endpoints.

Source: Phase 16, WRSKL-01..02
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pilot_space.application.services.role_skill.types import VALID_ROLE_TYPES


class GenerateWorkspaceSkillRequest(BaseModel):
    """Request body for generating a workspace role skill."""

    role_type: str = Field(description=f"SDLC role type; one of: {sorted(VALID_ROLE_TYPES)}")
    role_name: str = Field(description="Human-readable display name for the role")
    experience_description: str = Field(
        description="Natural language description of experience for AI generation"
    )


class WorkspaceRoleSkillResponse(BaseModel):
    """Response schema for a single workspace role skill."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    role_type: str
    role_name: str
    skill_content: str
    experience_description: str | None
    is_active: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class WorkspaceRoleSkillListResponse(BaseModel):
    """Response schema for a list of workspace role skills."""

    skills: list[WorkspaceRoleSkillResponse]


__all__ = [
    "GenerateWorkspaceSkillRequest",
    "WorkspaceRoleSkillListResponse",
    "WorkspaceRoleSkillResponse",
]
