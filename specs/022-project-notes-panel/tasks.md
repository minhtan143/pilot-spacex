# Tasks: Project Notes Panel (022)

**Source**: `/specs/022-project-notes-panel/`
**Branch**: `022-project-notes-panel`
**Updated**: 2026-03-10 — v2: Enhancement features T022–T044 added
**Required**: plan.md ✅, spec.md ✅
**Optional**: research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

---

## Task Format

```
- [ ] [ID] [P?] [Story?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies) |
| `[USn]` | User story label (Phase 3+ only) |

---

## Phase 1: Setup (Base Feature — COMPLETE)

Verify reference patterns and confirm the working environment before writing any code.
No new infrastructure needed — this is a frontend-only change to an existing Next.js app.

- [x] T001 Read `frontend/src/components/layout/sidebar.tsx` lines 372–544 to capture the exact CSS class names and structure used for PINNED/RECENT note sections (visual reference for FR-008)
- [x] T002 Read `frontend/src/components/projects/ProjectSidebar.tsx` in full to understand mount point and line count before modification
- [x] T003 [P] Read `frontend/src/features/notes/hooks/useNotes.ts` to confirm `useNotes` signature accepts `projectId`, `isPinned`, and `pageSize` parameters
- [x] T004 [P] Read `frontend/src/features/notes/hooks/useCreateNote.ts` to confirm `useCreateNote` mutation accepts `projectId` in the data payload

**Checkpoint**: Reference patterns confirmed ✅

---

## Phase 2: Foundational (Skipped)

No new shared infrastructure required. All hooks, types, and API services already exist.

**Skipped**: `useNotes`, `useCreateNote`, `useWorkspaceStore`, `Note` type, `Project` type, and all API services are pre-existing.

---

## Phase 3: User Story 1 — Browse Project Notes from Sidebar (P1) 🎯 MVP — COMPLETE

**Goal**: Display Pinned and Recent project-scoped notes in the project sidebar desktop panel.
**Verify**: Navigate to any project with notes → sidebar shows Pinned/Recent sections with working links.

- [x] T005 [US1] Create `frontend/src/components/projects/ProjectNotesPanel.tsx` with full component skeleton, two `useNotes` calls (pinned + recent), props interface `{ project, workspaceSlug, workspaceId }`
- [x] T006 [US1] Implement loading state in `ProjectNotesPanel.tsx`: 3 `<Skeleton>` rows when either query `isLoading`
- [x] T007 [US1] Implement error state in `ProjectNotesPanel.tsx`: inline "Failed to load notes" text (non-crashing)
- [x] T008 [US1] Implement "Pinned" sub-section in `ProjectNotesPanel.tsx`: section header with `<Pin>` icon; up to 5 note rows as `<Link>` with `<FileText>` icon and truncated title
- [x] T009 [US1] Implement "Recent" sub-section in `ProjectNotesPanel.tsx`: same structure with `<Clock>` header icon; note rows exclude pinned notes
- [x] T010 [US1] Implement empty state in `ProjectNotesPanel.tsx`: "No notes yet" message when both lists empty
- [x] T011 [US1] Mount `ProjectNotesPanel` in `frontend/src/components/projects/ProjectSidebar.tsx` after `</nav>` tag inside `<aside>` desktop block with `<Separator />`

**Checkpoint**: US1 complete ✅

---

## Phase 4: User Story 2 — Create Project-Linked Note from Panel (P2) — COMPLETE

**Goal**: "New Note" button in the panel creates a project-linked note and navigates to the editor. Hidden for guests.
**Verify**: Click "New Note" → new note created → navigated to editor → note has correct `projectId`.

- [x] T012 [US2] Add `useCreateNote`, `useWorkspaceStore`, `useRouter` to `ProjectNotesPanel.tsx`; add mutation and `canCreateContent` check
- [x] T013 [US2] Add "New Note" `<Button>` to `ProjectNotesPanel.tsx`; hide for guest role
- [x] T014 [US2] Implement `handleCreateNote` in `ProjectNotesPanel.tsx`: mutates with `{ title: 'Untitled', projectId: project.id }`; navigates on success

**Checkpoint**: US2 complete ✅

---

## Phase 5: User Story 3 — Visual Polish and "View all" (P3) — COMPLETE

**Goal**: "View all →" links when total > 5; exact visual parity with workspace sidebar.
**Verify**: Side-by-side comparison shows identical styles; "View all" link appears when more than 5 notes.

- [x] T015 [P] [US3] Add "View all" link to Pinned sub-section in `ProjectNotesPanel.tsx` (when `pinnedData?.total > 5`)
- [x] T016 [P] [US3] Add "View all" link to Recent sub-section in `ProjectNotesPanel.tsx` (when `recentData?.total > 5`)
- [x] T017 [US3] Audit `ProjectNotesPanel.tsx` for visual parity with `sidebar.tsx` lines 488–544

**Checkpoint**: US3 complete ✅

---

## Phase 6: Enhancement 1 — Workspace Sidebar Pinned Notes: Project Label (P1)

**Goal**: Each pinned note in the workspace sidebar `<aside>` PINNED section shows a muted project name label after the note title when `note.projectId` is set (FR-011).

**Verify**: Open workspace sidebar → PINNED section → note linked to a project shows `"[Note title]    [Project name]"` with project name muted/truncated on the right.

### Implementation

- [x] T022 [ENH1] In `frontend/src/components/layout/sidebar.tsx`, add `useProjects` import from `@/features/projects/hooks`; add `useProjects({ workspaceId, enabled: !!workspaceId })` call in the `Sidebar` component body; derive `projectMap: Record<string, string>` via `useMemo` mapping `project.id → project.name` from `projectsData?.items ?? []`
- [x] T023 [ENH1] In `frontend/src/components/layout/sidebar.tsx`, extend the `pinnedNotes` useMemo (around line 372) to also map `projectId: note.projectId` alongside `id`, `title`, `href` — change the mapped type from `{ id, title, href }` to `{ id, title, projectId: string | undefined, href }`
- [x] T024 [ENH1] In `frontend/src/components/layout/sidebar.tsx`, update the pinned notes render block (around line 546–554) to show a project label: inside the `<Link>` row, after `<span className="truncate">{note.title}</span>`, add `{note.projectId && projectMap[note.projectId] && (<span className="ml-auto shrink-0 text-[10px] text-muted-foreground/60 truncate max-w-[60px]">{projectMap[note.projectId]}</span>)}`

**Checkpoint**: Workspace sidebar pinned notes show muted project name badge when note has `projectId`. Notes without `projectId` show no label.

---

## Phase 7: Enhancement 2 — Project Panel: Remove "New Note" Button (P1)

**Goal**: The project sidebar `ProjectNotesPanel` shows only Pinned and Recent lists — no "New Note" button (FR-012). The workspace sidebar "New Note" (enhanced in E3/E4) is the creation entry point.

**Verify**: Open project sidebar notes panel → no "New Note" button visible for any user role.

### Implementation

- [x] T025 [ENH2] In `frontend/src/components/projects/ProjectNotesPanel.tsx`, remove the `useCreateNote` import and its call (the `createNote` mutation); remove the `useWorkspaceStore` import (no longer needed); remove the `canCreateContent` const; remove the `handleCreateNote` useCallback; remove the `Plus` and `Loader2` lucide icon imports
- [x] T026 [ENH2] In `frontend/src/components/projects/ProjectNotesPanel.tsx`, remove the "New Note" button `<Button>` render block (the `{canCreateContent && (<Button ...>)}` block at the bottom of the return); ensure the component still closes cleanly

**Checkpoint**: `ProjectNotesPanel` renders only note lists — no creation button, no guest check needed.

---

## Phase 8: Enhancement 3 — Wire TemplatePicker into Workspace Sidebar "New Note" (P2)

**Goal**: Clicking "New Note" in the workspace sidebar opens the `TemplatePicker` modal (4 SDLC templates + blank) before creating a note, reusing the T-018 component from feature 018 (FR-013).

**Verify**: Click workspace sidebar "New Note" → `TemplatePicker` modal opens → selecting a template and confirming creates a note with that template's content → navigates to note editor.

### Implementation

- [x] T027 [ENH3] In `frontend/src/components/layout/sidebar.tsx`, add imports: `import { TemplatePicker } from '@/features/notes/components/TemplatePicker'` and `import type { NoteTemplate } from '@/services/api/templates'`
- [x] T028 [ENH3] In `frontend/src/components/layout/sidebar.tsx`, in the `Sidebar` component body, add state: `const [showTemplatePicker, setShowTemplatePicker] = useState(false)`; replace the existing `handleNewNote` callback body from `createNote.mutate(createNoteDefaults())` to `setShowTemplatePicker(true)`
- [x] T029 [ENH3] In `frontend/src/components/layout/sidebar.tsx`, add `handleTemplateConfirm` callback: `(template: NoteTemplate | null) => { setShowTemplatePicker(false); setPendingTemplate(template); setShowProjectPicker(true); }` — note: `setPendingTemplate` and `setShowProjectPicker` are added in T031 (E4); wire the close handler: `onClose={() => setShowTemplatePicker(false)}`
- [x] T030 [ENH3] In `frontend/src/components/layout/sidebar.tsx`, render `TemplatePicker` conditionally inside the component return (outside the `<div className="flex h-full flex-col">`, just before the closing JSX fragment): `{showTemplatePicker && (<TemplatePicker workspaceId={workspaceId} isAdmin={workspaceStore.currentUserRole === 'owner' || workspaceStore.currentUserRole === 'admin'} onConfirm={handleTemplateConfirm} onClose={() => setShowTemplatePicker(false)} />)}`

**Checkpoint**: Workspace sidebar "New Note" opens TemplatePicker modal. Closing without confirming cancels without creating a note.

---

## Phase 9: Enhancement 4 — New Note Project Selector Step (P2)

**Goal**: After template selection, show a project picker (`MoveNoteDialog`) so users can assign the new note to a project or root workspace (FR-014).

**Verify**: Click "New Note" → TemplatePicker → confirm template → project picker appears → selecting "No project" or a project → note created with correct `projectId`.

### Implementation

- [x] T031 [P] [ENH4] Create `frontend/src/components/editor/MoveNoteDialog.tsx` (~80 lines): props `{ workspaceId: string, currentProjectId?: string | null, confirmLabel?: string, onSelect: (projectId: string | null) => void, onClose: () => void }`; fetch projects via `useProjects({ workspaceId })`; render as a modal overlay (same pattern as `TemplatePicker` — fixed inset-0, backdrop-blur-sm); list projects as selectable rows; include "No project (root)" option as first item; confirm button calls `onSelect(selectedId)`; cancel calls `onClose()`; pre-select `currentProjectId` if provided
- [x] T032 [ENH4] In `frontend/src/components/layout/sidebar.tsx`, add `MoveNoteDialog` import from `@/components/editor/MoveNoteDialog`; add state: `const [pendingTemplate, setPendingTemplate] = useState<NoteTemplate | null | undefined>(undefined)` and `const [showProjectPicker, setShowProjectPicker] = useState(false)`
- [x] T033 [ENH4] In `frontend/src/components/layout/sidebar.tsx`, add `handleProjectSelect` callback: `(projectId: string | null) => { setShowProjectPicker(false); const template = pendingTemplate; setPendingTemplate(undefined); createNote.mutate({ title: template ? \`New ${template.name} Note\` : 'Untitled', content: template?.content ?? createNoteDefaults().content, ...(projectId ? { projectId } : {}) }); }`
- [x] T034 [ENH4] In `frontend/src/components/layout/sidebar.tsx`, render `MoveNoteDialog` conditionally: `{showProjectPicker && (<MoveNoteDialog workspaceId={workspaceId} onSelect={handleProjectSelect} onClose={() => { setShowProjectPicker(false); setPendingTemplate(undefined); }} />)}`

**Checkpoint**: Full New Note flow: click button → TemplatePicker → project selector → note created with both template content and `projectId` (or null for root).

---

## Phase 10: Enhancement 5 — Note View Breadcrumb Shows Project Path (P2)

**Goal**: The note header breadcrumb displays `Notes > [Project name] > [Note title]` when the note has a `projectId`; project name links to the project overview page (FR-015).

**Verify**: Open a note linked to a project → breadcrumb shows three segments with project name as clickable link → note without `projectId` shows two-segment breadcrumb `Notes > [title]`.

### Implementation

- [x] T035 [ENH5] In `frontend/src/components/editor/InlineNoteHeader.tsx`, add `projectId?: string` and `workspaceId?: string` to the `InlineNoteHeaderProps` interface; add `useProject` import from `@/features/projects/hooks`; inside the component, add: `const { data: project } = useProject({ projectId: projectId ?? '', enabled: !!projectId })`
- [x] T036 [ENH5] In `frontend/src/components/editor/InlineNoteHeader.tsx`, update the breadcrumb render section (after the `<Link href="/{workspaceSlug}/notes">` notes link, before the note title `<span>`): insert the project segment conditionally: `{project && (<><ChevronRight className="h-3 w-3 flex-shrink-0" /><Link href={\`/${workspaceSlug}/projects/${projectId}/overview\`} className="hover:text-foreground transition-colors hidden sm:inline truncate max-w-[80px]">{project.name}</Link></>)}`; keep the existing `<ChevronRight>` before the title
- [x] T037 [ENH5] In `frontend/src/components/editor/NoteCanvasLayout.tsx`, update the `<InlineNoteHeader>` render call (around line 195) to pass `projectId={projectId}` and `workspaceId={workspaceId}` — both are already in scope in `NoteCanvasLayout` props

**Checkpoint**: Note breadcrumb shows `Notes > [Project] > [Title]` for project-linked notes; project name is a link to project overview; breadcrumb hides project on mobile.

---

## Phase 11: Enhancement 6 — Note Options: "Move..." Action (P2)

**Goal**: The note `...` options dropdown gains a "Move..." item that opens `MoveNoteDialog` to reassign the note to a different project or root workspace (FR-016).

**Verify**: Open note → click `...` → click "Move..." → `MoveNoteDialog` opens with current project pre-selected → selecting new project patches the note → breadcrumb updates.

### Implementation

- [x] T038 [ENH6] In `frontend/src/components/editor/InlineNoteHeader.tsx`, add `onMove?: (projectId: string | null) => void` to `InlineNoteHeaderProps`; add `FolderInput` to lucide imports; add state `const [showMoveDialog, setShowMoveDialog] = useState(false)`; add `MoveNoteDialog` import from `./MoveNoteDialog`
- [x] T039 [ENH6] In `frontend/src/components/editor/InlineNoteHeader.tsx`, in the `<DropdownMenuContent>` block (around line 356), add before the `<DropdownMenuSeparator />` before Delete: `{onMove && (<DropdownMenuItem onClick={() => setShowMoveDialog(true)}><FolderInput className="mr-2 h-4 w-4" />Move...</DropdownMenuItem>)}`
- [x] T040 [ENH6] In `frontend/src/components/editor/InlineNoteHeader.tsx`, render `MoveNoteDialog` conditionally at the end of the component return (after the delete confirm `<Dialog>`): `{showMoveDialog && workspaceId && (<MoveNoteDialog workspaceId={workspaceId} currentProjectId={projectId ?? null} confirmLabel="Move Note" onSelect={(newProjectId) => { setShowMoveDialog(false); onMove?.(newProjectId); }} onClose={() => setShowMoveDialog(false)} />)}`
- [x] T041 [ENH6] In `frontend/src/components/editor/NoteCanvasLayout.tsx`, add `onMove?: (projectId: string | null) => void` to `NoteCanvasProps` (in `NoteCanvasEditor.tsx`); destructure `onMove` in `NoteCanvasLayout`; pass `onMove={onMove}` to `<InlineNoteHeader>`
- [x] T042 [ENH6] In `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx`, add `handleMove` callback: `const handleMove = useCallback((newProjectId: string | null) => { updateNote.mutate({ projectId: newProjectId ?? undefined }); }, [updateNote])`; pass `onMove={handleMove}` to the `<NoteCanvas>` component call

**Checkpoint**: "Move..." action in note options opens project picker; selecting a project (or "No project") patches the note and the breadcrumb reflects the new project.

---

## Phase 12: Polish & Validation

Cross-cutting concerns after all enhancements complete.

- [x] T043 [P] Run `cd frontend && pnpm type-check` and fix all TypeScript errors across modified files: `sidebar.tsx`, `ProjectNotesPanel.tsx`, `InlineNoteHeader.tsx`, `NoteCanvasLayout.tsx`, `NoteCanvasEditor.tsx`, `notes/[noteId]/page.tsx`, and new `MoveNoteDialog.tsx`
- [x] T044 [P] Run `cd frontend && pnpm lint` and fix all ESLint errors across the same file set

---

## Dependencies

### Phase Order

```
Phase 1–5 (Base Feature) — COMPLETE
  │
  ├── Phase 6 (ENH1: workspace sidebar project label) — independent, starts immediately
  ├── Phase 7 (ENH2: remove project panel New Note) — independent, starts immediately
  │
  ├── Phase 8 (ENH3: TemplatePicker wiring)
  │     └── Phase 9 (ENH4: project selector step) — depends on ENH3 state/handlers
  │
  ├── Phase 10 (ENH5: breadcrumb) — independent; T037 modifies NoteCanvasLayout
  │
  └── Phase 11 (ENH6: Move... option)
        ├── T031 (MoveNoteDialog) — created in ENH4 Phase 9; must exist before T038–T042
        ├── T038–T040 depend on MoveNoteDialog (T031)
        ├── T041 depends on T035–T037 (NoteCanvasProps already updated)
        └── T042 depends on T041
          └── Phase 12 (Polish) — runs after all enhancements
```

### Cross-task Dependencies

| Task | Depends On | Reason |
|---|---|---|
| T023 | T022 | Uses `projectMap` from T022 |
| T024 | T022, T023 | Renders from `projectMap` and extended `pinnedNotes` |
| T029 | T031 (scheduled) | References `setPendingTemplate`/`setShowProjectPicker` added in T032 |
| T032 | T027 | Imports TemplatePicker types |
| T033 | T032 | Uses `pendingTemplate` state |
| T034 | T031, T033 | Renders `MoveNoteDialog` with `handleProjectSelect` |
| T036 | T035 | Uses `project` data fetched in T035 |
| T037 | T035, T036 | Passes props to updated InlineNoteHeader |
| T038 | T031 | Imports `MoveNoteDialog` |
| T039 | T038 | Adds to DropdownMenuContent after state added |
| T040 | T038, T031 | Renders MoveNoteDialog with state from T038 |
| T041 | T035 | `NoteCanvasProps` already updated; adds `onMove` to same interface |
| T042 | T041 | Passes `onMove` to NoteCanvas which now accepts it |
| T043, T044 | All T022–T042 | Final quality gate |

### Parallel Opportunities

Tasks marked `[P]` within the same phase can run concurrently:

```
Phase 6:   T022 → T023 → T024  (sequential — build on each other)
Phase 7:   T025 → T026         (sequential — T026 removes code added in T025 setup)

Phase 8+9: T027 → T028 → T029 → T030 (sequential in sidebar.tsx)
           T031 [P] — new file, no deps — can run in parallel with T027–T030

Phase 10:  T035 → T036 → T037 (sequential in InlineNoteHeader → NoteCanvasLayout)

Phase 11:  T038 → T039 → T040 (sequential in InlineNoteHeader)
           T041 → T042         (sequential in NoteCanvasLayout → NoteDetailPage)
           T038–T040 || T041–T042 (parallel — different files)

Phase 12:  T043 || T044        (independent tools)
```

---

## Implementation Strategy

### MVP Enhancement Order

Start with the two independent, highest-value enhancements:

```
ENH2 (T025–T026) — Remove project panel New Note button (quick cleanup)
ENH1 (T022–T024) — Project label on workspace sidebar pinned notes
ENH3+4 (T027–T034) — New Note with TemplatePicker + project selector (T031 first)
ENH5 (T035–T037) — Note breadcrumb
ENH6 (T038–T042) — Move... option (depends on T031 from ENH4)
Polish (T043–T044)
```

### Suggested Execution

```
Day 1:
  ENH2: T025 → T026  (fast — remove code from ProjectNotesPanel.tsx)
  ENH1: T022 → T023 → T024  (workspace sidebar project label)

Day 2:
  ENH4 prep: T031 (create MoveNoteDialog.tsx — shared by ENH4 and ENH6)
  ENH3: T027 → T028 → T029 → T030  (TemplatePicker wiring)
  ENH4: T032 → T033 → T034  (project selector step)

Day 3:
  ENH5: T035 → T036 → T037  (breadcrumb)
  ENH6: T038 → T039 → T040 || T041 → T042  (Move... option)
  Polish: T043 || T044
```

---

## Notes

- **Base feature (T001–T021)** is complete — `ProjectNotesPanel.tsx` and `ProjectSidebar.tsx` integration are already implemented
- **T031 (`MoveNoteDialog.tsx`)** is the critical shared component — create it before ENH6 (T038) and it doubles as the project selector for ENH4 (T034)
- **ENH2 reverses ENH from the base spec** — the project panel originally had a "New Note" button (T012–T014); these are now removed per the enhancement spec (FR-012)
- **`useProject` for breadcrumb** uses TanStack Query — data is typically pre-cached from the project context page; no extra API cost
- **`NoteTemplate.content`** — verify `NoteTemplate` type has `content?: JSONContent` before T033; check `frontend/src/services/api/templates.ts`
- **`updateNote` with `projectId: undefined`** — verify backend `PATCH /notes/{id}` treats omitted/undefined `projectId` as "remove project link"; if not, use `null` explicitly
