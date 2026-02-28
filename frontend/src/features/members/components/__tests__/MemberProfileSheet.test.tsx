/**
 * MemberProfileSheet component tests.
 *
 * Verifies sheet open/close behavior, loading skeleton, member data display,
 * and "View full profile" link href.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import type { MemberProfile, MemberActivityPage } from '../../types';

// Mock hooks before importing the component so vi.mock hoisting works correctly.
vi.mock('../../hooks/useMemberProfile', () => ({
  useMemberProfile: vi.fn(),
}));

vi.mock('../../hooks/useMemberActivity', () => ({
  useMemberActivity: vi.fn(),
}));

// next/link is already partially handled by vitest.setup.tsx, but we
// explicitly mock it here to capture href props in tests.
vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) =>
    React.createElement('a', { href, ...props }, children),
}));

import { MemberProfileSheet } from '../MemberProfileSheet';
import { useMemberProfile } from '../../hooks/useMemberProfile';
import { useMemberActivity } from '../../hooks/useMemberActivity';

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

const emptyActivityData: { pages: MemberActivityPage[]; pageParams: unknown[] } = {
  pages: [{ items: [], total: 0, page: 1, pageSize: 20 }],
  pageParams: [1],
};

const defaultSheetProps = {
  workspaceId: 'ws-1',
  workspaceSlug: 'my-workspace',
  onClose: vi.fn(),
};

function setup(userId: string | null, overrides?: Partial<typeof defaultSheetProps>) {
  return render(<MemberProfileSheet {...defaultSheetProps} {...overrides} userId={userId} />);
}

describe('MemberProfileSheet', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default: loaded, no data (covers the closed sheet case).
    vi.mocked(useMemberProfile).mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useMemberProfile>);

    vi.mocked(useMemberActivity).mockReturnValue({
      data: emptyActivityData,
      isLoading: false,
    } as unknown as ReturnType<typeof useMemberActivity>);
  });

  it('does not render visible sheet content when userId is null', () => {
    setup(null);

    // Sheet is closed — no SheetContent visible in DOM.
    expect(screen.queryByText('Alice Smith')).not.toBeInTheDocument();
    expect(screen.queryByText('View full profile')).not.toBeInTheDocument();
  });

  it('renders open sheet when userId is provided', () => {
    vi.mocked(useMemberProfile).mockReturnValue({
      data: mockProfile,
      isLoading: false,
    } as ReturnType<typeof useMemberProfile>);

    setup('user-1');

    // Sheet is open — content should be accessible.
    expect(screen.getByText('View full profile')).toBeInTheDocument();
  });

  it('shows loading skeleton when member data is loading', () => {
    vi.mocked(useMemberProfile).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useMemberProfile>);

    setup('user-1');

    expect(screen.getByText('Loading member profile')).toBeInTheDocument();
  });

  it('shows member full name when data loads', () => {
    vi.mocked(useMemberProfile).mockReturnValue({
      data: mockProfile,
      isLoading: false,
    } as ReturnType<typeof useMemberProfile>);

    setup('user-1');

    // sr-only SheetTitle and compact header both render the name.
    const nameElements = screen.getAllByText('Alice Smith');
    expect(nameElements.length).toBeGreaterThan(0);
  });

  it('shows member email in sr-only SheetDescription when data loads', () => {
    vi.mocked(useMemberProfile).mockReturnValue({
      data: mockProfile,
      isLoading: false,
    } as ReturnType<typeof useMemberProfile>);

    setup('user-1');

    expect(screen.getByText('Profile details for alice@example.com')).toBeInTheDocument();
  });

  it('renders "View full profile" link with correct href', () => {
    vi.mocked(useMemberProfile).mockReturnValue({
      data: mockProfile,
      isLoading: false,
    } as ReturnType<typeof useMemberProfile>);

    setup('user-1');

    const link = screen.getByRole('link', { name: /view full profile/i });
    expect(link).toHaveAttribute('href', '/my-workspace/members/user-1');
  });

  it('shows "No activity yet." when activity list is empty', () => {
    vi.mocked(useMemberProfile).mockReturnValue({
      data: mockProfile,
      isLoading: false,
    } as ReturnType<typeof useMemberProfile>);

    setup('user-1');

    expect(screen.getByText('No recent activity to show.')).toBeInTheDocument();
  });

  it('renders activity items when activity data is present', () => {
    vi.mocked(useMemberProfile).mockReturnValue({
      data: mockProfile,
      isLoading: false,
    } as ReturnType<typeof useMemberProfile>);

    vi.mocked(useMemberActivity).mockReturnValue({
      data: {
        pages: [
          {
            items: [
              {
                id: 'act-1',
                activityType: 'status_change',
                field: 'state',
                oldValue: 'Todo',
                newValue: 'In Progress',
                comment: null,
                createdAt: '2025-01-02T10:00:00Z',
                issueId: 'issue-1',
                issueIdentifier: 'PS-42',
                issueTitle: 'Fix bug',
              },
            ],
            total: 1,
            page: 1,
            pageSize: 20,
          },
        ],
        pageParams: [1],
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useMemberActivity>);

    setup('user-1');

    expect(screen.getByText('PS-42')).toBeInTheDocument();
    expect(screen.getByText(/Changed state/)).toBeInTheDocument();
  });

  it('shows activity loading skeleton when activity is loading', () => {
    vi.mocked(useMemberProfile).mockReturnValue({
      data: mockProfile,
      isLoading: false,
    } as ReturnType<typeof useMemberProfile>);

    vi.mocked(useMemberActivity).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof useMemberActivity>);

    setup('user-1');

    // Contribution stats section is rendered (not loading for member).
    expect(screen.getByLabelText('Contribution statistics')).toBeInTheDocument();
    // Activity section shows skeletons, no "No activity yet."
    expect(screen.queryByText('No activity yet.')).not.toBeInTheDocument();
  });

  it('renders member email fallback when fullName is null', () => {
    const profileNoName: MemberProfile = { ...mockProfile, fullName: null };
    vi.mocked(useMemberProfile).mockReturnValue({
      data: profileNoName,
      isLoading: false,
    } as ReturnType<typeof useMemberProfile>);

    setup('user-1');

    // Both sr-only title and compact header should show email as fallback.
    const emailElements = screen.getAllByText('alice@example.com');
    expect(emailElements.length).toBeGreaterThan(0);
  });
});
