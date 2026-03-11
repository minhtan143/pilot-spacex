/**
 * TemplateCard — Displays a skill template with source badge and actions.
 *
 * Plain component (NOT observer) — receives all data via props.
 * Source: Phase 20, P20-09
 */

'use client';

import { Lock, MoreVertical, Power, Pencil, Trash2, Wand2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { SkillTemplate } from '@/services/api/skill-templates';

interface TemplateCardProps {
  template: SkillTemplate;
  onUseThis: (template: SkillTemplate) => void;
  onEdit?: (template: SkillTemplate) => void;
  onToggleActive?: (template: SkillTemplate) => void;
  onDelete?: (template: SkillTemplate) => void;
  isAdmin: boolean;
}

const SOURCE_BADGE_STYLES: Record<string, string> = {
  built_in: 'border-blue-500/20 bg-blue-500/10 text-blue-500 dark:text-blue-400',
  workspace: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-500 dark:text-emerald-400',
  custom: 'border-purple-500/20 bg-purple-500/10 text-purple-500 dark:text-purple-400',
};

const SOURCE_LABELS: Record<string, string> = {
  built_in: 'Built-in',
  workspace: 'Workspace',
  custom: 'Custom',
};

export function TemplateCard({
  template,
  onUseThis,
  onEdit,
  onToggleActive,
  onDelete,
  isAdmin,
}: TemplateCardProps) {
  const isBuiltIn = template.source === 'built_in';
  const badgeStyle = SOURCE_BADGE_STYLES[template.source] ?? SOURCE_BADGE_STYLES.custom;
  const sourceLabel = SOURCE_LABELS[template.source] ?? template.source;

  return (
    <article
      className={`rounded-lg border bg-card p-4 transition-shadow hover:shadow-sm ${
        !template.is_active ? 'opacity-60' : ''
      }`}
      data-testid="template-card"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg" role="img" aria-label={template.name}>
            {template.icon || '🎯'}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold truncate">{template.name}</h3>
              {isBuiltIn && (
                <Lock
                  className="h-3 w-3 text-muted-foreground shrink-0"
                  aria-label="Built-in (read-only)"
                />
              )}
            </div>
            <Badge variant="outline" className={`text-[10px] px-1.5 py-0 h-4 mt-0.5 ${badgeStyle}`}>
              {sourceLabel}
            </Badge>
          </div>
        </div>

        {/* Admin actions dropdown */}
        {isAdmin && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0">
                <MoreVertical className="h-4 w-4" />
                <span className="sr-only">Template actions</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {!isBuiltIn && onEdit && (
                <DropdownMenuItem onClick={() => onEdit(template)}>
                  <Pencil className="mr-2 h-3.5 w-3.5" />
                  Edit
                </DropdownMenuItem>
              )}
              {onToggleActive && (
                <DropdownMenuItem onClick={() => onToggleActive(template)}>
                  <Power className="mr-2 h-3.5 w-3.5" />
                  {template.is_active ? 'Deactivate' : 'Activate'}
                </DropdownMenuItem>
              )}
              {!isBuiltIn && onDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => onDelete(template)}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 h-3.5 w-3.5" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {/* Description */}
      <p className="text-xs text-muted-foreground line-clamp-2 mb-3 min-h-[2rem]">
        {template.description}
      </p>

      {/* Use This button */}
      {template.is_active && (
        <Button size="sm" variant="outline" className="w-full" onClick={() => onUseThis(template)}>
          <Wand2 className="mr-1.5 h-3.5 w-3.5" />
          Use This
        </Button>
      )}
    </article>
  );
}
