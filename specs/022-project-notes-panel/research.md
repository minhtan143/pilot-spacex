# Research: Project Notes Panel (022)

**Date**: 2026-03-10
**Updated**: 2026-03-10 — v2 enhancement research added
**Feature**: Project sidebar notes panel matching workspace sidebar UX

---

## Decision 1: Data Fetching Strategy

**Decision**: Use `useNotes` (TanStack Query, non-infinite) with `projectId` + `isPinned` filters — two separate calls: one for pinned notes, one for recent notes.

**Rationale**:
- The panel shows at most 5+5 items — no infinite scroll needed; `useInfiniteNotes` adds unnecessary overhead
- `useNotes` is already available and accepts `projectId` and `isPinned` filters
- Two separate queries map cleanly to the two sub-sections and allow independent loading states
- TanStack Query de-dupes and caches each query independently

**Alternatives considered**:
- Single query + client-side split: rejected — wastes bandwidth fetching 10 notes when 5 per sub-section suffice
- MobX `NoteStore`: rejected — workspace-scoped store, not project-aware; adding project filtering would couple stores incorrectly
- `useInfiniteNotes`: overkill for a sidebar panel with a hard cap of 5 items

---

## Decision 2: Component Location

**Decision**: Add a `ProjectNotesPanel` component at `frontend/src/components/projects/ProjectNotesPanel.tsx` and integrate it into `ProjectSidebar`.

**Rationale**:
- `ProjectSidebar` already lives at `frontend/src/components/projects/ProjectSidebar.tsx`
- Keeping the notes panel in the same `components/projects/` folder maintains cohesion
- A dedicated component keeps `ProjectSidebar` under the 700-line limit
- Mirrors how the workspace sidebar consumes note data: sidebar imports and renders the sub-list directly

**Alternatives considered**:
- Inline in `ProjectSidebar`: rejected — exceeds 700-line limit easily; harder to test
- Feature-level component under `features/notes/components/`: rejected — this panel is project-domain UI, not note-domain UI

---

## Decision 3: Permission Check

**Decision**: Read `canCreateContent` by calling `useWorkspaceStore()` inside `ProjectNotesPanel` and checking `currentUserRole !== 'guest'`.

**Rationale**:
- This is exactly the same pattern used in `ProjectSidebar`, `notes/page.tsx`, and `sidebar.tsx`
- `WorkspaceStore` is a singleton in `RootStore`; reading it from a child component is idiomatic

**Alternatives considered**:
- Pass `canCreateContent` as a prop from `ProjectSidebar`: viable but adds prop drilling for a value already accessible via hook

---

## Decision 4: "View all" Link Target

**Decision**: Link to `/{workspaceSlug}/notes?projectId={project.id}` — future-proofing the notes page filter.

**Rationale**:
- Notes page at `/(workspace)/[workspaceSlug]/notes` is the canonical notes list
- The URL-based filter param `projectId` is a natural extension of the existing `filterPinned` query state pattern already in the notes page
- No backend changes required for the link target

**Note**: The notes page currently does not parse `projectId` from URL params — that is a follow-on enhancement, not a blocker. The "View all" link still navigates to the notes page (correct intent); project pre-filtering can be added separately.

---

## Decision 5: Loading and Error States

**Decision**: Use a `Skeleton` (3 rows) during loading; render a simple inline `"Failed to load notes"` text on error. No full error boundary needed — this is a secondary sidebar panel.

**Rationale**:
- Matches minimal pattern used in other sidebar sections
- Failure of the notes panel must NOT crash the project layout
- Constitution §IV (Code Quality): no mocks in production paths — real error state required

---

## Resolved Clarifications (Base Feature)

All spec assumptions confirmed via codebase inspection:

| Assumption | Verification |
|---|---|
| `Note.projectId` exists | `types/note.ts` line 28: `projectId?: string` |
| API supports `projectId` filter | `workspace_notes.py` line 147: `project_id` query param |
| `useNotes` accepts `projectId` | `hooks/useNotes.ts` line 17: `projectId?: string` |
| `CreateNoteData.projectId` exists | `types/note.ts` line 109: `projectId?: string` |
| `WorkspaceStore.currentUserRole` accessible | `sidebar.tsx`, `notes/page.tsx` both use `workspaceStore.currentUserRole !== 'guest'` |

---

## Decision 6: Project label in workspace sidebar pinned notes

**Decision**: Use `useProjects({ workspaceId })` — already called elsewhere in the sidebar — to build a `projectMap: Record<string, string>` (id → name). Render label as a muted span after note title. Pull `note.projectId` from `noteStore.pinnedNotes` (type `Note` which has `projectId?: string`).

**Rationale**:
- `useProjects` is cached by TanStack Query; no extra API call cost
- No new data types needed
- `noteStore.pinnedNotes` returns `Note[]` which already has `projectId?: string`

**Alternatives considered**:
- Fetch project per-note with `useProject`: rejected — N+1 calls for pinned notes list
- Add projectName to NoteStore: rejected — over-engineering; project data already in TQ cache

---

## Decision 7: Project selector after TemplatePicker

**Decision**: Show `MoveNoteDialog` (new small component, also used for "Move...") as a second modal after `TemplatePicker` closes. Stage the selected template in local state until project is chosen.

**Rationale**:
- Separates two distinct concerns (template vs. project) into two focused modals
- Reuses the same dialog component for "Move..." feature — avoids duplicating project picker UI
- Matches the "single responsibility" principle for modal flows

