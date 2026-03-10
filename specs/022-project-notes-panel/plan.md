# Implementation Plan: Project Notes Panel

**Branch**: `022-project-notes-panel` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-project-notes-panel/spec.md`
**Updated**: 2026-03-10 — Enhancement round: 6 UX improvements added

## Summary

The base `ProjectNotesPanel` component and `ProjectSidebar` integration are already implemented. This plan documents **6 enhancement features** to be added on top of the existing implementation. All changes remain **frontend-only** — no backend modifications required.

### Enhancement Features

1. **Workspace sidebar pinned notes: show project label** — Each pinned note in `sidebar.tsx` shows a muted project name badge after the note title when `note.projectId` is set.
2. **Project notes panel: remove Recent section, keep only Recent header** — The project panel already shows Recent notes; removing the `New Note` button from the project sidebar panel (it moves to workspace sidebar behavior).
3. **New Note uses TemplatePicker (T-018)** — Wire `TemplatePicker` into the "New Note" flow in `sidebar.tsx` (workspace sidebar) reusing the already-built `TemplatePicker` component from `018-mvp-note-first-complete`.
4. **New Note dialog includes project selector** — After confirming in `TemplatePicker`, a project selector step lets users assign the new note to a project (or root workspace).
5. **Note view breadcrumb shows project path** — `InlineNoteHeader` breadcrumb extends from `Notes > Title` to `Notes > [Project name] > Title` when `note.projectId` is set.
6. **Note options: Move to project/root** — `InlineNoteHeader` dropdown menu gains a "Move..." item that opens a project picker dialog to reassign `note.projectId`.

---

## Technical Context

**Language/Version**: TypeScript 5.x (strict mode)
**Primary Dependencies**: React 18, TanStack Query v5, MobX 6, Next.js 15 App Router, shadcn/ui, TailwindCSS
**Storage**: N/A (read-only from existing REST API; note move uses existing `useUpdateNote`)
**Testing**: Vitest + React Testing Library
**Target Platform**: Web (desktop sidebar, `md:` breakpoint and above)
**Constraints**: 700-line file limit per constitution; no new backend endpoints; no new backend migrations
**Scale/Scope**: 4 existing files modified + 1 new helper component

---

## Constitution Check

| Gate | Status | Notes |
|---|---|---|
| Frontend: React 18 + TypeScript strict | ✅ PASS | All enhancements use existing patterns |
| Frontend: TailwindCSS for styling | ✅ PASS | Reuses sidebar/panel CSS classes |
| Frontend: Feature-based MobX + TanStack Query | ✅ PASS | useProjects (TQ), useWorkspaceStore (MobX), useUpdateNote (TQ) |
| Code: Type check passes | ✅ PASS | New props are optional; existing Note.projectId is `string?` |
| Code: Lint passes | ✅ PASS | Will verify with `pnpm lint` |
| Code: No TODOs / mocks in production paths | ✅ PASS | Real API calls; real error states |
| Code: File size ≤ 700 lines | ✅ PASS | sidebar.tsx est. +25 lines; InlineNoteHeader +35 lines; new dialog ~60 lines |
| Security: Auth required for all API calls | ✅ PASS | `useUpdateNote` uses authenticated `apiClient` |
| Architecture: Layer boundaries respected | ✅ PASS | UI layer only |
| AI: Human-in-the-loop principle | ✅ N/A | No AI features in these enhancements |

**Complexity Tracking**: All 6 enhancements reuse existing hooks, components, and API patterns. No new abstractions introduced.

---

## Project Structure

### Source Code

```text
frontend/src/
├── components/
│   ├── layout/
│   │   └── sidebar.tsx                        # MODIFY: project label on pinned, TemplatePicker, project selector
│   ├── editor/
│   │   ├── InlineNoteHeader.tsx               # MODIFY: breadcrumb + "Move..." option
│   │   └── MoveNoteDialog.tsx                 # CREATE: project picker dialog (~60 lines)
│   └── projects/
│       └── ProjectNotesPanel.tsx              # MODIFY: remove "New Note" button
```

---

## Implementation Approach

### Enhancement 1: Workspace sidebar — project label on pinned notes

**File**: `frontend/src/components/layout/sidebar.tsx`
**Scope**: `pinnedNotes` useMemo + render

Add `projectId` to the mapped note objects from `noteStore.pinnedNotes`:

```ts
// sidebar.tsx pinnedNotes useMemo (~line 372)
const pinnedNotes = useMemo(() => {
  return noteStore.pinnedNotes.slice(0, 5).map((note) => ({
    id: note.id,
    title: note.title,
    projectId: note.projectId,           // NEW
    href: `/${workspaceSlug}/notes/${note.id}`,
  }));
}, [noteStore.pinnedNotes, workspaceSlug]);
```

Fetch project names via `useProjects` (already cached from workspace load):

```ts
const { data: projectsData } = useProjects({ workspaceId, enabled: !!workspaceId });
const projectMap = useMemo(() => {
  const map: Record<string, string> = {};
  (projectsData?.items ?? []).forEach((p) => { map[p.id] = p.name; });
  return map;
}, [projectsData]);
```

Render the project label after each pinned note title (only when `note.projectId` is set):

```tsx
<Link href={note.href} ...>
  <FileText className="h-3 w-3 text-muted-foreground" />
  <span className="truncate flex-1">{note.title}</span>
  {note.projectId && projectMap[note.projectId] && (
    <span className="ml-auto shrink-0 text-[10px] text-muted-foreground/60 truncate max-w-[60px]">
      {projectMap[note.projectId]}
    </span>
  )}
