/**
 * IssueDetailSheet component tests.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
}));

vi.mock('@/lib/issue-helpers', () => ({
  getIssueStateKey: (state: { group?: string } | undefined) => state?.group ?? 'backlog',
}));

vi.mock('@/components/ui/sheet', () => ({
  Sheet: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? React.createElement('div', { 'data-testid': 'sheet' }, children) : null,
  SheetContent: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'sheet-content' }, children),
  SheetHeader: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', null, children),
  SheetTitle: ({ children }: { children: React.ReactNode }) =>
    React.createElement('h2', null, children),
  SheetDescription: ({ children, ...props }: { children: React.ReactNode }) =>
    React.createElement('p', props, children),
  SheetFooter: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', null, children),
}));

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: { children: React.ReactNode }) =>
    React.createElement('span', { 'data-testid': 'badge' }, children),
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: { children: React.ReactNode }) =>
    React.createElement('button', props, children),
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) =>
    React.createElement('a', { href }, children),
}));

const mockIssue = {
  id: 'issue-1',
  identifier: 'PS-42',
  name: 'Fix login redirect bug',
  state: { name: 'In Progress', color: '#f59e0b', group: 'in_progress' },
  priority: 'high',
  assignee: { id: 'user-1', email: 'tin@example.com', displayName: 'Tin Dang' },
  cycleId: 'cycle-1',
};

const mockUseQuery = vi.fn();
vi.mock('@tanstack/react-query', () => ({
  useQuery: (opts: unknown) => mockUseQuery(opts),
}));

const mockUseIssueLinks = vi.fn();
vi.mock('@/features/issues/hooks/use-issue-links', () => ({
  useIssueLinks: (...args: unknown[]) => mockUseIssueLinks(...args),
}));

vi.mock('@/features/issues/components/linked-prs-list', () => ({
  LinkedPRsList: ({ links }: { links: unknown[] }) =>
    React.createElement('div', { 'data-testid': 'linked-prs' }, `${links.length} PRs`),
}));

vi.mock('@/services/api/issues', () => ({
  issuesApi: { get: vi.fn() },
}));

// BriefEntries imports RootStore → AuthStore → supabase.ts which needs env vars
vi.mock('@/stores/RootStore', () => ({
  useOnboardingStore: () => ({ openModal: vi.fn() }),
}));

vi.mock('@/features/onboarding/hooks/useOnboardingState', () => ({
  useOnboardingState: () => ({ data: null }),
  selectCompletionPercentage: () => 0,
}));

// ── Import after mocks ──────────────────────────────────────────────────

import { IssueDetailSheet } from '../IssueDetailSheet';

// ── Tests ────────────────────────────────────────────────────────────────

describe('IssueDetailSheet', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuery.mockReturnValue({ data: mockIssue, isLoading: false });
    mockUseIssueLinks.mockReturnValue({ pullRequests: [], isLoading: false });
  });

  it('does not render when issueId is null', () => {
    const { container } = render(
      <IssueDetailSheet
        issueId={null}
        workspaceId="ws-1"
        workspaceSlug="test-ws"
        onClose={vi.fn()}
      />
    );
    expect(container.querySelector('[data-testid="sheet"]')).not.toBeInTheDocument();
  });

  it('renders issue identifier and title', () => {
    render(
      <IssueDetailSheet
        issueId="issue-1"
        workspaceId="ws-1"
        workspaceSlug="test-ws"
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('PS-42')).toBeInTheDocument();
    expect(screen.getByText('Fix login redirect bug')).toBeInTheDocument();
  });

  it('renders state badge', () => {
    render(
      <IssueDetailSheet
        issueId="issue-1"
        workspaceId="ws-1"
        workspaceSlug="test-ws"
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('renders priority badge', () => {
    render(
      <IssueDetailSheet
        issueId="issue-1"
        workspaceId="ws-1"
        workspaceSlug="test-ws"
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('high')).toBeInTheDocument();
  });

  it('renders assignee name', () => {
    render(
      <IssueDetailSheet
        issueId="issue-1"
        workspaceId="ws-1"
        workspaceSlug="test-ws"
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText('Tin Dang')).toBeInTheDocument();
  });

  it('renders LinkedPRsList', () => {
    mockUseIssueLinks.mockReturnValue({
      pullRequests: [{ id: 'pr-1' }],
      isLoading: false,
    });

    render(
      <IssueDetailSheet
        issueId="issue-1"
        workspaceId="ws-1"
        workspaceSlug="test-ws"
        onClose={vi.fn()}
      />
    );
    expect(screen.getByTestId('linked-prs')).toBeInTheDocument();
  });

  it('renders "Open full page" link with correct href', () => {
    render(
      <IssueDetailSheet
        issueId="issue-1"
        workspaceId="ws-1"
        workspaceSlug="test-ws"
        onClose={vi.fn()}
      />
    );
    const link = screen.getByText('Open full page').closest('a');
    expect(link).toHaveAttribute('href', '/test-ws/issues/issue-1');
  });

  it('shows loading state', () => {
    mockUseQuery.mockReturnValue({ data: undefined, isLoading: true });

    const { container } = render(
      <IssueDetailSheet
        issueId="issue-1"
        workspaceId="ws-1"
        workspaceSlug="test-ws"
        onClose={vi.fn()}
      />
    );
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });
});
