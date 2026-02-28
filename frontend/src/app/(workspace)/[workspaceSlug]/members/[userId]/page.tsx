/**
 * Member profile page — /[workspaceSlug]/members/[userId]
 *
 * Thin server component that passes workspace/user context to the client MemberProfilePage.
 * workspaceId is resolved client-side from WorkspaceStore using the slug.
 */

import { notFound } from 'next/navigation';
import { MemberProfilePage } from '@/features/members';

interface PageParams {
  workspaceSlug: string;
  userId: string;
}

interface MemberProfileRouteProps {
  params: Promise<PageParams>;
}

export default async function MemberProfileRoute({ params }: MemberProfileRouteProps) {
  const { workspaceSlug, userId } = await params;

  if (!workspaceSlug || !userId) {
    notFound();
  }

  return <MemberProfilePage workspaceSlug={workspaceSlug} userId={userId} />;
}

export async function generateMetadata({ params }: MemberProfileRouteProps) {
  const { workspaceSlug } = await params;
  return {
    title: `Member Profile — ${workspaceSlug}`,
  };
}
