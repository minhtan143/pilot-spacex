/**
 * useStaleIssueDetection — Detect stale in-progress issues.
 *
 * Cross-references active issues with DevObjectStatus to find issues
 * where the latest commit is older than the threshold.
 * No API calls — pure derived computation.
 */

import { useMemo } from 'react';
import { getIssueStateKey } from '@/lib/issue-helpers';
import { STALE_THRESHOLD_DAYS } from '../constants';
import type { Issue } from '@/types';
import type { DevObjectStatus, StaleIssueInfo } from '../types';

export interface UseStaleIssueDetectionOptions {
  activeIssues: Issue[];
  devObjects: Map<string, DevObjectStatus>;
  thresholdDays?: number;
}

/**
 * Pure function: compute stale issues given a reference timestamp.
 */
export function detectStaleIssues(
  activeIssues: Issue[],
  devObjects: Map<string, DevObjectStatus>,
  thresholdDays: number,
  nowMs: number
): StaleIssueInfo[] {
  const stale: StaleIssueInfo[] = [];
  const thresholdMs = thresholdDays * 24 * 60 * 60 * 1000;

  for (const issue of activeIssues) {
    const stateKey = getIssueStateKey(issue.state);
    if (stateKey !== 'in_progress') continue;

    const devObj = devObjects.get(issue.id);

    if (!devObj || !devObj.latestCommitAt) {
      if (devObj?.hasActivity) {
        stale.push({
          issueId: issue.id,
          identifier: issue.identifier,
          title: issue.name,
          daysSinceLastCommit: thresholdDays + 1,
        });
      }
      continue;
    }

    const commitTime = new Date(devObj.latestCommitAt).getTime();
    const elapsed = nowMs - commitTime;
    // Guard against clock skew: future commit timestamps produce negative elapsed.
    // A negative daysSince would invert stale logic; clamp to 0 (not stale).
    const daysSince = Math.max(0, Math.floor(elapsed / (24 * 60 * 60 * 1000)));

    if (elapsed >= thresholdMs) {
      stale.push({
        issueId: issue.id,
        identifier: issue.identifier,
        title: issue.name,
        daysSinceLastCommit: daysSince,
      });
    }
  }

  return stale;
}

export function useStaleIssueDetection({
  activeIssues,
  devObjects,
  thresholdDays = STALE_THRESHOLD_DAYS,
}: UseStaleIssueDetectionOptions): StaleIssueInfo[] {
  // Capture render-time timestamp outside useMemo so the callback remains pure.

  const nowMs = Date.now();
  return useMemo(
    () => detectStaleIssues(activeIssues, devObjects, thresholdDays, nowMs),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- nowMs excluded: stale timing is per-render, not per-data-change
    [activeIssues, devObjects, thresholdDays]
  );
}
