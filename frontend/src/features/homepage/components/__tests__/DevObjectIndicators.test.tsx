/**
 * DevObjectIndicators component tests.
 *
 * Tests PR badges, branch chips, and empty states.
 */

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
}));

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', null, children),
  TooltipTrigger: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', null, children),
  TooltipContent: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { role: 'tooltip' }, children),
}));

// ── Import after mocks ──────────────────────────────────────────────────

import { DevObjectIndicators } from '../DevObjectIndicators';
import type { DevObjectStatus } from '../../types';

// ── Fixtures ────────────────────────────────────────────────────────────

const withPR: DevObjectStatus = {
  issueId: 'issue-1',
  branches: [{ name: 'feat/login-fix', lastPushAt: null, aheadBy: 2, behindBy: 0 }],
  pullRequests: [
    {
      number: 123,
      title: 'Fix login redirect bug',
      state: 'open',
      isDraft: false,
      reviewRequired: true,
      url: 'https://github.com/org/repo/pull/123',
    },
  ],
  latestCommitAt: '2026-02-28T10:00:00Z',
  hasActivity: true,
};

const mergedPR: DevObjectStatus = {
  issueId: 'issue-2',
  branches: [],
  pullRequests: [
    {
      number: 456,
      title: 'Merged PR',
      state: 'merged',
      isDraft: false,
      reviewRequired: false,
      url: 'https://github.com/org/repo/pull/456',
    },
  ],
  latestCommitAt: '2026-02-27T10:00:00Z',
  hasActivity: true,
};

const draftPR: DevObjectStatus = {
  issueId: 'issue-3',
  branches: [],
  pullRequests: [
    {
      number: 789,
      title: 'Draft PR',
      state: 'open',
      isDraft: true,
      reviewRequired: false,
      url: 'https://github.com/org/repo/pull/789',
    },
  ],
  latestCommitAt: null,
  hasActivity: true,
};

const branchOnly: DevObjectStatus = {
  issueId: 'issue-4',
  branches: [{ name: 'feat/new-feature', lastPushAt: null, aheadBy: 5, behindBy: 1 }],
  pullRequests: [],
  latestCommitAt: null,
  hasActivity: true,
};

const noActivity: DevObjectStatus = {
  issueId: 'issue-5',
  branches: [],
  pullRequests: [],
  latestCommitAt: null,
  hasActivity: false,
};

// ── Tests ────────────────────────────────────────────────────────────────

describe('DevObjectIndicators', () => {
  it('renders null when devObjects is undefined', () => {
    const { container } = render(<DevObjectIndicators devObjects={undefined} issueId="issue-1" />);
    expect(container.innerHTML).toBe('');
  });

  it('renders null when no branches or PRs', () => {
    const { container } = render(<DevObjectIndicators devObjects={noActivity} issueId="issue-5" />);
    expect(container.innerHTML).toBe('');
  });

  it('renders branch chip with name', () => {
    render(<DevObjectIndicators devObjects={branchOnly} issueId="issue-4" />);
    // Branch name appears in chip and tooltip
    expect(screen.getAllByText('feat/new-feature').length).toBeGreaterThanOrEqual(1);
  });

  it('renders PR chip with number', () => {
    render(<DevObjectIndicators devObjects={withPR} issueId="issue-1" />);
    expect(screen.getByText('#123')).toBeInTheDocument();
  });

  it('renders PR title in tooltip', () => {
    render(<DevObjectIndicators devObjects={withPR} issueId="issue-1" />);
    expect(screen.getAllByText('Fix login redirect bug').length).toBeGreaterThanOrEqual(1);
  });

  it('renders merged PR badge', () => {
    render(<DevObjectIndicators devObjects={mergedPR} issueId="issue-2" />);
    expect(screen.getByText('#456')).toBeInTheDocument();
  });

  it('renders draft PR badge', () => {
    render(<DevObjectIndicators devObjects={draftPR} issueId="issue-3" />);
    expect(screen.getByText('#789')).toBeInTheDocument();
  });

  it('renders branch chip when dev objects have branches', () => {
    render(<DevObjectIndicators devObjects={withPR} issueId="issue-1" />);
    // Branch name should appear in the chip
    expect(screen.getAllByText('feat/login-fix').length).toBeGreaterThanOrEqual(1);
  });

  it('renders branch and PR together', () => {
    render(<DevObjectIndicators devObjects={withPR} issueId="issue-1" />);
    // Branch name appears in chip and tooltip
    expect(screen.getAllByText('feat/login-fix').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('#123')).toBeInTheDocument();
  });

  it('shows multiple PR count in tooltip', () => {
    const multiPR: DevObjectStatus = {
      ...withPR,
      pullRequests: [
        ...withPR.pullRequests,
        {
          number: 124,
          title: 'Second PR',
          state: 'open' as const,
          isDraft: false,
          reviewRequired: true,
          url: '',
        },
      ],
    };
    render(<DevObjectIndicators devObjects={multiPR} issueId="issue-1" />);
    expect(screen.getByText(/\+1 more/)).toBeInTheDocument();
  });
});
