/**
 * MySkillCard — Displays a user's personalized skill.
 *
 * Plain component (NOT observer) — receives all data via props.
 * Source: Phase 20, P20-10
 */

'use client';

import { Power, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { UserSkill } from '@/services/api/user-skills';

interface MySkillCardProps {
  skill: UserSkill;
  onToggleActive: (skill: UserSkill) => void;
  onDelete: (skill: UserSkill) => void;
}

export function MySkillCard({ skill, onToggleActive, onDelete }: MySkillCardProps) {
  const displayName = skill.template_name ?? 'Custom Skill';

  return (
    <article
      className={`rounded-lg border bg-card p-4 transition-shadow hover:shadow-sm ${
        !skill.is_active ? 'opacity-60' : ''
      }`}
      data-testid="my-skill-card"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold truncate">{displayName}</h3>
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 h-4 mt-0.5 ${
              skill.is_active
                ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-500 dark:text-emerald-400'
                : 'border-muted-foreground/20 bg-muted/50 text-muted-foreground'
            }`}
          >
            {skill.is_active ? 'Active' : 'Inactive'}
          </Badge>
        </div>

        <div className="flex gap-1 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => onToggleActive(skill)}
            aria-label={skill.is_active ? 'Deactivate skill' : 'Activate skill'}
          >
            <Power className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive hover:text-destructive"
            onClick={() => onDelete(skill)}
            aria-label="Delete skill"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Experience snippet */}
      {skill.experience_description && (
        <p className="text-xs text-muted-foreground line-clamp-2">{skill.experience_description}</p>
      )}

      {/* Skill content preview */}
      <p className="mt-2 text-xs text-muted-foreground/70 font-mono line-clamp-2">
        {skill.skill_content.slice(0, 150)}
        {skill.skill_content.length > 150 ? '\u2026' : ''}
      </p>
    </article>
  );
}
