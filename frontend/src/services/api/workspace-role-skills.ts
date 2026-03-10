/**
 * Workspace Role Skills API client.
 * Admin-only endpoints for workspace-level skill management.
 * Source: Phase 16, WRSKL-01..04
 *
 * NOTE: is_active is a one-way approval gate. There is no deactivate endpoint.
 * To revert an active skill, Remove it and Generate a new one.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { SDLCRoleType } from './role-skills';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WorkspaceRoleSkill {
  id: string;
  workspaceId: string;
  roleType: SDLCRoleType;
  roleName: string;
  skillContent: string;
  experienceDescription: string | null;
  /** One-way approval gate: false = Pending Review, true = Active. No deactivate endpoint. */
  isActive: boolean;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface WorkspaceRoleSkillsResponse {
  skills: WorkspaceRoleSkill[];
}

export interface GenerateWorkspaceSkillPayload {
  roleType: SDLCRoleType;
  roleName: string;
  experienceDescription: string;
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

export const workspaceRoleSkillsApi = {
  getWorkspaceSkills(workspaceId: string): Promise<WorkspaceRoleSkillsResponse> {
    return apiClient.get<WorkspaceRoleSkillsResponse>(
      `/workspaces/${workspaceId}/workspace-role-skills`
    );
  },

  generateWorkspaceSkill(
    workspaceId: string,
    payload: GenerateWorkspaceSkillPayload
  ): Promise<WorkspaceRoleSkill> {
    return apiClient.post<WorkspaceRoleSkill>(
      `/workspaces/${workspaceId}/workspace-role-skills`,
      payload
    );
  },

  activateWorkspaceSkill(workspaceId: string, skillId: string): Promise<WorkspaceRoleSkill> {
    return apiClient.post<WorkspaceRoleSkill>(
      `/workspaces/${workspaceId}/workspace-role-skills/${skillId}/activate`,
      {}
    );
  },

  deleteWorkspaceSkill(workspaceId: string, skillId: string): Promise<void> {
    return apiClient.delete(`/workspaces/${workspaceId}/workspace-role-skills/${skillId}`);
  },
};

// ---------------------------------------------------------------------------
// TanStack Query Hooks
// ---------------------------------------------------------------------------

export function useWorkspaceRoleSkills(workspaceId: string) {
  return useQuery({
    queryKey: ['workspace-role-skills', workspaceId],
    queryFn: () => workspaceRoleSkillsApi.getWorkspaceSkills(workspaceId),
    staleTime: 60_000,
    enabled: !!workspaceId,
  });
}

export function useGenerateWorkspaceSkill({ workspaceId }: { workspaceId: string }) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: GenerateWorkspaceSkillPayload) =>
      workspaceRoleSkillsApi.generateWorkspaceSkill(workspaceId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workspace-role-skills', workspaceId] }),
  });
}

export function useActivateWorkspaceSkill({ workspaceId }: { workspaceId: string }) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (skillId: string) =>
      workspaceRoleSkillsApi.activateWorkspaceSkill(workspaceId, skillId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workspace-role-skills', workspaceId] }),
  });
}

export function useDeleteWorkspaceSkill({ workspaceId }: { workspaceId: string }) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (skillId: string) =>
      workspaceRoleSkillsApi.deleteWorkspaceSkill(workspaceId, skillId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workspace-role-skills', workspaceId] }),
  });
}
