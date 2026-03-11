/**
 * TemplateCatalog — Observer component displaying browsable skill templates.
 *
 * Uses useSkillTemplates TanStack Query hook. Grid layout consistent with plugins.
 * Source: Phase 20, P20-09
 */

'use client';

import { observer } from 'mobx-react-lite';
import { Layers } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import { useSkillTemplates } from '@/services/api/skill-templates';
import type { SkillTemplate } from '@/services/api/skill-templates';
import { TemplateCard } from './template-card';

interface TemplateCatalogProps {
  workspaceSlug: string;
  isAdmin: boolean;
  onUseThis: (template: SkillTemplate) => void;
  onEditTemplate?: (template: SkillTemplate) => void;
  onToggleTemplateActive?: (template: SkillTemplate) => void;
  onDeleteTemplate?: (template: SkillTemplate) => void;
}

export const TemplateCatalog = observer(function TemplateCatalog({
  workspaceSlug,
  isAdmin,
  onUseThis,
  onEditTemplate,
  onToggleTemplateActive,
  onDeleteTemplate,
}: TemplateCatalogProps) {
  const { data: templates, isLoading, isError, error } = useSkillTemplates(workspaceSlug);

  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[160px] rounded-lg" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load templates: {error?.message ?? 'Unknown error'}
        </AlertDescription>
      </Alert>
    );
  }

  if (!templates || templates.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 px-4">
        <div className="rounded-lg border border-border/50 bg-muted/30 p-3 mb-3">
          <Layers className="h-6 w-6 text-muted-foreground/50" />
        </div>
        <h3 className="text-sm font-medium text-foreground">No skill templates available</h3>
        <p className="mt-0.5 text-xs text-muted-foreground text-center max-w-[280px]">
          {isAdmin
            ? 'Create a workspace template or wait for built-in templates to be seeded.'
            : 'No templates have been configured for this workspace yet.'}
        </p>
      </div>
    );
  }

  // Sort: active first, then by sort_order
  const sorted = [...templates].sort((a, b) => {
    if (a.is_active !== b.is_active) return a.is_active ? -1 : 1;
    return a.sort_order - b.sort_order;
  });

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {sorted.map((template) => (
        <TemplateCard
          key={template.id}
          template={template}
          onUseThis={onUseThis}
          onEdit={onEditTemplate}
          onToggleActive={onToggleTemplateActive}
          onDelete={onDeleteTemplate}
          isAdmin={isAdmin}
        />
      ))}
    </div>
  );
});
