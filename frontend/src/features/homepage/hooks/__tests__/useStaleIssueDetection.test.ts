/**
 * useStaleIssueDetection hook tests.
 *
 * Tests threshold logic, edge cases, and state filtering.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock('@/lib/issue-helpers', () => ({
  getIssueStateKey: (state: { group?: string } | undefined) => state?.group ?? 'backlog',
}));

// ── Import after mocks ──────────────────────────────────────────────────

import { useStaleIssueDetection } from '../useStaleIssueDetection';
import type { Issue } from '@/types';
import type { DevObjectStatus } from '../../types';

// ── Helpers ─────────────────────────────────────────────────────────────

function daysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

function makeIssue(id: string, group: string): Issue {
  return {
    id,
    identifier: `PS-${id}`,
    name: `Issue ${id}`,
    state: { name: group, color: '#000', group },
  } as unknown as Issue;
}

function makeDevObj(issueId: string, daysBack: number | null): DevObjectStatus {
  return {
    issueId,
    branches: [],
    pullRequests: [],
    latestCommitAt: daysBack !== null ? daysAgo(daysBack) : null,
    hasActivity: true,
  };
}

// ── Tests ────────────────────────────────────────────────────────────────

describe('useStaleIssueDetection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty array when no issues', () => {
    const { result } = renderHook(() =>
      useStaleIssueDetection({
        activeIssues: [],
        devObjects: new Map(),
      })
    );
    expect(result.current).toEqual([]);
  });

  it('flags in_progress issues with old commits', () => {
    const issues = [makeIssue('1', 'in_progress')];
    const devObjects = new Map([['1', makeDevObj('1', 5)]]);

    const { result } = renderHook(() =>
      useStaleIssueDetection({ activeIssues: issues, devObjects })
    );

    expect(result.current).toHaveLength(1);
    expect(result.current[0]!.issueId).toBe('1');
    expect(result.current[0]!.daysSinceLastCommit).toBe(5);
  });

  it('does not flag in_progress issues with recent commits', () => {
    const issues = [makeIssue('1', 'in_progress')];
    const devObjects = new Map([['1', makeDevObj('1', 1)]]);

    const { result } = renderHook(() =>
      useStaleIssueDetection({ activeIssues: issues, devObjects })
    );

    expect(result.current).toHaveLength(0);
  });

  it('ignores issues not in_progress', () => {
    const issues = [makeIssue('1', 'todo'), makeIssue('2', 'in_review'), makeIssue('3', 'done')];
    const devObjects = new Map([
      ['1', makeDevObj('1', 10)],
      ['2', makeDevObj('2', 10)],
      ['3', makeDevObj('3', 10)],
    ]);

    const { result } = renderHook(() =>
      useStaleIssueDetection({ activeIssues: issues, devObjects })
    );

    expect(result.current).toHaveLength(0);
  });

  it('respects custom threshold', () => {
    const issues = [makeIssue('1', 'in_progress')];
    const devObjects = new Map([['1', makeDevObj('1', 2)]]);

    const { result } = renderHook(() =>
      useStaleIssueDetection({
        activeIssues: issues,
        devObjects,
        thresholdDays: 1,
      })
    );

    expect(result.current).toHaveLength(1);
  });

  it('flags issues with activity but no commit timestamp', () => {
    const issues = [makeIssue('1', 'in_progress')];
    const devObj: DevObjectStatus = {
      issueId: '1',
      branches: [{ name: 'feat/x', lastPushAt: null, aheadBy: 0, behindBy: 0 }],
      pullRequests: [],
      latestCommitAt: null,
      hasActivity: true,
    };
    const devObjects = new Map([['1', devObj]]);

    const { result } = renderHook(() =>
      useStaleIssueDetection({ activeIssues: issues, devObjects })
    );

    expect(result.current).toHaveLength(1);
    expect(result.current[0]!.daysSinceLastCommit).toBeGreaterThan(3);
  });

  it('does not flag issues without any dev objects', () => {
    const issues = [makeIssue('1', 'in_progress')];
    const devObjects = new Map<string, DevObjectStatus>();

    const { result } = renderHook(() =>
      useStaleIssueDetection({ activeIssues: issues, devObjects })
    );

    expect(result.current).toHaveLength(0);
  });

  it('handles exact threshold boundary', () => {
    const issues = [makeIssue('1', 'in_progress')];
    const devObjects = new Map([['1', makeDevObj('1', 3)]]);

    const { result } = renderHook(() =>
      useStaleIssueDetection({ activeIssues: issues, devObjects })
    );

    // 3 days with default threshold of 3 → should flag
    expect(result.current).toHaveLength(1);
  });
});
