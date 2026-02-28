/**
 * useMemberActivity — Paginated TanStack Query hook for member activity feed.
 */

'use client';

import { useInfiniteQuery } from '@tanstack/react-query';
import { membersApi } from '@/services/api/members';
import type { MemberActivityPage } from '../types';

const PAGE_SIZE = 20;

export const memberActivityKeys = {
  activity: (workspaceId: string, userId: string) =>
    ['members', 'activity', workspaceId, userId] as const,
};

export function useMemberActivity(workspaceId: string, userId: string) {
  return useInfiniteQuery<MemberActivityPage>({
    queryKey: memberActivityKeys.activity(workspaceId, userId),
    queryFn: ({ pageParam = 1 }) =>
      membersApi.getActivity(workspaceId, userId, pageParam as number, PAGE_SIZE),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      const totalFetched = lastPage.page * lastPage.pageSize;
      return totalFetched < lastPage.total ? lastPage.page + 1 : undefined;
    },
    enabled: !!workspaceId && !!userId,
    staleTime: 30_000,
  });
}
