# Quickstart: Project Notes Panel (022)

**Date**: 2026-03-10
**Updated**: 2026-03-10 — v2: Enhancement feature scenarios added

## Integration Scenarios (Base Feature)

### Scenario 1: Panel renders with pinned + recent notes

```
Setup:
  - Workspace has a project with ID "proj-123"
  - 3 notes linked to "proj-123", 1 pinned, 2 recent

Steps:
  1. Navigate to /{workspaceSlug}/projects/proj-123/overview
  2. Project layout renders ProjectSidebar
  3. ProjectSidebar renders ProjectNotesPanel below nav items
  4. Panel shows:
     - "Pinned" section: 1 note title (clickable)
     - "Recent" section: 2 note titles (clickable)

Verify:
  - API call: GET /workspaces/{wsId}/notes?project_id=proj-123&is_pinned=true&pageSize=5
  - API call: GET /workspaces/{wsId}/notes?project_id=proj-123&is_pinned=false&pageSize=5
  - Clicking a title navigates to /{workspaceSlug}/notes/{noteId}
  - No "New Note" button visible (Enhancement 2)
```

### Scenario 2: Empty project (no notes)

```
Setup:
  - Project has no linked notes

Steps:
  1. Navigate to project
  2. ProjectNotesPanel renders

Verify:
  - Both queries return { items: [], total: 0 }
  - Empty state message shown
  - No "New Note" button (Enhancement 2: button removed from project panel)
```

### Scenario 3: Guest user sees panel without "New Note"

```
Setup:
  - Current user has role "guest"

Steps:
  1. Navigate to project sidebar

Verify:
  - Notes panel renders notes list normally
  - No "New Note" button (removed from project panel by Enhancement 2)
```

### Scenario 4: "View all" link with >5 notes

```
Setup:
  - Project has 8 pinned notes

Steps:
  1. Navigate to project sidebar

Verify:
  - Only 5 pinned note rows shown
  - "View all →" link present below pinned section
  - Link points to /{workspaceSlug}/notes (notes page)
```

---

## Integration Scenarios (Enhancement Features)

### Scenario 5: Workspace sidebar pinned notes show project label

```
Setup:
  - Workspace has note "Sprint Retro" (pinned) with projectId = "proj-123"
  - Project "proj-123" has name "Backend"
  - useProjects returns project list including Backend

Steps:
  1. Open workspace sidebar
  2. PINNED section renders

Verify:
  - Row shows: [FileText icon] "Sprint Retro" · "Backend" (muted label)
  - Notes without projectId show no label
  - Project name resolved from TQ cache (no extra API call)
```

### Scenario 6: New Note via TemplatePicker + project selection

```
Steps:
  1. Click "New Note" in workspace sidebar
  2. TemplatePicker modal opens (4 SDLC templates + blank)
  3. Select "Design Review" template
  4. Click "Create Design Review Note →"
  5. MoveNoteDialog opens: "Add to project?"
  6. Select project "Frontend" from list
  7. Note created: title "New Design Review Note", template content, projectId = Frontend.id
  8. Router navigates to /{workspaceSlug}/notes/{newNoteId}

Verify:
  - note.projectId === Frontend.id
  - note.content matches Design Review template content
  - TanStack Query notes list cache invalidated
```

### Scenario 7: New Note to root workspace (no project)

```
Steps:
  1. Click "New Note" in workspace sidebar
  2. TemplatePicker opens → select "Blank"
  3. MoveNoteDialog opens
  4. Select "No project (root)"
  5. Confirm

Verify:
  - note.projectId is undefined/null
  - Note created without project association
```

### Scenario 8: Note breadcrumb shows project path

```
Setup:
  - Note "Auth Design" with projectId = "proj-backend"
  - Project "proj-backend" has name "Backend"

Steps:
  1. Navigate to /{workspaceSlug}/notes/{noteId}
  2. NoteCanvasLayout renders InlineNoteHeader with projectId

Verify:
  - Breadcrumb renders: [FileText] Notes > Backend > Auth Design
  - "Backend" is a link to /{workspaceSlug}/projects/proj-backend/overview
  - On mobile (<sm), project segment hidden (hidden sm:inline)
  - useProject fetches project data (cached from earlier page loads)
```

### Scenario 9: Note without project shows simple breadcrumb

```
Setup:
  - Note has no projectId

Verify:
  - Breadcrumb renders: [FileText] Notes > [Title]
  - No project segment rendered
```

### Scenario 10: Move note to different project

```
Setup:
  - Note currently linked to project "Frontend"

Steps:
  1. Open note
  2. Click "..." options dropdown in header
  3. Click "Move..."
  4. MoveNoteDialog opens with "Frontend" pre-selected
  5. Select "Backend"
  6. Click "Move Note"

Verify:
  - PATCH /workspaces/{wsId}/notes/{noteId} called with body { projectId: "backend-id" }
  - Breadcrumb updates to "Notes > Backend > [title]"
  - TanStack Query note detail cache invalidated/updated
```

