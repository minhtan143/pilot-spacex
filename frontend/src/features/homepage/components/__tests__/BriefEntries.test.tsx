/**
 * BriefEntries sub-component tests.
 *
 * Tests extracted components: SectionDivider, NoteEntry, IssueEntry,
 * ProjectEntry, NoteSkeleton, IssueSkeleton.
 */

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
}));

vi.mock('@/lib/format-utils', () => ({
  abbreviatedTimeAgo: (date: string) => {
    void date;
    return '2m';
  },
}));

vi.mock('@/lib/issue-helpers', () => ({
  getIssueStateKey: (state: { group?: string } | undefined) => state?.group ?? 'backlog',
}));

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children, ...props }: { children: React.ReactNode }) =>
    React.createElement('span', { 'data-testid': 'badge', ...props }, children),
}));

vi.mock('@/components/ui/progress', () => ({
  Progress: ({ value }: { value: number }) =>
    React.createElement('div', {
      'data-testid': 'progress',
      role: 'progressbar',
      'aria-valuenow': value,
    }),
}));

vi.mock('@/stores/RootStore', () => ({
  useOnboardingStore: () => ({ openModal: vi.fn() }),
}));

vi.mock('@/features/onboarding/hooks/useOnboardingState', () => ({
  useOnboardingState: () => ({ data: null }),
  selectCompletionPercentage: () => 0,
}));

// ── Import after mocks ──────────────────────────────────────────────────

import {
  SectionDivider,
  NoteEntry,
  IssueEntry,
  ProjectEntry,
  NoteSkeleton,
  IssueSkeleton,
  STATE_COLORS,
} from '../BriefEntries';
import type { ActivityCardNote } from '../../types';
import type { Issue, Project } from '@/types';

// ── Fixtures ────────────────────────────────────────────────────────────

const mockNote: ActivityCardNote = {
  type: 'note' as const,
  id: 'note-1',
  title: 'Sprint Planning Notes',
  project: { id: 'proj-1', name: 'Pilot Space', identifier: 'PS' },
  wordCount: 150,
  latestAnnotation: null,
  updatedAt: '2026-02-28T10:00:00Z',
  isPinned: true,
};

const mockIssue = {
  id: 'issue-1',
  identifier: 'PS-42',
  name: 'Fix login redirect bug',
  state: { name: 'In Progress', color: '#f59e0b', group: 'in_progress' },
  priority: 'high',
} as unknown as Issue;

const mockProject = {
  id: 'proj-1',
  name: 'Pilot Space',
  issueCount: 20,
  completedIssueCount: 15,
} as unknown as Project;

// ── Tests ────────────────────────────────────────────────────────────────

describe('SectionDivider', () => {
  it('renders an hr element', () => {
    const { container } = render(<SectionDivider />);
    expect(container.querySelector('hr')).toBeInTheDocument();
  });
});