</Link>
```

**Key references**:
- `sidebar.tsx` lines 372–378 (pinnedNotes useMemo)
- `sidebar.tsx` lines 539–554 (pinned notes render)
- `useProjects` hook: `frontend/src/features/projects/hooks/useProjects.ts`
- `Note.projectId?: string` in `frontend/src/types/note.ts` line 28

---

### Enhancement 2: Project notes panel — remove "New Note" button

**File**: `frontend/src/components/projects/ProjectNotesPanel.tsx`

The project sidebar's `ProjectNotesPanel` currently shows a "New Note" button (lines 167–183). Per the enhancement spec, the project panel should only display the Recent note section without a "New Note" button (the button belongs to the workspace-level sidebar flow enhanced in Enhancement 3).

Remove:
- The `useCreateNote` hook import and usage (lines 49–53)
- The `handleCreateNote` callback (lines 56–58)
- The "New Note" button render block (lines 167–183)
- The `canCreateContent` check (line 23) — no longer needed here
- The `useWorkspaceStore` import if no longer used (line 11)
- The `Plus` and `Loader2` icon imports (line 6)

**Result**: Panel is read-only list of pinned + recent notes only.

---

### Enhancement 3: Wire TemplatePicker into workspace sidebar "New Note"

**File**: `frontend/src/components/layout/sidebar.tsx`
**Reference**: T-018 from `specs/018-mvp-note-first-complete/tasks.md`

The existing `handleNewNote` handler (line 391) calls `createNote.mutate(createNoteDefaults())` directly, bypassing the already-built `TemplatePicker` component.

**Implementation**:

1. Add state:
```ts
const [showTemplatePicker, setShowTemplatePicker] = useState(false);
```

2. Replace `handleNewNote`:
```ts
const handleNewNote = useCallback(() => {
  setShowTemplatePicker(true);
}, []);
```

3. Handle template confirm:
```ts
const handleTemplateConfirm = useCallback((template: NoteTemplate | null) => {
  setShowTemplatePicker(false);
  createNote.mutate({
    title: template ? `New ${template.name} Note` : 'Untitled',
    content: template?.content ?? { type: 'doc', content: [{ type: 'paragraph' }] },
  });
}, [createNote]);
```

4. Render `TemplatePicker` conditionally (renders as a modal overlay over the entire page):
```tsx
{showTemplatePicker && (
  <TemplatePicker
    workspaceId={workspaceId}
    isAdmin={workspaceStore.currentUserRole === 'owner' || workspaceStore.currentUserRole === 'admin'}
    onConfirm={handleTemplateConfirm}
    onClose={() => setShowTemplatePicker(false)}
  />
)}
```

**Imports to add**:
```ts
import { TemplatePicker } from '@/features/notes/components/TemplatePicker';
import type { NoteTemplate } from '@/services/api/templates';
```

**Key references**:
- `TemplatePicker` props: `frontend/src/features/notes/components/TemplatePicker.tsx` lines 35–41
- `sidebar.tsx` lines 391–393 (`handleNewNote`)
- `sidebar.tsx` lines 597–606 (New Note button)

---

### Enhancement 4: New Note dialog includes project selector

**File**: `frontend/src/components/layout/sidebar.tsx`

After the user confirms a template in `TemplatePicker`, show a second step that lets them assign the new note to a project or leave it at root workspace level.

**Implementation**:

Add a second modal state and a `pendingTemplate` state:

```ts
const [pendingTemplate, setPendingTemplate] = useState<NoteTemplate | null | undefined>(undefined);
const [showProjectPicker, setShowProjectPicker] = useState(false);
```

Update `handleTemplateConfirm` to stage the template then open project picker:
```ts
const handleTemplateConfirm = useCallback((template: NoteTemplate | null) => {
  setShowTemplatePicker(false);
  setPendingTemplate(template);
  setShowProjectPicker(true);
}, []);
```

Handle project selection:
```ts
const handleProjectSelect = useCallback((projectId: string | null) => {
  setShowProjectPicker(false);
  const template = pendingTemplate;
  setPendingTemplate(undefined);
  createNote.mutate({
    title: template ? `New ${template.name} Note` : 'Untitled',
    content: template?.content ?? { type: 'doc', content: [{ type: 'paragraph' }] },
    ...(projectId ? { projectId } : {}),
  });
}, [pendingTemplate, createNote]);
```

The project picker is a simple inline dialog using existing shadcn/ui primitives:

```tsx
{showProjectPicker && (
  <ProjectPickerDialog
    workspaceId={workspaceId}
    onSelect={handleProjectSelect}
    onClose={() => { setShowProjectPicker(false); setPendingTemplate(undefined); }}
  />
)}
```

`ProjectPickerDialog` is a new small component (~60 lines) — see separate section below.

---

### Enhancement 4b: Create `MoveNoteDialog.tsx` (shared by Enhancement 4 and 6)

**File**: `frontend/src/components/editor/MoveNoteDialog.tsx` (new, ~80 lines)

A reusable project picker dialog used by both the "New Note" project selection step and the "Move..." note option.

```tsx
interface MoveNoteDialogProps {
  workspaceId: string;
  /** Current projectId (for Move... — pre-selects current project). null = root. */
  currentProjectId?: string | null;
  /** Label for the confirm button */
  confirmLabel?: string;
  onSelect: (projectId: string | null) => void;
  onClose: () => void;
}
```

Internal structure:
- Fetches projects via `useProjects({ workspaceId })`
- Lists projects as selectable rows
- "No project (root)" option always first
- Confirm button calls `onSelect(selectedProjectId)`
- Cancel calls `onClose()`

Render as a modal overlay (same pattern as `TemplatePicker`).

**Key references**:
- `useProjects` hook: `frontend/src/features/projects/hooks/useProjects.ts`
- `TemplatePicker` modal pattern: `frontend/src/features/notes/components/TemplatePicker.tsx` lines 285–300

---

### Enhancement 5: Note breadcrumb shows project path

**File**: `frontend/src/components/editor/InlineNoteHeader.tsx`

**Current breadcrumb** (lines 233–243):
```
Notes (link) > [Title]
```

**Target breadcrumb**:
```
Notes (link) > [Project name] (link) > [Title]
```

**Changes**:

1. Add `projectId?: string` and `workspaceId?: string` to `InlineNoteHeaderProps`:
```ts
/** Project ID — when set, renders project name in breadcrumb */
projectId?: string;
/** Workspace ID — needed to build project link href */
workspaceId?: string;
```

2. Inside the component, fetch project data conditionally:
```ts
const { data: project } = useProject({
  projectId: projectId ?? '',
  enabled: !!projectId,
});
```

3. Update breadcrumb render:
```tsx
{/* Breadcrumb */}
<Link href={`/${workspaceSlug}/notes`} ...>
  <FileText ... />
  <span className="hidden sm:inline">Notes</span>
