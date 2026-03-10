# Data Model: Project Notes Panel (022)

**Date**: 2026-03-10
**Updated**: 2026-03-10 — v2: Enhancement feature data flows added

This feature is **frontend-only** — no new backend models, migrations, or API endpoints. All data already exists.

---

## Entities Used

### Note (existing)

Relevant fields consumed by the panel and enhancements:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Navigation link key |
| `title` | `string` | Displayed in panel row (truncated to 1 line) |
| `isPinned` | `boolean` | Determines Pinned vs Recent sub-section |
| `projectId` | `string?` | Filter: only notes where `projectId === project.id`; also used for breadcrumb and Move dialog |
| `updatedAt` | `string` (ISO) | Sort order for Recent sub-section |

Source: `frontend/src/types/note.ts`

### Project (existing)

Relevant fields consumed by the panel and enhancements:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Used as `projectId` filter in API call; used as option value in project picker |
| `name` | `string` | Displayed as label in workspace sidebar pinned notes; used in breadcrumb; listed in project picker |
| `workspaceId` | `string` (UUID) | Used to build `workspaceSlug`-based note links |

Source: `frontend/src/types/workspace.ts`

---

## Data Flow

### Base Feature: Project panel

```
ProjectSidebar
  └── ProjectNotesPanel (props: project, workspaceSlug, workspaceId)
        ├── useNotes({ workspaceId, projectId: project.id, isPinned: true, pageSize: 5 })
        │     → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=true&pageSize=5
        │     → pinnedNotes: Note[]
        └── useNotes({ workspaceId, projectId: project.id, isPinned: false, pageSize: 5 })
              → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=false&pageSize=5
              → recentNotes: Note[]
```

### Enhancement 1: Workspace sidebar project label

```
sidebar.tsx
  ├── noteStore.pinnedNotes → Note[] (includes projectId?: string)
  └── useProjects({ workspaceId })
        → TanStack Query → GET /workspaces/{id}/projects
        → projectMap: Record<string, string>  (id → name)
  → Render: pinnedNotes[i].title + projectMap[pinnedNotes[i].projectId]
```

### Enhancement 3+4: New Note with TemplatePicker + project selector

```
sidebar.tsx (showTemplatePicker state)
  └── TemplatePicker
        → onConfirm(template: NoteTemplate | null)
        → sets pendingTemplate, opens showProjectPicker
  └── MoveNoteDialog (project selector step)
        ├── useProjects({ workspaceId })
        └── onSelect(projectId: string | null)
              → createNote.mutate({ title, content, projectId })
              → POST /workspaces/{id}/notes
```

### Enhancement 5: Note breadcrumb

```
NoteDetailPage
  └── NoteCanvasLayout (props: projectId, workspaceId)
        └── InlineNoteHeader (props: projectId, workspaceId)
              └── useProject({ projectId, enabled: !!projectId })
                    → TanStack Query → GET /projects/{id}
                    → project: Project
              → Render: Notes > [project.name link] > [note.title]
```

### Enhancement 6: Move note

```
NoteDetailPage
  └── NoteCanvasLayout (props: onMove)
        └── InlineNoteHeader (props: onMove, projectId, workspaceId)
              └── MoveNoteDialog (when "Move..." clicked)
                    ├── useProjects({ workspaceId })
                    └── onSelect(newProjectId: string | null)
                          → updateNote.mutate({ projectId: newProjectId ?? undefined })
                          → PATCH /workspaces/{id}/notes/{noteId}
```

---

## API Calls (existing endpoints, no changes)

### List pinned project notes
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=true
  &pageSize=5
```

### List recent project notes (not pinned)
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=false
  &pageSize=5
```

### Create project-linked note
```
POST /api/v1/workspaces/{workspaceId}/notes
Body: {
  "title": "...",
  "workspaceId": "{workspaceId}",
  "projectId": "{projectId}",        // optional
  "content": { ... }                  // optional template content
}
```

### Move note (update projectId)
```
PATCH /api/v1/workspaces/{workspaceId}/notes/{noteId}
Body: {
  "projectId": "{newProjectId}"      // or omit to remove project link
}
```

### List projects (for picker and label)
```
GET /api/v1/workspaces/{workspaceId}/projects
```

### Get single project (for breadcrumb)
```
GET /api/v1/projects/{projectId}
```

All endpoints are authenticated (Supabase Auth header) and RLS-enforced.

---

## State (UI only, no persistent state)

### Base Feature

| State | Location | Type |
|---|---|---|
| Loading (pinned) | TanStack Query | `boolean` |
| Loading (recent) | TanStack Query | `boolean` |
| Error (pinned) | TanStack Query | `Error \| null` |
| Error (recent) | TanStack Query | `Error \| null` |
| Create pending | TanStack Query mutation | `boolean` |

### Enhancement Features

| State | Location | Type | Purpose |
|---|---|---|---|
| `showTemplatePicker` | `sidebar.tsx` local | `boolean` | Controls TemplatePicker modal |
| `pendingTemplate` | `sidebar.tsx` local | `NoteTemplate \| null \| undefined` | Staged template awaiting project selection |
| `showProjectPicker` | `sidebar.tsx` local | `boolean` | Controls project selector modal after template |
| `showMoveDialog` | `InlineNoteHeader` local | `boolean` | Controls Move... dialog |


---

## Entities Used

### Note (existing)

Relevant fields consumed by the panel:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Navigation link key |
| `title` | `string` | Displayed in panel row (truncated to 1 line) |
| `isPinned` | `boolean` | Determines Pinned vs Recent sub-section |
| `projectId` | `string?` | Filter: only notes where `projectId === project.id` |
| `updatedAt` | `string` (ISO) | Sort order for Recent sub-section |

Source: `frontend/src/types/note.ts`

### Project (existing)

Relevant fields consumed by the panel:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Used as `projectId` filter in API call |
| `workspaceId` | `string` (UUID) | Used to build `workspaceSlug`-based note links |

Source: `frontend/src/types/workspace.ts`

---

## Data Flow

```
ProjectSidebar
  └── ProjectNotesPanel (props: project, workspaceSlug, workspaceId)
        ├── useNotes({ workspaceId, projectId: project.id, isPinned: true, pageSize: 5 })
        │     → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=true&pageSize=5
        │     → pinnedNotes: Note[]
        └── useNotes({ workspaceId, projectId: project.id, isPinned: false, pageSize: 5 })
              → TanStack Query → GET /workspaces/{id}/notes?project_id=X&is_pinned=false&pageSize=5
              → recentNotes: Note[]
```

---

## API Calls (existing endpoints, no changes)

### List pinned project notes
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=true
  &pageSize=5
```

### List recent project notes (not pinned)
```
GET /api/v1/workspaces/{workspaceId}/notes
  ?project_id={projectId}
  &is_pinned=false
  &pageSize=5
```

### Create project-linked note
```
POST /api/v1/workspaces/{workspaceId}/notes
Body: {
  "title": "Untitled",
  "workspaceId": "{workspaceId}",
  "projectId": "{projectId}"
}
```

All endpoints are authenticated (Supabase Auth header) and RLS-enforced.

---

## State (UI only, no persistent state)

| State | Location | Type |
|---|---|---|
| Loading (pinned) | TanStack Query | `boolean` |
| Loading (recent) | TanStack Query | `boolean` |
| Error (pinned) | TanStack Query | `Error \| null` |
| Error (recent) | TanStack Query | `Error \| null` |
| Create pending | TanStack Query mutation | `boolean` |
