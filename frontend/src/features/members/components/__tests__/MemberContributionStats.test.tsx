/**
 * MemberContributionStats component tests.
 *
 * Verifies skeleton loading, stat card rendering, progress bar, and PR/commit count text.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemberContributionStats } from '../MemberContributionStats';
import type { MemberContributionStats as Stats } from '../../types';

const mockStats: Stats = {
  issuesCreated: 12,
  issuesAssigned: 8,
  cycleVelocity: 3.5,
  capacityUtilizationPct: 75,
  prCommitLinksCount: 5,
};

describe('MemberContributionStats', () => {
  it('renders skeleton loading state when isLoading is true', () => {
    render(<MemberContributionStats isLoading />);

    const container = screen.getByLabelText('Loading contribution stats');
    expect(container).toBeInTheDocument();
    expect(container).toHaveAttribute('aria-busy', 'true');
  });

  it('renders skeleton when stats is undefined and isLoading is false', () => {
    render(<MemberContributionStats isLoading={false} />);

    const container = screen.getByLabelText('Loading contribution stats');
    expect(container).toBeInTheDocument();
  });

  it('renders 4 stat card labels when stats are provided', () => {
    render(<MemberContributionStats stats={mockStats} />);

    expect(screen.getByText('Issues Created')).toBeInTheDocument();
    expect(screen.getByText('Issues Assigned')).toBeInTheDocument();
    expect(screen.getByText('Cycle Velocity')).toBeInTheDocument();
    expect(screen.getByText('Capacity')).toBeInTheDocument();
  });

  it('renders correct numeric values for issues created and assigned', () => {
    render(<MemberContributionStats stats={mockStats} />);

    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('renders cycle velocity formatted to one decimal place', () => {
    render(<MemberContributionStats stats={mockStats} />);

    expect(screen.getByText('3.5')).toBeInTheDocument();
    expect(screen.getByText('avg issues/sprint')).toBeInTheDocument();
  });

  it('renders capacity utilization percentage', () => {
    render(<MemberContributionStats stats={mockStats} />);

    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('renders progress bar with aria-label for capacity utilization', () => {
    render(<MemberContributionStats stats={mockStats} />);

    expect(screen.getByLabelText('Capacity utilization 75%')).toBeInTheDocument();
  });

  it('shows plural PR/commit links text when count is not 1', () => {
    render(<MemberContributionStats stats={mockStats} />);

    expect(screen.getByText('5 PR/commit links')).toBeInTheDocument();
  });

  it('shows singular PR/commit link text when count is 1', () => {
    const singleLinkStats: Stats = { ...mockStats, prCommitLinksCount: 1 };
    render(<MemberContributionStats stats={singleLinkStats} />);

    expect(screen.getByText('1 PR/commit link')).toBeInTheDocument();
  });

  it('shows zero PR/commit links text when count is 0', () => {
    const noLinkStats: Stats = { ...mockStats, prCommitLinksCount: 0 };
    render(<MemberContributionStats stats={noLinkStats} />);

    expect(screen.getByText('0 PR/commit links')).toBeInTheDocument();
  });

  it('applies destructive color class when capacity exceeds 90%', () => {
    const highCapacityStats: Stats = { ...mockStats, capacityUtilizationPct: 95 };
    render(<MemberContributionStats stats={highCapacityStats} />);

    const pctSpan = screen.getByText('95%');
    expect(pctSpan).toHaveClass('text-destructive');
  });

  it('applies yellow color class when capacity is between 70% and 90%', () => {
    const mediumCapacityStats: Stats = { ...mockStats, capacityUtilizationPct: 80 };
    render(<MemberContributionStats stats={mediumCapacityStats} />);

    const pctSpan = screen.getByText('80%');
    expect(pctSpan).toHaveClass('text-amber-600');
  });

  it('applies foreground color class when capacity is 70% or below', () => {
    const lowCapacityStats: Stats = { ...mockStats, capacityUtilizationPct: 50 };
    render(<MemberContributionStats stats={lowCapacityStats} />);

    const pctSpan = screen.getByText('50%');
    expect(pctSpan).toHaveClass('text-foreground');
  });

  it('renders contribution statistics aria-label on the grid when data is loaded', () => {
    render(<MemberContributionStats stats={mockStats} />);

    expect(screen.getByLabelText('Contribution statistics')).toBeInTheDocument();
  });
});