### Scenario 11: Move note to root workspace

```
Steps:
  1. Open note in project "Frontend"
  2. Click "..." → "Move..."
  3. Select "No project (root)"
  4. Confirm

Verify:
  - PATCH called with { projectId: null } or projectId omitted
  - Breadcrumb reverts to "Notes > [title]"
```

---

## File Locations

| File | Purpose |
|---|---|
| `frontend/src/components/projects/ProjectNotesPanel.tsx` | Panel component (modify: remove New Note button) |
| `frontend/src/components/projects/ProjectSidebar.tsx` | Mount point (no change needed) |
| `frontend/src/components/layout/sidebar.tsx` | Workspace sidebar (modify: project label, TemplatePicker, project selector) |
| `frontend/src/components/editor/InlineNoteHeader.tsx` | Note header (modify: breadcrumb + Move option) |
| `frontend/src/components/editor/MoveNoteDialog.tsx` | New: project picker dialog |
| `frontend/src/app/.../notes/[noteId]/page.tsx` | Note detail page (modify: pass onMove) |
| `frontend/src/components/editor/NoteCanvasLayout.tsx` | Canvas layout (modify: forward onMove prop) |

---

## Dev Commands

```bash
cd frontend && pnpm dev          # Start dev server (port 3000)
cd frontend && pnpm type-check   # TypeScript check
cd frontend && pnpm lint         # ESLint check
cd frontend && pnpm test         # Vitest unit tests
```


## Integration Scenarios

### Scenario 1: Panel renders with pinned + recent notes

```
Setup:
  - Workspace has a project with ID "proj-123"
  - 3 notes linked to "proj-123", 1 pinned, 2 recent

Steps:
  1. Navigate to /{workspaceSlug}/projects/proj-123/overview
  2. Project layout renders ProjectSidebar
  3. ProjectSidebar renders ProjectNotesPanel below nav items
  4. Panel shows:
     - "Pinned" section: 1 note title (clickable)
     - "Recent" section: 2 note titles (clickable)
     - "New Note" button visible (non-guest user)

Verify:
  - API call: GET /workspaces/{wsId}/notes?project_id=proj-123&is_pinned=true&pageSize=5
  - API call: GET /workspaces/{wsId}/notes?project_id=proj-123&is_pinned=false&pageSize=5
  - Clicking a title navigates to /{workspaceSlug}/notes/{noteId}
```

### Scenario 2: Empty project (no notes)

```
Setup:
  - Project has no linked notes

Steps:
  1. Navigate to project
  2. ProjectNotesPanel renders

Verify:
  - Both queries return { items: [], total: 0 }
  - Empty state message shown
  - "New Note" button visible (non-guest)
```

### Scenario 3: Create note from panel

```
Steps:
  1. Click "New Note" in the panel
  2. Mutation: POST /workspaces/{wsId}/notes { title: "Untitled", projectId: "proj-123" }
  3. On success: navigate to /{workspaceSlug}/notes/{newNoteId}
  4. Note canvas opens with project context header

Verify:
  - New note has projectId === "proj-123"
  - TanStack Query cache invalidated for project notes list
```

### Scenario 4: Guest user sees panel without "New Note"

```
Setup:
  - Current user has role "guest"

Steps:
  1. Navigate to project sidebar

Verify:
  - Notes panel renders notes list normally
  - "New Note" button is NOT rendered
  - workspaceStore.currentUserRole === 'guest' check passes
```

### Scenario 5: "View all" link with >5 notes

```
Setup:
  - Project has 8 pinned notes

Steps:
  1. Navigate to project sidebar

Verify:
  - Only 5 pinned note rows shown
  - "View all →" link present below pinned section
  - Link points to /{workspaceSlug}/notes (notes page)
```

---

## File Locations

| File | Purpose |
|---|---|
| `frontend/src/components/projects/ProjectNotesPanel.tsx` | New panel component (create) |
| `frontend/src/components/projects/ProjectSidebar.tsx` | Mount point (modify: add panel after nav) |
| `frontend/src/features/notes/hooks/useNotes.ts` | Data hook (already supports projectId + isPinned) |
| `frontend/src/features/notes/hooks/useCreateNote.ts` | Create mutation (already supports projectId) |

---

## Dev Commands

```bash
cd frontend && pnpm dev          # Start dev server (port 3000)
cd frontend && pnpm type-check   # TypeScript check
cd frontend && pnpm lint         # ESLint check
cd frontend && pnpm test         # Vitest unit tests
```
