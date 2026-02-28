/**
 * SDLCSuggestionCards component tests.
 */

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
}));

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children, ...props }: { children: React.ReactNode }) =>
    React.createElement('span', { 'data-testid': 'badge', ...props }, children),
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, ...props }: { children: React.ReactNode; onClick?: () => void }) =>
    React.createElement('button', { onClick, ...props }, children),
}));

// ── Import after mocks ──────────────────────────────────────────────────

import { SDLCSuggestionCards } from '../SDLCSuggestionCards';
import type { SuggestionCardData } from '../../types';

// ── Fixtures ────────────────────────────────────────────────────────────

const suggestions: SuggestionCardData[] = [
  {
    id: '1',
    type: 'sprint_completion',
    title: 'Sprint on track',
    description: '70% of sprint completed with 4 days remaining',
    severity: 'info',
  },
  {
    id: '2',
    type: 'stale_alert',
    title: 'Stale issues detected',
    description: '2 issues have no commits in 5+ days',
    actionLabel: 'View issues',
    severity: 'warning',
  },
  {
    id: '3',
    type: 'actionable_suggestion',
    title: 'Consider splitting PS-45',
    description: 'This issue has grown beyond the sprint scope',
    actionLabel: 'Open issue',
    severity: 'critical',
  },
];

// ── Tests ────────────────────────────────────────────────────────────────

describe('SDLCSuggestionCards', () => {
  it('returns null when no suggestions', () => {
    const { container } = render(<SDLCSuggestionCards suggestions={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders all suggestion cards', () => {
    render(<SDLCSuggestionCards suggestions={suggestions} />);
    expect(screen.getByText('Sprint on track')).toBeInTheDocument();
    expect(screen.getByText('Stale issues detected')).toBeInTheDocument();
    expect(screen.getByText('Consider splitting PS-45')).toBeInTheDocument();
  });

  it('renders descriptions', () => {
    render(<SDLCSuggestionCards suggestions={suggestions} />);
    expect(screen.getByText(/70% of sprint completed/)).toBeInTheDocument();
  });

  it('renders severity badges', () => {
    render(<SDLCSuggestionCards suggestions={suggestions} />);
    const badges = screen.getAllByTestId('badge');
    expect(badges).toHaveLength(3);
    expect(badges[0]!.textContent).toBe('info');
    expect(badges[1]!.textContent).toBe('warning');
    expect(badges[2]!.textContent).toBe('critical');
  });

  it('renders action buttons when actionLabel provided', () => {
    const onAction = vi.fn();
    render(<SDLCSuggestionCards suggestions={suggestions} onAction={onAction} />);
    expect(screen.getByText('View issues')).toBeInTheDocument();
    expect(screen.getByText('Open issue')).toBeInTheDocument();
  });

  it('does not render action button when no actionLabel', () => {
    const onAction = vi.fn();
    render(<SDLCSuggestionCards suggestions={[suggestions[0]!]} onAction={onAction} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('calls onAction when action button clicked', async () => {
    const onAction = vi.fn();
    const user = userEvent.setup();
    render(<SDLCSuggestionCards suggestions={[suggestions[1]!]} onAction={onAction} />);
    await user.click(screen.getByText('View issues'));
    expect(onAction).toHaveBeenCalledOnce();
    expect(onAction).toHaveBeenCalledWith(suggestions[1]);
  });
});