describe('NoteEntry', () => {
  it('renders note title', () => {
    render(<NoteEntry note={mockNote} onClick={vi.fn()} isLast={false} />);
    expect(screen.getByText('Sprint Planning Notes')).toBeInTheDocument();
  });

  it('shows pinned indicator', () => {
    render(<NoteEntry note={mockNote} onClick={vi.fn()} isLast={false} />);
    expect(screen.getByLabelText('Pinned')).toBeInTheDocument();
  });

  it('shows project identifier badge', () => {
    render(<NoteEntry note={mockNote} onClick={vi.fn()} isLast={false} />);
    expect(screen.getByText('PS')).toBeInTheDocument();
  });

  it('shows time ago', () => {
    render(<NoteEntry note={mockNote} onClick={vi.fn()} isLast={false} />);
    expect(screen.getByText('2m')).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<NoteEntry note={mockNote} onClick={onClick} isLast={false} />);
    await user.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('renders "Untitled" for empty title', () => {
    const emptyNote = { ...mockNote, title: '' };
    render(<NoteEntry note={emptyNote} onClick={vi.fn()} isLast={false} />);
    expect(screen.getByText('Untitled')).toBeInTheDocument();
  });

  it('shows italic styling for empty notes', () => {
    const emptyNote = { ...mockNote, wordCount: 0 };
    render(<NoteEntry note={emptyNote} onClick={vi.fn()} isLast={false} />);
    const title = screen.getByText('Sprint Planning Notes');
    expect(title.className).toContain('italic');
  });

  it('renders optional badge prop', () => {
    const badge = React.createElement('span', { 'data-testid': 'custom-badge' }, 'badge');
    render(<NoteEntry note={mockNote} onClick={vi.fn()} isLast={false} badge={badge} />);
    expect(screen.getByTestId('custom-badge')).toBeInTheDocument();
  });
});

describe('IssueEntry', () => {
  it('renders issue identifier in monospace', () => {
    render(<IssueEntry issue={mockIssue} onClick={vi.fn()} />);
    const identifier = screen.getByText('PS-42');
    expect(identifier.className).toContain('font-mono');
  });

  it('renders issue name', () => {
    render(<IssueEntry issue={mockIssue} onClick={vi.fn()} />);
    expect(screen.getByText('Fix login redirect bug')).toBeInTheDocument();
  });

  it('renders state badge', () => {
    render(<IssueEntry issue={mockIssue} onClick={vi.fn()} />);
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<IssueEntry issue={mockIssue} onClick={onClick} />);
    await user.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('renders optional trailing content', () => {
    const trailing = React.createElement('span', { 'data-testid': 'trail' }, 'dev-obj');
    render(<IssueEntry issue={mockIssue} onClick={vi.fn()} trailing={trailing} />);
    expect(screen.getByTestId('trail')).toBeInTheDocument();
  });
});

describe('ProjectEntry', () => {
  it('renders project name', () => {
    render(<ProjectEntry project={mockProject} onClick={vi.fn()} />);
    expect(screen.getByText('Pilot Space')).toBeInTheDocument();
  });

  it('renders issue count (done/total)', () => {
    render(<ProjectEntry project={mockProject} onClick={vi.fn()} />);
    expect(screen.getByText('15/20')).toBeInTheDocument();
  });

  it('renders progress bar', () => {
    render(<ProjectEntry project={mockProject} onClick={vi.fn()} />);
    const progress = screen.getByTestId('progress');
    expect(progress).toHaveAttribute('aria-valuenow', '75');
  });

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<ProjectEntry project={mockProject} onClick={onClick} />);
    await user.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('handles zero issues gracefully', () => {
    const emptyProject = {
      ...mockProject,
      issueCount: 0,
      completedIssueCount: 0,
    } as unknown as Project;
    render(<ProjectEntry project={emptyProject} onClick={vi.fn()} />);
    expect(screen.getByText('0/0')).toBeInTheDocument();
    expect(screen.getByTestId('progress')).toHaveAttribute('aria-valuenow', '0');
  });
});

describe('NoteSkeleton', () => {
  it('renders 3 skeleton rows', () => {
    const { container } = render(<NoteSkeleton />);
    const rows = container.querySelectorAll('.motion-safe\\:animate-pulse');
    expect(rows.length).toBe(3);
  });
});

describe('IssueSkeleton', () => {
  it('renders 3 skeleton rows', () => {
    const { container } = render(<IssueSkeleton />);
    const rows = container.querySelectorAll('.motion-safe\\:animate-pulse');
    expect(rows.length).toBe(3);
  });
});

describe('STATE_COLORS', () => {
  it('has entries for all 6 issue states', () => {
    expect(Object.keys(STATE_COLORS)).toEqual([
      'backlog',
      'todo',
      'in_progress',
      'in_review',
      'done',
      'cancelled',
    ]);
  });

  it('each entry has dot and label properties', () => {
    for (const [, value] of Object.entries(STATE_COLORS)) {
      expect(value).toHaveProperty('dot');
      expect(value).toHaveProperty('label');
    }
  });
});
