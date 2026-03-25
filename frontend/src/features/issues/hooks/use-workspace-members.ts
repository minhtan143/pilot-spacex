/**
 * useWorkspaceMembers - TanStack Query hook for workspace members.
 *
 * T013b: Fetches members via apiClient directly (no dedicated API service).
 */

import { apiClient } from '@/services/api';
import { useQuery } from '@tanstack/react-query';

export interface WorkspaceMember {
  userId: string;
  email: string;
  fullName: string | null;
  avatarUrl: string | null;
  role: 'owner' | 'admin' | 'member' | 'guest';
  joinedAt: string;
  /** Hours available per week for capacity planning (0-168, T-246) */
  weeklyAvailableHours: number;
  /** Custom role assigned by RBAC (01-03). When set, overrides built-in role display. */
  custom_role?: { id: string; name: string } | null;
  /** Whether the member is active. Deprovisioned (SCIM) members have is_active=false. */
  is_active?: boolean;
  /** Project chips — projects this member is assigned to (FR-02). */
  projects?: Array<{ id: string; name: string; identifier: string }>;
}

export const workspaceMembersKeys = {
  all: (workspaceId: string) => ['workspaces', workspaceId, 'members'] as const,
  filtered: (workspaceId: string, projectId: string | null) =>
    ['workspaces', workspaceId, 'members', { projectId }] as const,
};

interface UseWorkspaceMembersOptions {
  projectId?: string | null;
}

export function useWorkspaceMembers(workspaceId: string, options?: UseWorkspaceMembersOptions) {
  const projectId = options?.projectId ?? null;
  return useQuery<WorkspaceMember[]>({
    queryKey: projectId
      ? workspaceMembersKeys.filtered(workspaceId, projectId)
      : workspaceMembersKeys.all(workspaceId),
    queryFn: async () => {
      const params = projectId ? `?project_id=${projectId}` : '';
      const members = await apiClient.get<WorkspaceMember[]>(
        `/workspaces/${workspaceId}/members${params}`
      );
      return members.map((m) => ({
        ...m,
        role: m.role.toLowerCase() as WorkspaceMember['role'],
      }));
    },
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}
