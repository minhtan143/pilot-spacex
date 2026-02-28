/**
 * Member profile API client.
 *
 * Provides typed access to member profile and activity endpoints.
 */

import { apiClient } from './client';
import type { MemberProfile, MemberActivityPage } from '@/features/members/types';

export const membersApi = {
  getProfile(workspaceId: string, userId: string): Promise<MemberProfile> {
    return apiClient.get<MemberProfile>(`/workspaces/${workspaceId}/members/${userId}`);
  },

  getActivity(
    workspaceId: string,
    userId: string,
    page = 1,
    pageSize = 20,
    typeFilter?: string
  ): Promise<MemberActivityPage> {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (typeFilter) params['type_filter'] = typeFilter;
    return apiClient.get<MemberActivityPage>(
      `/workspaces/${workspaceId}/members/${userId}/activity`,
      { params }
    );
  },
};