</Link>
<ChevronRight className="h-3 w-3 flex-shrink-0" />
{project && (
  <>
    <Link
      href={`/${workspaceSlug}/projects/${projectId}/overview`}
      className="hover:text-foreground transition-colors hidden sm:inline truncate max-w-[80px]"
    >
      {project.name}
    </Link>
    <ChevronRight className="h-3 w-3 flex-shrink-0 hidden sm:block" />
  </>
)}
<span className="text-foreground truncate max-w-[80px] sm:max-w-[120px] md:max-w-[180px] lg:max-w-[240px] font-medium">
  {title || 'Untitled'}
</span>
```

4. Pass through `projectId` and `workspaceId` from `NoteCanvasLayout.tsx` (already receives `projectId` as prop; needs to also pass `workspaceId`):
```tsx
<InlineNoteHeader
  ...
  projectId={projectId}
  workspaceId={workspaceId}
/>
```

**Key references**:
- `InlineNoteHeader` props: `InlineNoteHeader.tsx` lines 94–127
- `InlineNoteHeader` render: `InlineNoteHeader.tsx` lines 232–243
- `NoteCanvasLayout.tsx` lines 184–200 (where InlineNoteHeader is rendered, `projectId` already in scope)
- `useProject` hook: `frontend/src/features/projects/hooks/useProject.ts`

---

### Enhancement 6: Note options — "Move..." action

**File**: `frontend/src/components/editor/InlineNoteHeader.tsx`

Add a "Move..." option to the DropdownMenuContent that opens `MoveNoteDialog`.

**Changes**:

1. Add `onMove?: (projectId: string | null) => void` to `InlineNoteHeaderProps`.

2. Add state for the dialog:
```ts
const [showMoveDialog, setShowMoveDialog] = useState(false);
```

3. Add `MoveNoteDialog` import:
```ts
import { MoveNoteDialog } from './MoveNoteDialog';
```

4. Add menu item before the separator before Delete:
```tsx
{onMove && (
  <DropdownMenuItem onClick={() => setShowMoveDialog(true)}>
    <FolderInput className="mr-2 h-4 w-4" />
    Move...
  </DropdownMenuItem>
)}
```

5. Add `FolderInput` to lucide imports.

6. Render dialog:
```tsx
{showMoveDialog && workspaceId && (
  <MoveNoteDialog
    workspaceId={workspaceId}
    currentProjectId={projectId ?? null}
    confirmLabel="Move Note"
    onSelect={(newProjectId) => {
      setShowMoveDialog(false);
      onMove?.(newProjectId);
    }}
    onClose={() => setShowMoveDialog(false)}
  />
)}
```

7. In `NoteDetailPage` (`notes/[noteId]/page.tsx`), wire `handleMove`:
```ts
const handleMove = useCallback((newProjectId: string | null) => {
  updateNote.mutate({ projectId: newProjectId ?? undefined });
}, [updateNote]);
```

Pass to `NoteCanvas`:
```tsx
onMove={handleMove}
```

8. In `NoteCanvasLayout.tsx`, forward `onMove` through to `InlineNoteHeader`:
- Add `onMove?: (projectId: string | null) => void` to `NoteCanvasProps`
- Pass it down to `InlineNoteHeader`

**Key references**:
- `InlineNoteHeader` dropdown: `InlineNoteHeader.tsx` lines 344–406
- `NoteDetailPage` handlers: `notes/[noteId]/page.tsx` lines 276–309
- `useUpdateNote` supports `projectId`: `UpdateNoteData.projectId?: string` in `types/note.ts` line 116
- `NoteCanvasLayout` props: `NoteCanvasLayout.tsx` lines 84–106

---

## Updated Data Model

No new backend models. All data is served by existing endpoints.

**New prop flows**:

| Prop | From | To | Purpose |
|---|---|---|---|
| `note.projectId` | NoteStore | sidebar.tsx pinnedNotes | Show project label |
| `projectId` | NoteDetailPage | NoteCanvasLayout → InlineNoteHeader | Breadcrumb + Move |
| `workspaceId` | NoteDetailPage | NoteCanvasLayout → InlineNoteHeader | Breadcrumb link + MoveNoteDialog |
| `onMove` | NoteDetailPage | NoteCanvasLayout → InlineNoteHeader | Move note callback |

---

## API Calls (all existing)

| Action | Endpoint |
|---|---|
| Fetch projects for label/picker | `GET /api/v1/workspaces/{id}/projects` |
| Fetch project for breadcrumb | `GET /api/v1/projects/{id}` |
| Create note with projectId | `POST /api/v1/workspaces/{id}/notes` |
| Move note (update projectId) | `PATCH /api/v1/workspaces/{id}/notes/{noteId}` |

---

## Updated Quickstart Scenarios

### Scenario 6: Pinned note with project label in workspace sidebar
```
Setup: Workspace has a note "Sprint Retro" pinned, linked to project "Backend"
Steps:
  1. Open workspace sidebar
  2. PINNED section shows "Sprint Retro    Backend"
