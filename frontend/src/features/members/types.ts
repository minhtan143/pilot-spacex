/**
 * Member profile feature types.
 * Mirrors backend MemberProfileResponse and MemberActivityResponse schemas.
 */

export interface MemberContributionStats {
  issuesCreated: number;
  issuesAssigned: number;
  cycleVelocity: number;
  capacityUtilizationPct: number;
  prCommitLinksCount: number;
}

export interface MemberProfile {
  userId: string;
  email: string;
  fullName: string | null;
  avatarUrl: string | null;
  role: string;
  joinedAt: string;
  weeklyAvailableHours: number;
  stats: MemberContributionStats;
}

export interface MemberActivityItem {
  id: string;
  activityType: string;
  field: string | null;
  oldValue: string | null;
  newValue: string | null;
  comment: string | null;
  createdAt: string;
  issueId: string | null;
  issueIdentifier: string | null;
  issueTitle: string | null;
}

export interface MemberActivityPage {
  items: MemberActivityItem[];
  total: number;
  page: number;
  pageSize: number;
}

/** Issue chip used in the Issue Digest tab. */
export interface MemberIssueDigestItem {
  id: string;
  identifier: string;
  title: string;
  state: string;
}
