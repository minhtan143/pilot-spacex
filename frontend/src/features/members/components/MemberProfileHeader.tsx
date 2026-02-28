/**
 * MemberProfileHeader — Avatar + name + email + role badge + meta.
 *
 * Used in both sheet (compact) and full profile page.
 */

'use client';

import { formatDistanceToNow } from 'date-fns';
import { Clock } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import type { MemberProfile } from '../types';

interface MemberProfileHeaderProps {
  member: MemberProfile;
  compact?: boolean;
}

function getInitials(fullName: string | null, email: string): string {
  if (fullName) {
    const parts = fullName.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return `${parts[0]![0]}${parts[parts.length - 1]![0]}`.toUpperCase();
    return parts[0]?.[0]?.toUpperCase() ?? email[0]?.toUpperCase() ?? '?';
  }
  return email[0]?.toUpperCase() ?? '?';
}

const ROLE_BADGE: Record<string, 'default' | 'secondary' | 'outline'> = {
  owner: 'default',
  admin: 'secondary',
  member: 'outline',
  guest: 'outline',
};

export function MemberProfileHeader({ member, compact = false }: MemberProfileHeaderProps) {
  const initials = getInitials(member.fullName, member.email);
  const joinedLabel = formatDistanceToNow(new Date(member.joinedAt), { addSuffix: true });
  const badgeVariant = ROLE_BADGE[member.role] ?? 'outline';

  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <Avatar className="h-10 w-10 shrink-0">
          <AvatarImage src={member.avatarUrl ?? undefined} alt={member.fullName ?? member.email} />
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium leading-tight">{member.fullName ?? member.email}</p>
          <p className="truncate text-xs text-muted-foreground">{member.email}</p>
        </div>
        <Badge variant={badgeVariant} className="ml-auto shrink-0 capitalize">
          {member.role}
        </Badge>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-4">
      <Avatar className="h-16 w-16 shrink-0">
        <AvatarImage src={member.avatarUrl ?? undefined} alt={member.fullName ?? member.email} />
        <AvatarFallback className="text-lg">{initials}</AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-semibold">{member.fullName ?? member.email}</h2>
          <Badge variant={badgeVariant} className="capitalize">
            {member.role}
          </Badge>
        </div>
        <p className="mt-0.5 text-sm text-muted-foreground">{member.email}</p>
        <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
          <span>Joined {joinedLabel}</span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" aria-hidden="true" />
            {member.weeklyAvailableHours}h/week available
          </span>
        </div>
      </div>
    </div>
  );
}
