/**
 * useActiveCycleMetrics hook tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ── Mocks ────────────────────────────────────────────────────────────────

const mockGetActive = vi.fn();
const mockGetVelocityData = vi.fn();

vi.mock('@/services/api/cycles', () => ({
  cyclesApi: {
    getActive: (...args: unknown[]) => mockGetActive(...args),
    getVelocityData: (...args: unknown[]) => mockGetVelocityData(...args),
  },
}));

// ── Import after mocks ──────────────────────────────────────────────────

import { useActiveCycleMetrics } from '../useActiveCycleMetrics';

// ── Helpers ─────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

const mockCycle = {
  id: 'cycle-1',
  name: 'Sprint 5',
  totalIssues: 10,
  completedIssues: 7,
};

const mockVelocity = {
  projectId: 'proj-1',
  dataPoints: [
    { cycleId: 'c1', cycleName: 'S1', completedPoints: 8, committedPoints: 10, velocity: 8 },
    { cycleId: 'c2', cycleName: 'S2', completedPoints: 12, committedPoints: 15, velocity: 12 },
  ],
  averageVelocity: 10,
};

// ── Tests ────────────────────────────────────────────────────────────────

describe('useActiveCycleMetrics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null cycle and empty velocity when no projects', () => {
    const { result } = renderHook(
      () =>
        useActiveCycleMetrics({
          workspaceId: 'ws-1',
          projectIds: [],
        }),
      { wrapper: createWrapper() }
    );

    expect(result.current.activeCycle).toBeNull();
    expect(result.current.velocityData).toEqual([]);
    expect(result.current.averageVelocity).toBe(0);
  });

  it('fetches and returns active cycle and velocity data', async () => {
    mockGetActive.mockResolvedValue(mockCycle);
    mockGetVelocityData.mockResolvedValue(mockVelocity);

    const { result } = renderHook(
      () =>
        useActiveCycleMetrics({
          workspaceId: 'ws-1',
          projectIds: ['proj-1'],
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.activeCycle).not.toBeNull();
    });

    expect(result.current.activeCycle?.name).toBe('Sprint 5');
    expect(result.current.velocityData).toHaveLength(2);
    expect(result.current.averageVelocity).toBe(10);
  });

  it('handles null active cycle gracefully', async () => {
    mockGetActive.mockResolvedValue(null);
    mockGetVelocityData.mockResolvedValue(mockVelocity);

    const { result } = renderHook(
      () =>
        useActiveCycleMetrics({
          workspaceId: 'ws-1',
          projectIds: ['proj-1'],
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.activeCycle).toBeNull();
    expect(result.current.velocityData).toHaveLength(2);
  });

  it('does not fetch when disabled', () => {
    renderHook(
      () =>
        useActiveCycleMetrics({
          workspaceId: 'ws-1',
          projectIds: ['proj-1'],
          enabled: false,
        }),
      { wrapper: createWrapper() }
    );

    expect(mockGetActive).not.toHaveBeenCalled();
    expect(mockGetVelocityData).not.toHaveBeenCalled();
  });
});
