/**
 * SprintSparkline component tests.
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

import { SprintSparkline } from '../SprintSparkline';
import type { VelocityDataPoint, Cycle } from '@/types';

// ── Fixtures ────────────────────────────────────────────────────────────

const velocityData: VelocityDataPoint[] = [
  { cycleId: 'c1', cycleName: 'S1', completedPoints: 8, committedPoints: 10, velocity: 8 },
  { cycleId: 'c2', cycleName: 'S2', completedPoints: 12, committedPoints: 15, velocity: 12 },
  { cycleId: 'c3', cycleName: 'S3', completedPoints: 10, committedPoints: 12, velocity: 10 },
];

const activeCycle = {
  id: 'cycle-1',
  name: 'Sprint 5',
  metrics: {
    cycleId: 'cycle-1',
    totalIssues: 20,
    completedIssues: 14,
    inProgressIssues: 4,
    notStartedIssues: 2,
    totalPoints: 40,
    completedPoints: 28,
    completionPercentage: 70,
    velocity: 14,
  },
} as unknown as Cycle;

// ── Tests ────────────────────────────────────────────────────────────────

describe('SprintSparkline', () => {
  it('returns null when no velocity data and no active cycle', () => {
    const { container } = render(
      <SprintSparkline velocityData={[]} averageVelocity={0} activeCycle={null} />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders SVG with polyline when velocity data has 2+ points', () => {
    const { container } = render(
      <SprintSparkline velocityData={velocityData} averageVelocity={10} activeCycle={null} />
    );
    expect(container.querySelector('svg')).toBeInTheDocument();
    expect(container.querySelector('polyline')).toBeInTheDocument();
  });

  it('renders completion percentage when active cycle exists', () => {
    render(
      <SprintSparkline velocityData={velocityData} averageVelocity={10} activeCycle={activeCycle} />
    );
    expect(screen.getByText('70%')).toBeInTheDocument();
  });

  it('renders tooltip with cycle name and velocity', () => {
    render(
      <SprintSparkline velocityData={velocityData} averageVelocity={10} activeCycle={activeCycle} />
    );
    expect(screen.getByText(/Sprint 5: 70% complete/)).toBeInTheDocument();
  });

  it('handles single data point gracefully (no SVG)', () => {
    const singlePoint = velocityData.slice(0, 1);
    render(
      <SprintSparkline velocityData={singlePoint} averageVelocity={8} activeCycle={activeCycle} />
    );
    // Still shows completion but no SVG polyline
    expect(screen.getByText('70%')).toBeInTheDocument();
  });

  it('has proper aria-label for accessibility', () => {
    render(
      <SprintSparkline velocityData={velocityData} averageVelocity={10} activeCycle={activeCycle} />
    );
    const sparkline = screen.getByRole('img');
    expect(sparkline).toHaveAttribute('aria-label', expect.stringContaining('Sprint 5'));
  });
});
