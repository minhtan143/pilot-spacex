'use client';

/**
 * DevObjectIndicators — Inline chips showing branch/PR status for an issue.
 *
 * Renders compact badges for linked branches and pull requests.
 */

import { GitBranch, GitPullRequest } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { DevObjectStatus } from '../types';

// ---------------------------------------------------------------------------
// PR Status Config
// ---------------------------------------------------------------------------

const PR_STATUS_STYLES: Record<string, { label: string; className: string }> = {
  open: {
    label: 'Open',
    className: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  },
  merged: {
    label: 'Merged',
    className: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  },
  closed: {
    label: 'Closed',
    className: 'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400',
  },
};

const PR_DRAFT_STYLE = {
  label: 'Draft',
  className: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface DevObjectIndicatorsProps {
  devObjects: DevObjectStatus | undefined;
  issueId: string;
  isLoading?: boolean;
  className?: string;
}

export function DevObjectIndicators({
  devObjects,
  isLoading = false,
  className,
}: DevObjectIndicatorsProps) {
  if (isLoading) {
    return (
      <span className="flex items-center gap-1.5" aria-hidden="true">
        <span className="h-4 w-16 animate-pulse rounded bg-muted/30" />
      </span>
    );
  }

  if (!devObjects || (!devObjects.branches.length && !devObjects.pullRequests.length)) {
    return null;
  }

  const firstBranch = devObjects.branches[0];
  const firstPR = devObjects.pullRequests[0];

  return (
    <span className={cn('flex items-center gap-1.5', className)}>
      {/* Branch chip */}
      {firstBranch && (
        <Tooltip>
          <TooltipTrigger asChild>
            <span
              className={cn(
                'inline-flex items-center gap-0.5 rounded px-1 py-0.5',
                'bg-muted/60 text-[10px] font-mono text-muted-foreground',
                'max-w-[80px] truncate'
              )}
            >
              <GitBranch className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />
              <span className="truncate">{firstBranch.name}</span>
            </span>
          </TooltipTrigger>
          <TooltipContent side="top">
            <p className="text-xs">
              {devObjects.branches.length === 1
                ? firstBranch.name
                : `${devObjects.branches.length} branches`}
            </p>
          </TooltipContent>
        </Tooltip>
      )}

      {/* PR chip */}
      {firstPR && (
        <Tooltip>
          <TooltipTrigger asChild>
            <span
              className={cn(
                'inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                firstPR.isDraft
                  ? PR_DRAFT_STYLE.className
                  : (PR_STATUS_STYLES[firstPR.state]?.className ?? PR_STATUS_STYLES.open!.className)
              )}
            >
              <GitPullRequest className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />#
              {firstPR.number}
            </span>
          </TooltipTrigger>
          <TooltipContent side="top">
            <p className="text-xs">
              {firstPR.title}
              {devObjects.pullRequests.length > 1 &&
                ` (+${devObjects.pullRequests.length - 1} more)`}
            </p>
          </TooltipContent>
        </Tooltip>
      )}
    </span>
  );
}
