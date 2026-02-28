/**
 * StaleLogicAlert component tests.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
}));

// ── Import after mocks ──────────────────────────────────────────────────

import { StaleLogicAlert } from '../StaleLogicAlert';
import type { StaleIssueInfo } from '../../types';

// ── Fixtures ────────────────────────────────────────────────────────────

const staleIssues: StaleIssueInfo[] = [
  { issueId: '1', identifier: 'PS-42', title: 'Fix login redirect', daysSinceLastCommit: 5 },
  { issueId: '2', identifier: 'PS-43', title: 'Update auth flow', daysSinceLastCommit: 7 },
];

// ── Tests ────────────────────────────────────────────────────────────────

describe('StaleLogicAlert', () => {
  it('returns null when no stale issues', () => {
    const { container } = render(<StaleLogicAlert staleIssues={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders alert with stale issue count', () => {
    render(<StaleLogicAlert staleIssues={staleIssues} />);
    expect(screen.getByText('2 stale issues')).toBeInTheDocument();
  });

  it('renders singular form for single stale issue', () => {
    render(<StaleLogicAlert staleIssues={[staleIssues[0]!]} />);
    expect(screen.getByText('1 stale issue')).toBeInTheDocument();
  });

  it('renders issue identifiers in monospace', () => {
    render(<StaleLogicAlert staleIssues={staleIssues} />);
    const identifier = screen.getByText('PS-42');
    expect(identifier.className).toContain('font-mono');
  });

  it('renders issue titles', () => {
    render(<StaleLogicAlert staleIssues={staleIssues} />);
    expect(screen.getByText('Fix login redirect')).toBeInTheDocument();
    expect(screen.getByText('Update auth flow')).toBeInTheDocument();
  });

  it('renders days since last commit', () => {
    render(<StaleLogicAlert staleIssues={staleIssues} />);
    expect(screen.getByText('5d')).toBeInTheDocument();
    expect(screen.getByText('7d')).toBeInTheDocument();
  });

  it('has role="alert" for accessibility', () => {
    render(<StaleLogicAlert staleIssues={staleIssues} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders threshold text', () => {
    render(<StaleLogicAlert staleIssues={staleIssues} />);
    expect(screen.getByText(/No commits in 3\+ days/)).toBeInTheDocument();
  });
});
