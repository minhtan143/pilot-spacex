'use client';

/**
 * StaleLogicAlert — Warning card listing stale in-progress issues.
 *
 * Displays a compact alert when issues have not had commits
 * for more than STALE_THRESHOLD_DAYS days.
 */

import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { STALE_THRESHOLD_DAYS } from '../constants';
import type { StaleIssueInfo } from '../types';

export interface StaleLogicAlertProps {
  staleIssues: StaleIssueInfo[];
  className?: string;
}

export function StaleLogicAlert({ staleIssues, className }: StaleLogicAlertProps) {
  if (staleIssues.length === 0) return null;

  return (
    <div
      className={cn(
        'rounded-lg border border-amber-200 bg-amber-50/50 px-3 py-2.5',
        'dark:border-amber-800/40 dark:bg-amber-950/20',
        className
      )}
      role="alert"
    >
      <div className="flex items-center gap-2 mb-1.5">
        <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-500" aria-hidden="true" />
        <span className="text-xs font-medium text-amber-700 dark:text-amber-400">
          {staleIssues.length} stale {staleIssues.length === 1 ? 'issue' : 'issues'}
        </span>
        <span className="text-[10px] text-amber-600/70 dark:text-amber-500/60">
          No commits in {STALE_THRESHOLD_DAYS}+ days
        </span>
      </div>

      <ul className="space-y-0.5" role="list" aria-label="Stale issues">
        {staleIssues.map((issue) => (
          <li key={issue.issueId} className="flex items-center gap-2 text-xs">
            <span className="shrink-0 font-mono text-amber-600 dark:text-amber-400">
              {issue.identifier}
            </span>
            <span className="min-w-0 flex-1 truncate text-foreground">{issue.title}</span>
            <span className="shrink-0 tabular-nums text-amber-600/70 dark:text-amber-500/60">
              {issue.daysSinceLastCommit}d
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
