/**
 * useMemberProfile hook tests.
 *
 * Verifies TanStack Query integration: enabled guard, loading, success, and error states.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useMemberProfile } from '../useMemberProfile';
import type { MemberProfile } from '../../types';

vi.mock('@/services/api/members', () => ({
  membersApi: {
    getProfile: vi.fn(),
  },
}));

import { membersApi } from '@/services/api/members';

const mockProfile: MemberProfile = {
  userId: 'user-1',
  email: 'alice@example.com',
  fullName: 'Alice Smith',
  avatarUrl: null,
  role: 'member',
  joinedAt: '2025-01-01T00:00:00Z',
  weeklyAvailableHours: 40,
  stats: {
    issuesCreated: 12,
    issuesAssigned: 8,
    cycleVelocity: 3.5,
    capacityUtilizationPct: 75,
    prCommitLinksCount: 5,
  },
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useMemberProfile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns loading state initially when query is enabled', () => {
    vi.mocked(membersApi.getProfile).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useMemberProfile('ws-1', 'user-1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('returns member data on successful fetch', async () => {
    vi.mocked(membersApi.getProfile).mockResolvedValue(mockProfile);

    const { result } = renderHook(() => useMemberProfile('ws-1', 'user-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(membersApi.getProfile).toHaveBeenCalledWith('ws-1', 'user-1');
    expect(result.current.data).toEqual(mockProfile);
  });

  it('returns error state when API call fails', async () => {
    vi.mocked(membersApi.getProfile).mockRejectedValue(new Error('Not found'));

    const { result } = renderHook(() => useMemberProfile('ws-1', 'user-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.data).toBeUndefined();
  });

  it('does not query when workspaceId is empty', () => {
    const { result } = renderHook(() => useMemberProfile('', 'user-1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(membersApi.getProfile).not.toHaveBeenCalled();
  });

  it('does not query when userId is empty', () => {
    const { result } = renderHook(() => useMemberProfile('ws-1', ''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(membersApi.getProfile).not.toHaveBeenCalled();
  });

  it('does not query when both workspaceId and userId are empty', () => {
    const { result } = renderHook(() => useMemberProfile('', ''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(membersApi.getProfile).not.toHaveBeenCalled();
  });
});
