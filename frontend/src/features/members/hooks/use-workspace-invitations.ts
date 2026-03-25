/**
 * useWorkspaceInvitations - TanStack Query hook for workspace invitations.
 *
 * T025: Fetches pending invitations and provides cancel mutation.
 * S008: Adds acceptInvitation API function and useAcceptInvitation hook.
 * Follows use-workspace-members.ts pattern.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

export interface WorkspaceInvitation {
  id: string;
  email: string;
  role: 'admin' | 'member' | 'guest';
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  invitedById: string;
  invitedByName: string | null;
  createdAt: string;
  expiresAt: string;
}

export interface AcceptInvitationResponse {
  workspace_id: string;
  workspace_slug: string;
  requires_profile_completion: boolean;
}

export const workspaceInvitationsKeys = {
  all: (workspaceId: string) => ['workspaces', workspaceId, 'invitations'] as const,
};

export function useWorkspaceInvitations(workspaceId: string, enabled = true) {
  return useQuery<WorkspaceInvitation[]>({
    queryKey: workspaceInvitationsKeys.all(workspaceId),
    queryFn: () => apiClient.get<WorkspaceInvitation[]>(`/workspaces/${workspaceId}/invitations`),
    enabled: !!workspaceId && enabled,
    staleTime: 60_000,
  });
}

export function useCancelInvitation(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (invitationId: string) =>
      apiClient.delete(`/workspaces/${workspaceId}/invitations/${invitationId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workspaceInvitationsKeys.all(workspaceId),
      });
    },
  });
}

/**
 * Accept a workspace invitation after Supabase magic-link authentication.
 * Called by the /auth/accept-invite page once the Supabase session is active.
 */
export async function acceptInvitation(
  invitationId: string,
): Promise<AcceptInvitationResponse> {
  return apiClient.post<AcceptInvitationResponse>(
    `/auth/workspace-invitations/${invitationId}/accept`,
  );
}

/**
 * useAcceptInvitation — mutation hook wrapping acceptInvitation().
 * On success, returns workspace_slug and requires_profile_completion flag.
 */
export function useAcceptInvitation() {
  return useMutation<AcceptInvitationResponse, Error, string>({
    mutationFn: acceptInvitation,
  });
}
