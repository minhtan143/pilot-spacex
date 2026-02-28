/**
 * NoteContextBadge component tests.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
}));

// ── Import after mocks ──────────────────────────────────────────────────

import { NoteContextBadge, findMatchingProject } from '../NoteContextBadge';
import type { ActivityCardNote } from '../../types';
import type { Project } from '@/types';

// ── Fixtures ────────────────────────────────────────────────────────────

const mockProjects: Project[] = [
  { id: 'proj-1', name: 'Pilot Space', issueCount: 20, completedIssueCount: 15 } as Project,
  { id: 'proj-2', name: 'Other Project', issueCount: 10, completedIssueCount: 3 } as Project,
];

const noteWithProject: ActivityCardNote = {
  type: 'note',
  id: 'note-1',
  title: 'Sprint planning',
  project: { id: 'proj-1', name: 'Pilot Space', identifier: 'PS' },
  wordCount: 100,
  latestAnnotation: null,
  updatedAt: '2026-02-28T10:00:00Z',
  isPinned: false,
};

const noteMatchByTitle: ActivityCardNote = {
  type: 'note',
  id: 'note-2',
  title: 'Pilot Space sprint review notes',
  project: null,
  wordCount: 200,
  latestAnnotation: null,
  updatedAt: '2026-02-28T10:00:00Z',
  isPinned: false,
};

const noteNoMatch: ActivityCardNote = {
  type: 'note',
  id: 'note-3',
  title: 'Random thoughts',
  project: null,
  wordCount: 50,
  latestAnnotation: null,
  updatedAt: '2026-02-28T10:00:00Z',
  isPinned: false,
};

const noteShortTitle: ActivityCardNote = {
  type: 'note',
  id: 'note-4',
  title: 'Hi',
  project: null,
  wordCount: 10,
  latestAnnotation: null,
  updatedAt: '2026-02-28T10:00:00Z',
  isPinned: false,
};

// ── findMatchingProject unit tests ──────────────────────────────────────

describe('findMatchingProject', () => {
  it('returns backend-assigned project when present', () => {
    const result = findMatchingProject(noteWithProject, mockProjects);
    expect(result?.id).toBe('proj-1');
  });

  it('matches by title substring (case-insensitive)', () => {
    const result = findMatchingProject(noteMatchByTitle, mockProjects);
    expect(result?.id).toBe('proj-1');
  });

  it('returns null when no match', () => {
    const result = findMatchingProject(noteNoMatch, mockProjects);
    expect(result).toBeNull();
  });

  it('returns null for titles shorter than 3 chars', () => {
    const result = findMatchingProject(noteShortTitle, mockProjects);
    expect(result).toBeNull();
  });

  it('returns null when project list is empty', () => {
    const result = findMatchingProject(noteMatchByTitle, []);
    expect(result).toBeNull();
  });

  it('prefers backend-assigned over title match', () => {
    const note: ActivityCardNote = {
      ...noteMatchByTitle,
      project: { id: 'proj-2', name: 'Other Project', identifier: 'OP' },
    };
    const result = findMatchingProject(note, mockProjects);
    expect(result?.id).toBe('proj-2');
  });
});

// ── Component tests ─────────────────────────────────────────────────────

describe('NoteContextBadge', () => {
  it('returns null when no project matches', () => {
    const { container } = render(<NoteContextBadge note={noteNoMatch} projects={mockProjects} />);
    expect(container.innerHTML).toBe('');
  });

  it('shows badge for backend-assigned project', () => {
    render(<NoteContextBadge note={noteWithProject} projects={mockProjects} />);
    expect(screen.getByText('Pilot Space')).toBeInTheDocument();
  });

  it('shows badge for title-matched project', () => {
    render(<NoteContextBadge note={noteMatchByTitle} projects={mockProjects} />);
    expect(screen.getByText('Pilot Space')).toBeInTheDocument();
  });

  it('shows health bar with correct percentage', () => {
    render(<NoteContextBadge note={noteWithProject} projects={mockProjects} />);
    const healthBar = screen.getByLabelText('75% complete');
    expect(healthBar).toBeInTheDocument();
  });

  it('has teleport icon in DOM', () => {
    const { container } = render(
      <NoteContextBadge note={noteWithProject} projects={mockProjects} />
    );
    // ArrowUpRight SVG should be present (hidden by default, shown on hover)
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has title attribute with project info', () => {
    render(<NoteContextBadge note={noteWithProject} projects={mockProjects} />);
    const badge = screen.getByTitle(/Pilot Space: 15\/20 issues/);
    expect(badge).toBeInTheDocument();
  });
});
