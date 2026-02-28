/**
 * useMemberIssueDigest — Fetches issues assigned to a member for the digest tab.
 *
 * Uses the existing issues API with assignee_id filter since no dedicated endpoint exists.
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';
import type { MemberIssueDigestItem } from '../types';

interface RawIssue {
  id: string;
  identifier: string;
  name: string;
  state: {
    group: string;
    name: string;
  };
  targetDate: string | null;
}

function toDigestState(issue: RawIssue): string {
  const group = issue.state?.group ?? 'unstarted';
  const targetDate = issue.targetDate;
  if (
    group !== 'completed' &&
    group !== 'cancelled' &&
    targetDate &&
    new Date(targetDate) < new Date()
  ) {
    return 'overdue';
  }
  if (group === 'completed') return 'done';
  if (group === 'started') {
    // Distinguish in_progress from in_review by state name
    const name = (issue.state?.name ?? '').toLowerCase();
    return name.includes('review') ? 'in_review' : 'in_progress';
  }
  return 'todo';
}

export const memberIssueDigestKeys = {
  digest: (workspaceId: string, userId: string) =>
    ['members', 'issue-digest', workspaceId, userId] as const,
};

export function useMemberIssueDigest(workspaceId: string, userId: string) {
  return useQuery<MemberIssueDigestItem[]>({
    queryKey: memberIssueDigestKeys.digest(workspaceId, userId),
    queryFn: async () => {
      const resp = await apiClient.get<{ items: RawIssue[] }>(
        `/workspaces/${workspaceId}/issues/`,
        { params: { assignee_id: userId, pageSize: 100 } }
      );
      return resp.items.map((issue) => ({
        id: issue.id,
        identifier: issue.identifier,
        title: issue.name,
        state: toDigestState(issue),
      }));
    },
    enabled: !!workspaceId && !!userId,
    staleTime: 60_000,
  });
}