**Alternatives considered**:
- Embed project selector inside TemplatePicker: rejected — TemplatePicker is focused; adding a step would violate SRP
- Combined single dialog with steps: more complex state machine; rejected for simplicity

---

## Decision 8: Note breadcrumb project segment

**Decision**: Add optional `projectId` and `workspaceId` props to `InlineNoteHeader`. Fetch project via `useProject({ projectId, enabled: !!projectId })`. Render project name as an inline link between "Notes" and note title. Hide project segment on mobile (`hidden sm:inline`) to prevent breadcrumb overflow.

**Rationale**:
- `useProject` is already cached; the note editor page already has `projectId` in scope
- Hiding on mobile matches existing responsive strategy in the breadcrumb (note title truncation)
- `workspaceId` is already available in `NoteCanvasLayout` via props

**Alternatives considered**:
- Pass `projectName` as prop instead of fetching: rejected — requires caller to already have the project name, adding coupling
- Render project in a separate component: rejected — breadcrumb is self-contained in InlineNoteHeader

---

## Decision 9: Move note — updateNote with projectId

**Decision**: Use existing `useUpdateNote` mutation with `{ projectId: newProjectId ?? undefined }` payload. Setting `projectId` to `undefined` removes the project link (moves note to root workspace).

**Rationale**:
- `UpdateNoteData.projectId?: string` already exists in `types/note.ts` line 116
- Backend `PATCH /notes/{id}` already handles `project_id` field
- No new API service code needed

**Alternatives considered**:
- Dedicated "move" endpoint: rejected — over-engineered for a simple field update


---

## Decision 1: Data Fetching Strategy

**Decision**: Use `useNotes` (TanStack Query, non-infinite) with `projectId` + `isPinned` filters — two separate calls: one for pinned notes, one for recent notes.

**Rationale**:
- The panel shows at most 5+5 items — no infinite scroll needed; `useInfiniteNotes` adds unnecessary overhead
- `useNotes` is already available and accepts `projectId` and `isPinned` filters
- Two separate queries map cleanly to the two sub-sections and allow independent loading states
- TanStack Query de-dupes and caches each query independently

**Alternatives considered**:
- Single query + client-side split: rejected — wastes bandwidth fetching 10 notes when 5 per sub-section suffice
- MobX `NoteStore`: rejected — workspace-scoped store, not project-aware; adding project filtering would couple stores incorrectly
- `useInfiniteNotes`: overkill for a sidebar panel with a hard cap of 5 items

---

## Decision 2: Component Location

**Decision**: Add a `ProjectNotesPanel` component at `frontend/src/components/projects/ProjectNotesPanel.tsx` and integrate it into `ProjectSidebar`.

**Rationale**:
- `ProjectSidebar` already lives at `frontend/src/components/projects/ProjectSidebar.tsx`
- Keeping the notes panel in the same `components/projects/` folder maintains cohesion
- A dedicated component keeps `ProjectSidebar` under the 700-line limit
- Mirrors how the workspace sidebar consumes note data: sidebar imports and renders the sub-list directly

**Alternatives considered**:
- Inline in `ProjectSidebar`: rejected — exceeds 700-line limit easily; harder to test
- Feature-level component under `features/notes/components/`: rejected — this panel is project-domain UI, not note-domain UI

---

## Decision 3: Permission Check

**Decision**: Read `canCreateContent` by calling `useWorkspaceStore()` inside `ProjectNotesPanel` and checking `currentUserRole !== 'guest'`.

**Rationale**:
- This is exactly the same pattern used in `ProjectSidebar`, `notes/page.tsx`, and `sidebar.tsx`
- `WorkspaceStore` is a singleton in `RootStore`; reading it from a child component is idiomatic

**Alternatives considered**:
- Pass `canCreateContent` as a prop from `ProjectSidebar`: viable but adds prop drilling for a value already accessible via hook

---

## Decision 4: "View all" Link Target

**Decision**: Link to `/{workspaceSlug}/notes?projectId={project.id}` — future-proofing the notes page filter.

**Rationale**:
- Notes page at `/(workspace)/[workspaceSlug]/notes` is the canonical notes list
- The URL-based filter param `projectId` is a natural extension of the existing `filterPinned` query state pattern already in the notes page
- No backend changes required for the link target

**Note**: The notes page currently does not parse `projectId` from URL params — that is a follow-on enhancement, not a blocker. The "View all" link still navigates to the notes page (correct intent); project pre-filtering can be added separately.

---

## Decision 5: Loading and Error States

**Decision**: Use a `Skeleton` (3 rows) during loading; render a simple inline `"Failed to load notes"` text on error. No full error boundary needed — this is a secondary sidebar panel.

**Rationale**:
- Matches minimal pattern used in other sidebar sections
- Failure of the notes panel must NOT crash the project layout
- Constitution §IV (Code Quality): no mocks in production paths — real error state required

---

## Resolved Clarifications

All spec assumptions confirmed via codebase inspection:

| Assumption | Verification |
|---|---|
| `Note.projectId` exists | `types/note.ts` line 108: `projectId?: string` |
| API supports `projectId` filter | `workspace_notes.py` line 147: `project_id` query param |
| `useNotes` accepts `projectId` | `hooks/useNotes.ts` line 17: `projectId?: string` |
| `CreateNoteData.projectId` exists | `types/note.ts` line 108: `projectId?: string` |
| `WorkspaceStore.currentUserRole` accessible | `sidebar.tsx`, `notes/page.tsx` both use `workspaceStore.currentUserRole !== 'guest'` |