Verify:
  - projectId resolved to project name via useProjects (cached)
  - Label appears muted after note title
```

### Scenario 7: New Note via TemplatePicker + project selection
```
Steps:
  1. Click "New Note" in workspace sidebar
  2. TemplatePicker modal opens (4 SDLC templates + blank)
  3. Select "Design Review", click confirm
  4. MoveNoteDialog opens: "Add to project?"
  5. Select project "Frontend" or "No project (root)"
  6. Note created with templateId and optional projectId
  7. Navigate to note editor
Verify:
  - Note.projectId set (or null for root)
  - Template content applied to new note
```

### Scenario 8: Note breadcrumb with project
```
Setup: Note "Auth Design" linked to project "Backend"
Steps:
  1. Open note
  2. Header breadcrumb shows: "Notes > Backend > Auth Design"
Verify:
  - "Backend" is a link to /{workspaceSlug}/projects/{projectId}/overview
  - Breadcrumb hides project segment on mobile (hidden sm:inline)
```

### Scenario 9: Move note to different project
```
Steps:
  1. Open note currently in project "Frontend"
  2. Click "..." options menu
  3. Click "Move..."
  4. MoveNoteDialog shows all projects; "Frontend" pre-selected
  5. Select "Backend" and confirm
  6. PATCH /notes/{id} called with projectId = "Backend" id
  7. Breadcrumb updates to "Notes > Backend > [title]"
