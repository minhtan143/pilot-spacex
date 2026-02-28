/**
 * useMemberProfile — TanStack Query hook for member profile data.
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { membersApi } from '@/services/api/members';
import type { MemberProfile } from '../types';

export const memberProfileKeys = {
  profile: (workspaceId: string, userId: string) =>
    ['members', 'profile', workspaceId, userId] as const,
};

export function useMemberProfile(workspaceId: string, userId: string) {
  return useQuery<MemberProfile>({
    queryKey: memberProfileKeys.profile(workspaceId, userId),
    queryFn: () => membersApi.getProfile(workspaceId, userId),
    enabled: !!workspaceId && !!userId,
    staleTime: 60_000,
  });
}
