/**
 * SkillsSettingsPage - Workspace AI Skills configuration.
 *
 * Phase 20: Unified skill management with SkillGeneratorModal.
 * Source: FR-009, FR-010, FR-015, FR-018, US6
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle, Lock, MousePointerClick, Package, Plus, Wand2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useStore } from '@/stores';
import {
  useRoleSkills,
  useRoleTemplates,
  useUpdateRoleSkill,
  useRegenerateSkill,
  useDeleteRoleSkill,
} from '@/features/onboarding/hooks';
import {
  useWorkspaceRoleSkills,
  useActivateWorkspaceSkill,
  useDeleteWorkspaceSkill,
} from '@/services/api/workspace-role-skills';
import type { WorkspaceRoleSkill } from '@/services/api/workspace-role-skills';
import { WorkspaceSkillCard } from '../components/workspace-skill-card';
import { SkillCard } from '../components/skill-card';
import { RegenerateSkillModal } from '../components/regenerate-skill-modal';
import { ConfirmActionDialog } from '../components/confirm-action-dialog';
import { PluginsTabContent } from '../components/plugins-tab-content';
import { ActionButtonsTabContent } from '../components/action-buttons-tab-content';
import { SkillGeneratorModal } from '../components/skill-generator-modal';
import type { SkillGeneratorMode } from '../components/skill-generator-modal';
import type { RoleSkill } from '@/services/api/role-skills';

const MAX_SKILLS = 3;

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="h-9 w-56" />
      <Skeleton className="h-[140px] w-full rounded-lg" />
      <Skeleton className="h-[140px] w-full rounded-lg" />
    </div>
  );
}

function EmptyState({ onSetup }: { onSetup: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 space-y-3">
      <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
        <Wand2 className="h-6 w-6 text-muted-foreground/50" />
      </div>
      <div className="text-center">
        <h3 className="text-sm font-medium text-foreground">No skills configured</h3>
        <p className="mt-0.5 text-xs text-muted-foreground max-w-[260px]">
          Set up your skill to personalize AI assistance.
        </p>
      </div>
      <Button size="sm" onClick={onSetup}>
        <Plus className="mr-1.5 h-4 w-4" />
        Set Up Your Skill
      </Button>
    </div>
  );
}

function GuestView() {
  return (
    <div className="py-8">
      <Alert role="alert">
        <Lock className="h-4 w-4" />
        <AlertDescription>
          Skill configuration requires Member or higher access. Contact a workspace admin for
          permission.
        </AlertDescription>
      </Alert>
    </div>
  );
}

export const SkillsSettingsPage = observer(function SkillsSettingsPage() {
  const { workspaceStore, roleSkillStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  // Server state
  const { data: skills, isLoading, isError, error } = useRoleSkills(workspaceId);
  const { data: templates } = useRoleTemplates();
  const updateSkill = useUpdateRoleSkill({ workspaceId });
  const regenerateSkill = useRegenerateSkill({ workspaceId });
  const deleteSkill = useDeleteRoleSkill({ workspaceId });

  // Workspace skills state (admin only)
  const { data: wsSkillsData } = useWorkspaceRoleSkills(workspaceStore.isAdmin ? workspaceId : '');
  const activateWsSkill = useActivateWorkspaceSkill({ workspaceId });
  const deleteWsSkill = useDeleteWorkspaceSkill({ workspaceId });
  const [wsSkillToRemove, setWsSkillToRemove] = React.useState<WorkspaceRoleSkill | null>(null);

  // Unified skill generator modal state
  const [generatorOpen, setGeneratorOpen] = React.useState(false);
  const [generatorMode, setGeneratorMode] = React.useState<SkillGeneratorMode>('personal');

  const openGenerator = (mode: SkillGeneratorMode) => {
    setGeneratorMode(mode);
    setGeneratorOpen(true);
  };

  const handleWsRemoveConfirm = () => {
    if (!wsSkillToRemove) return;
    deleteWsSkill.mutate(wsSkillToRemove.id, {
      onSuccess: () => setWsSkillToRemove(null),
    });
  };

  // UI state
  const [regenerateTarget, setRegenerateTarget] = React.useState<RoleSkill | null>(null);
  const [removeTarget, setRemoveTarget] = React.useState<RoleSkill | null>(null);
  const [resetTarget, setResetTarget] = React.useState<RoleSkill | null>(null);

  // Tab state
  const [activeTab, setActiveTab] = React.useState('skills');
  const [addPluginDialogOpen, setAddPluginDialogOpen] = React.useState(false);

  const skillCount = skills?.length ?? 0;
  const slotsLeft = MAX_SKILLS - skillCount;
  const isMaxReached = skillCount >= MAX_SKILLS;
  const isGuest = workspaceStore.currentUserRole === 'guest';
  const wsSkillCount = wsSkillsData?.skills.length ?? 0;
  const hasAnySkills = skillCount > 0 || wsSkillCount > 0;

  const handleEdit = (skillId: string, content: string) => {
    updateSkill.mutate(
      { skillId, payload: { skillContent: content } },
      { onSuccess: () => roleSkillStore.clearEditingSkillId() }
    );
  };

  const handleRegenerate = (skillId: string) => {
    const skill = skills?.find((s) => s.id === skillId);
    if (skill) setRegenerateTarget(skill);
  };

  const handleRegenerateSubmit = async (experienceDescription: string) => {
    if (!regenerateTarget) throw new Error('No target skill');
    return regenerateSkill.mutateAsync({
      skillId: regenerateTarget.id,
      payload: { experienceDescription },
    });
  };

  const handleRegenerateAccept = (newContent: string, newName: string) => {
    if (!regenerateTarget) return;
    updateSkill.mutate(
      {
        skillId: regenerateTarget.id,
        payload: { skillContent: newContent, roleName: newName },
      },
      { onSuccess: () => setRegenerateTarget(null) }
    );
  };

  const handleReset = (skillId: string) => {
    const skill = skills?.find((s) => s.id === skillId);
    if (skill) setResetTarget(skill);
  };

  const handleResetConfirm = () => {
    if (!resetTarget || !templates) return;
    const template = templates.find((t) => t.roleType === resetTarget.roleType);
    if (template) {
      updateSkill.mutate(
        {
          skillId: resetTarget.id,
          payload: {
            skillContent: template.defaultSkillContent,
            roleName: template.displayName,
          },
        },
        { onSuccess: () => setResetTarget(null) }
      );
    }
  };

  const handleRemove = (skillId: string) => {
    const skill = skills?.find((s) => s.id === skillId);
    if (skill) setRemoveTarget(skill);
  };

  const handleRemoveConfirm = () => {
    if (!removeTarget) return;
    deleteSkill.mutate(removeTarget.id, {
      onSuccess: () => setRemoveTarget(null),
    });
  };

  if (isGuest) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight mb-4">Skills</h1>
        <GuestView />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load skills: {error?.message ?? 'Unknown error'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="px-4 py-4 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-semibold tracking-tight mb-4">Skills</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between gap-3">
          <TabsList>
            <TabsTrigger value="skills">
              <Wand2 className="mr-1.5 h-4 w-4" />
              Skills
            </TabsTrigger>
            {workspaceStore.isAdmin && (
              <TabsTrigger value="plugins">
                <Package className="mr-1.5 h-4 w-4" />
                Plugins
              </TabsTrigger>
            )}
            {workspaceStore.isAdmin && (
              <TabsTrigger value="action-buttons">
                <MousePointerClick className="mr-1.5 h-4 w-4" />
                Action Buttons
              </TabsTrigger>
            )}
          </TabsList>
          {activeTab === 'skills' && (
            <Button
              size="sm"
              onClick={() => openGenerator('personal')}
              disabled={isMaxReached}
              aria-describedby={isMaxReached ? 'max-skills-hint' : undefined}
            >
              <Plus className="mr-1.5 h-4 w-4" />
              Add Skill
              {!isMaxReached && slotsLeft > 0 && (
                <span className="ml-1 text-xs opacity-70">({slotsLeft})</span>
              )}
            </Button>
          )}
          {activeTab === 'plugins' && workspaceStore.isAdmin && (
            <Button size="sm" onClick={() => setAddPluginDialogOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" />
              Add Plugin
            </Button>
          )}
        </div>

        <TabsContent value="skills">
          <div className="space-y-4 pt-3">
            {/* Max skills warning */}
            {isMaxReached && (
              <Alert id="max-skills-hint">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Maximum {MAX_SKILLS} skills per workspace reached. Remove an existing skill to add
                  a new one.
                </AlertDescription>
              </Alert>
            )}

            {/* Unified skills list: personal + workspace skills */}
            {hasAnySkills ? (
              <div className="space-y-4">
                {/* Personal skills */}
                {skills
                  ?.slice()
                  .sort((a, b) => {
                    if (a.isPrimary && !b.isPrimary) return -1;
                    if (!a.isPrimary && b.isPrimary) return 1;
                    return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
                  })
                  .map((skill) => (
                    <SkillCard
                      key={skill.id}
                      skill={skill}
                      onEdit={handleEdit}
                      onRegenerate={handleRegenerate}
                      onReset={handleReset}
                      onRemove={handleRemove}
                      isSaving={updateSkill.isPending}
                    />
                  ))}

                {/* Workspace skills (admin sees management cards) */}
                {workspaceStore.isAdmin &&
                  wsSkillsData?.skills.map((skill) => (
                    <WorkspaceSkillCard
                      key={skill.id}
                      skill={skill}
                      onActivate={(id) => activateWsSkill.mutate(id)}
                      onRemove={(id) =>
                        setWsSkillToRemove(wsSkillsData.skills.find((s) => s.id === id) ?? null)
                      }
                      isActivating={activateWsSkill.isPending}
                      isRemoving={deleteWsSkill.isPending}
                    />
                  ))}
              </div>
            ) : (
              <EmptyState onSetup={() => openGenerator('personal')} />
            )}
          </div>

          {/* Regenerate Modal */}
          {regenerateTarget && (
            <RegenerateSkillModal
              open={!!regenerateTarget}
              onOpenChange={(open) => !open && setRegenerateTarget(null)}
              skill={regenerateTarget}
              onRegenerate={handleRegenerateSubmit}
              onAccept={handleRegenerateAccept}
              isRegenerating={regenerateSkill.isPending}
            />
          )}

          {/* Remove Confirmation */}
          {removeTarget && (
            <ConfirmActionDialog
              open={!!removeTarget}
              onCancel={() => setRemoveTarget(null)}
              onConfirm={handleRemoveConfirm}
              title={`Remove ${removeTarget.roleName} Skill?`}
              description={`This will deactivate the ${removeTarget.roleName} skill for this workspace. The AI assistant will no longer use ${removeTarget.roleName}-specific behavior in your conversations. Your skill content will be permanently deleted.`}
              confirmLabel="Remove Skill"
              variant="destructive"
            />
          )}

          {/* Reset Confirmation */}
          {resetTarget && (
            <ConfirmActionDialog
              open={!!resetTarget}
              onCancel={() => setResetTarget(null)}
              onConfirm={handleResetConfirm}
              title="Reset to Default Template?"
              description={`This will replace your custom ${resetTarget.roleName} skill with the default ${resetTarget.roleType.replace(/_/g, ' ')} template. All customizations will be lost.`}
              confirmLabel="Reset Skill"
              variant="destructive"
            />
          )}

          {/* Workspace skill remove confirmation */}
          {wsSkillToRemove && (
            <ConfirmActionDialog
              open={!!wsSkillToRemove}
              onCancel={() => setWsSkillToRemove(null)}
              onConfirm={handleWsRemoveConfirm}
              title={`Remove ${wsSkillToRemove.role_name} Workspace Skill?`}
              description={`This will permanently delete the ${wsSkillToRemove.role_name} workspace skill. Members will no longer inherit this skill. To revert, generate a new skill.`}
              confirmLabel="Remove Skill"
              variant="destructive"
            />
          )}

          {/* Unified Skill Generator Modal */}
          <SkillGeneratorModal
            open={generatorOpen}
            onOpenChange={setGeneratorOpen}
            defaultMode={generatorMode}
            showModeToggle={workspaceStore.isAdmin}
            workspaceId={workspaceId}
          />
        </TabsContent>

        {workspaceStore.isAdmin && (
          <TabsContent value="plugins">
            <PluginsTabContent
              workspaceId={workspaceId}
              addDialogOpen={addPluginDialogOpen}
              onAddDialogOpenChange={setAddPluginDialogOpen}
            />
          </TabsContent>
        )}

        {workspaceStore.isAdmin && (
          <TabsContent value="action-buttons">
            <ActionButtonsTabContent workspaceId={workspaceId} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
});