Verify:
  - updateNote mutation fires with new projectId
  - TanStack Query cache invalidated
```

---

## Constitution Check (Post-Design)

| Gate | Status | Notes |
|---|---|---|
| File size ≤ 700 lines | ✅ PASS | sidebar.tsx: +~50 lines; InlineNoteHeader: +~35 lines; MoveNoteDialog: new ~80-line file |
| No duplicate API calls | ✅ PASS | `useProjects` is cached; `useProject` for breadcrumb uses existing cache key |
| Type safety | ✅ PASS | All new props are optional; no `any` types |
| No new backend | ✅ PASS | All endpoints already exist |

---

## Key Reference Patterns

| Pattern | Source |
|---|---|
| Pinned notes in sidebar | `sidebar.tsx` lines 372–554 |
| `useProjects` | `frontend/src/features/projects/hooks/useProjects.ts` |
| `useProject` | `frontend/src/features/projects/hooks/useProject.ts` |
| TemplatePicker props/usage | `features/notes/components/TemplatePicker.tsx` lines 35–41, 285–300 |
| InlineNoteHeader breadcrumb | `components/editor/InlineNoteHeader.tsx` lines 232–243 |
| InlineNoteHeader dropdown | `components/editor/InlineNoteHeader.tsx` lines 344–406 |
| useUpdateNote with projectId | `types/note.ts` line 116; `features/notes/hooks/useUpdateNote.ts` |
| NoteDetailPage handlers | `app/.../notes/[noteId]/page.tsx` lines 276–309 |
| NoteCanvasLayout props | `components/editor/NoteCanvasLayout.tsx` lines 84–106 |
| MobX workspace role check | `sidebar.tsx` line 288; `workspaceStore.currentUserRole` |
