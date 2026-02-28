/**
 * useIssueDevObjects hook tests.
 *
 * Tests batch-fetching integration links and transforming into DevObjectStatus.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { IntegrationLink } from '@/types';

// ── Mocks ────────────────────────────────────────────────────────────────

const mockGetIssueLinks = vi.fn();

vi.mock('@/services/api/integrations', () => ({
  integrationsApi: {
    getIssueLinks: (_workspaceId: string, _issueId: string) =>
      mockGetIssueLinks(_workspaceId, _issueId),
  },
}));

// ── Import after mocks ──────────────────────────────────────────────────

import { useIssueDevObjects } from '../useIssueDevObjects';

// ── Helpers ─────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

const mockPRLink: IntegrationLink = {
  id: 'link-1',
  issueId: 'issue-1',
  integrationType: 'github_pr',
  externalId: '123',
  externalUrl: 'https://github.com/org/repo/pull/123',
  link_type: 'pull_request',
  prNumber: 123,
  prTitle: 'Fix login bug',
  prStatus: 'open',
};

const mockBranchLink: IntegrationLink = {
  id: 'link-2',
  issueId: 'issue-1',
  integrationType: 'github_issue',
  externalId: 'feat/login-fix',
  externalUrl: 'https://github.com/org/repo/tree/feat/login-fix',
  link_type: 'branch',
  title: 'feat/login-fix',
};

const mockCommitLink: IntegrationLink = {
  id: 'link-3',
  issueId: 'issue-1',
  integrationType: 'github_commit',
  externalId: 'abc123',
  externalUrl: 'https://github.com/org/repo/commit/abc123',
  link_type: 'commit',
  title: 'fix: resolve login redirect',
  // C1 fix: actual commit timestamp (not new Date()) must be present in fixture
  // so stale detection can compute days since last commit correctly.
  commitTimestamp: '2026-02-20T10:00:00.000Z',
};

// ── Tests ────────────────────────────────────────────────────────────────

describe('useIssueDevObjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty map when no issue IDs provided', () => {
    const { result } = renderHook(() => useIssueDevObjects({ workspaceId: 'ws-1', issueIds: [] }), {
      wrapper: createWrapper(),
    });

    expect(result.current.devObjects.size).toBe(0);
    expect(result.current.isLoading).toBe(false);
  });

  it('fetches and transforms links for each issue', async () => {
    mockGetIssueLinks.mockResolvedValue([mockPRLink, mockBranchLink, mockCommitLink]);

    const { result } = renderHook(
      () =>
        useIssueDevObjects({
          workspaceId: 'ws-1',
          issueIds: ['issue-1'],
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.devObjects.size).toBe(1);
    });

    const status = result.current.devObjects.get('issue-1');
    expect(status).toBeDefined();
    expect(status!.issueId).toBe('issue-1');
    expect(status!.branches).toHaveLength(1);
    expect(status!.branches[0]!.name).toBe('feat/login-fix');
    expect(status!.pullRequests).toHaveLength(1);
    expect(status!.pullRequests[0]!.number).toBe(123);
    expect(status!.pullRequests[0]!.state).toBe('open');
    expect(status!.hasActivity).toBe(true);
    // C1: latestCommitAt must reflect the actual commit timestamp, not Date.now()
    expect(status!.latestCommitAt).toBe('2026-02-20T10:00:00.000Z');
  });

  it('handles empty links for an issue', async () => {
    mockGetIssueLinks.mockResolvedValue([]);

    const { result } = renderHook(
      () =>
        useIssueDevObjects({
          workspaceId: 'ws-1',
          issueIds: ['issue-1'],
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.devObjects.size).toBe(1);
    });

    const status = result.current.devObjects.get('issue-1');
    expect(status!.hasActivity).toBe(false);
    expect(status!.branches).toHaveLength(0);
    expect(status!.pullRequests).toHaveLength(0);
  });

  it('does not fetch when disabled', () => {
    renderHook(
      () =>
        useIssueDevObjects({
          workspaceId: 'ws-1',
          issueIds: ['issue-1'],
          enabled: false,
        }),
      { wrapper: createWrapper() }
    );

    expect(mockGetIssueLinks).not.toHaveBeenCalled();
  });

  it('does not fetch when workspaceId is empty', () => {
    renderHook(
      () =>
        useIssueDevObjects({
          workspaceId: '',
          issueIds: ['issue-1'],
        }),
      { wrapper: createWrapper() }
    );

    expect(mockGetIssueLinks).not.toHaveBeenCalled();
  });

  it('handles multiple issues in parallel', async () => {
    mockGetIssueLinks.mockResolvedValueOnce([mockPRLink]).mockResolvedValueOnce([mockBranchLink]);

    const { result } = renderHook(
      () =>
        useIssueDevObjects({
          workspaceId: 'ws-1',
          issueIds: ['issue-1', 'issue-2'],
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.devObjects.size).toBe(2);
    });

    expect(result.current.devObjects.get('issue-1')!.pullRequests).toHaveLength(1);
    expect(result.current.devObjects.get('issue-2')!.branches).toHaveLength(1);
  });
});
