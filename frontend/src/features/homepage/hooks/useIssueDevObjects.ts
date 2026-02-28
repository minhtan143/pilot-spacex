'use client';

/**
 * useIssueDevObjects — Batch-fetch integration links per issue for homepage display.
 *
 * Transforms raw IntegrationLink[] into DevObjectStatus map for compact
 * branch/PR indicators on issue rows.
 */

import { useMemo } from 'react';
import { useQueries } from '@tanstack/react-query';
import { integrationsApi } from '@/services/api/integrations';
import { DEV_OBJECT_STALE_TIME } from '../constants';
import type { IntegrationLink } from '@/types';
import type { DevObjectStatus, BranchStatusBrief, PRStatusBrief } from '../types';

export interface UseIssueDevObjectsOptions {
  workspaceId: string;
  issueIds: string[];
  enabled?: boolean;
}

export interface UseIssueDevObjectsResult {
  devObjects: Map<string, DevObjectStatus>;
  isLoading: boolean;
}

/** Transform raw integration links into a DevObjectStatus record */
function transformLinks(issueId: string, links: IntegrationLink[]): DevObjectStatus {
  const branches: BranchStatusBrief[] = [];
  const pullRequests: PRStatusBrief[] = [];
  let latestCommitAt: string | null = null;

  for (const link of links) {
    if (link.link_type === 'branch') {
      branches.push({
        name: link.title ?? link.externalId,
        lastPushAt: null,
        aheadBy: 0,
        behindBy: 0,
      });
    } else if (link.link_type === 'pull_request') {
      pullRequests.push({
        number: link.prNumber ?? 0,
        title: link.prTitle ?? link.externalId,
        state: link.prStatus ?? 'open',
        isDraft: false,
        reviewRequired: link.prStatus === 'open',
        url: link.externalUrl,
      });
    } else if (link.link_type === 'commit') {
      // C1 fix: read actual timestamp from link.commitTimestamp (mapped from
      // CommitLinkMetadata.timestamp in integrations API client).
      // Previously used new Date().toISOString() which always set "now", making
      // stale detection report every issue with commits as "active".
      const commitTs = link.commitTimestamp ?? null;
      // Track the most recent commit across all commit links for this issue.
      if (commitTs && (!latestCommitAt || commitTs > latestCommitAt)) {
        latestCommitAt = commitTs;
      }
    }
  }

  return {
    issueId,
    branches,
    pullRequests,
    latestCommitAt,
    hasActivity: links.length > 0,
  };
}

export function useIssueDevObjects({
  workspaceId,
  issueIds,
  enabled = true,
}: UseIssueDevObjectsOptions): UseIssueDevObjectsResult {
  const queries = useQueries({
    queries: issueIds.map((issueId) => ({
      queryKey: ['homepage', 'dev-objects', workspaceId, issueId],
      queryFn: () => integrationsApi.getIssueLinks(workspaceId, issueId),
      enabled: enabled && !!workspaceId && !!issueId,
      staleTime: DEV_OBJECT_STALE_TIME,
    })),
  });

  const isLoading = queries.some((q) => q.isLoading);

  // W5 fix: useQueries returns a new array reference every render even when data
  // is unchanged. Using `queries` directly as a dep causes the Map to be rebuilt
  // every render. Instead, derive a stable string from per-query dataUpdatedAt
  // timestamps — this only changes when actual data is refreshed.
  const dataVersion = queries.map((q) => q.dataUpdatedAt ?? 0).join(',');

  const devObjects = useMemo(() => {
    const map = new Map<string, DevObjectStatus>();
    for (let i = 0; i < issueIds.length; i++) {
      const issueId = issueIds[i]!;
      const data = queries[i]?.data;
      if (data) {
        map.set(issueId, transformLinks(issueId, data));
      }
    }
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- dataVersion is a stable proxy for queries data freshness; queries array ref excluded intentionally
  }, [issueIds, dataVersion]);

  return { devObjects, isLoading };
}
