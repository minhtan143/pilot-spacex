'use client';

/**
 * NoteContextBadge — Micro-badge showing project health for a note.
 *
 * Matches notes to projects via backend-assigned project or title substring.
 * Shows a compact health bar with completion ratio and teleport icon on hover.
 */

import { useMemo } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ActivityCardNote } from '../types';
import type { Project } from '@/types';

// ---------------------------------------------------------------------------
// Matching logic (exported for testing)
// ---------------------------------------------------------------------------

/**
 * Find the project that matches a note.
 * Priority: backend-assigned project > title substring match.
 */
export function findMatchingProject(note: ActivityCardNote, projects: Project[]): Project | null {
  // 1. Backend-assigned project takes priority
  if (note.project) {
    return projects.find((p) => p.id === note.project!.id) ?? null;
  }

  // 2. Title-based word-boundary matching (case-insensitive, min 5 chars).
  // W8 fix: plain substring match (e.g. "App") caused false positives on notes
  // like "Apply...", "Mapping..." etc. Word boundary ensures whole-word matches only.
  const title = note.title.toLowerCase();
  if (title.length < 3) return null;

  return (
    projects.find((p) => {
      const name = p.name.toLowerCase();
      if (name.length < 5) return false; // short names produce too many false positives
      // Escape regex metacharacters in project name before building pattern
      const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      return new RegExp(`\\b${escaped}\\b`).test(title);
    }) ?? null
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface NoteContextBadgeProps {
  note: ActivityCardNote;
  projects: Project[];
}

export function NoteContextBadge({ note, projects }: NoteContextBadgeProps) {
  const matchedProject = useMemo(() => findMatchingProject(note, projects), [note, projects]);

  if (!matchedProject) return null;

  const total = matchedProject.issueCount ?? 0;
  const done = matchedProject.completedIssueCount ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded bg-muted/50 px-1.5 py-0.5',
        'text-[10px] text-muted-foreground',
        'group-hover:bg-muted/80'
      )}
      title={`${matchedProject.name}: ${done}/${total} issues (${pct}%)`}
    >
      {/* Health bar */}
      <span className="relative h-1 w-6 overflow-hidden rounded-full bg-muted">
        <span
          className="absolute inset-y-0 left-0 rounded-full bg-primary"
          style={{ width: `${pct}%` }}
          aria-label={`${pct}% complete`}
        />
      </span>

      {/* Project name (truncated) */}
      <span className="max-w-[60px] truncate">{matchedProject.name}</span>

      {/* Teleport icon (visible on group hover) */}
      <ArrowUpRight
        className="h-2.5 w-2.5 shrink-0 opacity-0 group-hover:opacity-70 motion-safe:transition-opacity"
        aria-hidden="true"
      />
    </span>
  );
}
