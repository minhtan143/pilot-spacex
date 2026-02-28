'use client';

/**
 * useActiveCycleMetrics — Fetch active cycle + velocity data for homepage sparkline.
 *
 * Uses only the first project in `projectIds` (lowest-index). Multi-project
 * aggregation is out of scope for the homepage summary view; the caller should
 * pass the primary/default project first.
 *
 * Note: `cyclesApi.getVelocityData()` endpoint is not yet implemented on the
 * backend. The velocity query will 404 and fall back to empty data gracefully.
 */

import { useQueries } from '@tanstack/react-query';
import { cyclesApi } from '@/services/api/cycles';
import { SPARKLINE_POINT_COUNT } from '../constants';
import type { VelocityDataPoint, Cycle } from '@/types';

export interface UseActiveCycleMetricsOptions {
  workspaceId: string;
  projectIds: string[];
  enabled?: boolean;
}

export interface ActiveCycleMetrics {
  activeCycle: Cycle | null;
  velocityData: VelocityDataPoint[];
  averageVelocity: number;
  isLoading: boolean;
}

export function useActiveCycleMetrics({
  workspaceId,
  projectIds,
  enabled = true,
}: UseActiveCycleMetricsOptions): ActiveCycleMetrics {
  const firstProjectId = projectIds[0] ?? '';

  const queries = useQueries({
    queries: [
      {
        queryKey: ['homepage', 'active-cycle', workspaceId, firstProjectId],
        queryFn: () => cyclesApi.getActive(workspaceId, firstProjectId),
        enabled: enabled && !!workspaceId && !!firstProjectId,
        staleTime: 60_000,
      },
      {
        queryKey: ['homepage', 'velocity', workspaceId, firstProjectId],
        queryFn: () =>
          cyclesApi.getVelocityData(workspaceId, firstProjectId, SPARKLINE_POINT_COUNT),
        enabled: enabled && !!workspaceId && !!firstProjectId,
        staleTime: 120_000,
      },
    ],
  });

  const cycleQuery = queries[0]!;
  const velocityQuery = queries[1]!;

  return {
    activeCycle: (cycleQuery.data as Cycle | null | undefined) ?? null,
    velocityData:
      (velocityQuery.data as { dataPoints?: VelocityDataPoint[] } | undefined)?.dataPoints ?? [],
    averageVelocity:
      (velocityQuery.data as { averageVelocity?: number } | undefined)?.averageVelocity ?? 0,
    isLoading: cycleQuery.isLoading || velocityQuery.isLoading,
  };
}
