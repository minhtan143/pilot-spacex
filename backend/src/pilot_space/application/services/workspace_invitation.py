"""Workspace invitation management service.

Handles invitation operations following CQRS-lite pattern (DD-064):
- List workspace invitations
- Cancel invitation
- Accept invitation (magic-link flow)

Note: The invite_member operation is in WorkspaceService (maintains
existing API compatibility).

Source: FR-014, FR-015, FR-016, US3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.domain.exceptions import ConflictError, ForbiddenError, NotFoundError
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace_invitation import (
        WorkspaceInvitation,
    )
    from pilot_space.infrastructure.database.repositories.invitation_repository import (
        InvitationRepository,
    )
    from pilot_space.infrastructure.database.repositories.user_repository import (
        UserRepository,
    )
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

logger = get_logger(__name__)


# ===== Payloads & Results =====


@dataclass
class ListInvitationsPayload:
    """Payload for listing workspace invitations."""

    workspace_id: UUID
    requesting_user_id: UUID


@dataclass
class ListInvitationsResult:
    """Result of list_invitations operation."""

    invitations: list[WorkspaceInvitation]


@dataclass
class CancelInvitationPayload:
    """Payload for canceling invitation."""

    workspace_id: UUID
    invitation_id: UUID
    actor_id: UUID


@dataclass
class CancelInvitationResult:
    """Result of cancel_invitation operation."""

    invitation_id: UUID
    cancelled_at: datetime


@dataclass
class AcceptInvitationPayload:
    """Payload for accepting a workspace invitation via magic link."""

    invitation_id: UUID
    user_id: UUID


@dataclass
class AcceptInvitationResult:
    """Result of accept_invitation operation."""

    workspace_slug: str
    requires_profile_completion: bool


class WorkspaceInvitationService:
    """Service for workspace invitation operations.

    Follows CQRS-lite pattern per DD-064.
    """

    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        invitation_repo: InvitationRepository,
        user_repo: UserRepository | None = None,
    ) -> None:
        self.workspace_repo = workspace_repo
        self.invitation_repo = invitation_repo
        self.user_repo = user_repo

    async def list_invitations(
        self,
        payload: ListInvitationsPayload,
    ) -> ListInvitationsResult:
        """List invitations for a workspace.

        Requires admin or owner role.

        Args:
            payload: List invitations payload.

        Returns:
            List of invitations.

        Raises:
            ValueError: If workspace not found or user not admin.
        """
        # H-3 fix: use get_with_members to eagerly load members
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            msg = "Workspace not found"
            raise NotFoundError(msg)

        # Check admin/owner role
        current_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.requesting_user_id),
            None,
        )
        if not current_member or not current_member.is_admin:
            msg = "Admin role required"
            raise ForbiddenError(msg)

        invitations = await self.invitation_repo.get_by_workspace(payload.workspace_id)

        return ListInvitationsResult(invitations=list(invitations))

    async def cancel_invitation(
        self,
        payload: CancelInvitationPayload,
    ) -> CancelInvitationResult:
        """Cancel a pending invitation.

        Requires admin or owner role.

        Args:
            payload: Cancel invitation payload.

        Returns:
            Cancelled invitation info.

        Raises:
            ValueError: If not found, not authorized, or invitation processed.
        """
        # H-3 fix: use get_with_members to eagerly load members
        workspace = await self.workspace_repo.get_with_members(payload.workspace_id)
        if not workspace:
            msg = "Workspace not found"
            raise NotFoundError(msg)

        # Check admin/owner role
        current_member = next(
            (m for m in (workspace.members or []) if m.user_id == payload.actor_id),
            None,
        )
        if not current_member or not current_member.is_admin:
            msg = "Admin role required"
            raise ForbiddenError(msg)

        # Cancel invitation
        cancelled_invitation = await self.invitation_repo.cancel(payload.invitation_id)
        if cancelled_invitation is None:
            msg = "Invitation not found or already processed"
            raise NotFoundError(msg)

        # H-5 fix: verify invitation belongs to this workspace (cross-workspace security)
        if cancelled_invitation.workspace_id != payload.workspace_id:
            msg = "Invitation not found or already processed"
            raise NotFoundError(msg)

        logger.info(
            "Invitation cancelled",
            extra={
                "workspace_id": str(payload.workspace_id),
                "invitation_id": str(payload.invitation_id),
            },
        )

        return CancelInvitationResult(
            invitation_id=payload.invitation_id,
            cancelled_at=datetime.now(tz=UTC),
        )

    async def accept_invitation(
        self,
        payload: AcceptInvitationPayload,
    ) -> AcceptInvitationResult:
        """Accept a workspace invitation after Supabase magic-link authentication.

        Adds the authenticated user as a workspace member, marks the invitation
        accepted, and materializes any project assignments stored on the invitation.

        Args:
            payload: Accept invitation payload containing invitation_id and user_id.

        Returns:
            AcceptInvitationResult with workspace_slug and profile-completion flag.

        Raises:
            NotFoundError: If invitation is not found.
            ConflictError: If invitation is not in PENDING state.
        """
        invitation = await self.invitation_repo.get_by_id(payload.invitation_id)
        if invitation is None:
            msg = "Invitation not found"
            raise NotFoundError(msg)

        from pilot_space.infrastructure.database.models.workspace_invitation import (
            InvitationStatus,
        )

        if invitation.status != InvitationStatus.PENDING:
            msg = f"Invitation is {invitation.status.value}, cannot be accepted"
            raise ConflictError(msg)

        workspace_id = invitation.workspace_id

        # Set RLS context using the inviting admin so workspace_members INSERT passes policy
        if invitation.invited_by:
            from pilot_space.infrastructure.database.rls import set_rls_context

            session = self.workspace_repo.session
            await set_rls_context(session, invitation.invited_by)

        await self.workspace_repo.add_member(
            workspace_id=workspace_id,
            user_id=payload.user_id,
            role=invitation.role,
        )
        await self.invitation_repo.mark_accepted(payload.invitation_id)

        # Materialize stored project assignments
        if invitation.project_assignments:
            from pilot_space.application.services.project_member import (
                InviteAssignmentsPayload,
                ProjectMemberService,
            )
            from pilot_space.infrastructure.database.repositories.project_member import (
                ProjectMemberRepository,
            )

            pm_repo = ProjectMemberRepository(session=self.workspace_repo.session)
            pm_svc = ProjectMemberService(project_member_repository=pm_repo)
            await pm_svc.materialize_invite_assignments(
                InviteAssignmentsPayload(
                    workspace_id=workspace_id,
                    user_id=payload.user_id,
                    assigned_by=invitation.invited_by,
                    project_assignments=invitation.project_assignments,
                )
            )

        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if workspace is None:
            msg = "Workspace not found"
            raise NotFoundError(msg)

        # Determine if user needs to complete their profile (provide full_name)
        requires_profile_completion = False
        if self.user_repo is not None:
            user = await self.user_repo.get_by_id_scalar(payload.user_id)
            requires_profile_completion = user is not None and not user.full_name

        logger.info(
            "invitation_accepted",
            invitation_id=str(payload.invitation_id),
            user_id=str(payload.user_id),
            workspace_id=str(workspace_id),
        )

        return AcceptInvitationResult(
            workspace_slug=workspace.slug,
            requires_profile_completion=requires_profile_completion,
        )


__all__ = [
    "AcceptInvitationPayload",
    "AcceptInvitationResult",
    "CancelInvitationPayload",
    "CancelInvitationResult",
    "ListInvitationsPayload",
    "ListInvitationsResult",
    "WorkspaceInvitationService",
]
