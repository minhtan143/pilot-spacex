# Feature Specification: Project Notes Panel

**Feature Branch**: `022-project-notes-panel`
**Created**: 2026-03-10
**Updated**: 2026-03-10 — v2: 6 enhancement features added
**Status**: In Progress
**Input**: User description: "A new panel has been added to the project's taskbar to display Recent Notes/Pinned Notes, which looks similar to the workspace's UI panel."

---

## Enhancement Features (v2 additions)

These 6 enhancements build on the base implementation:

1. **Workspace sidebar pinned notes** — display a project label after the note name.
2. **Project notes panel** — remove the "New Note" button; show only the Recent notes section.
3. **New Note button (workspace sidebar)** — wire TemplatePicker modal before note creation (reusing T-018 from feature 018).
4. **New Note with project selector** — after template selection, user can choose which project (or root workspace) to store the note in.
5. **Note view breadcrumb** — display `Notes > [Project name] > [Note name]` when the note belongs to a project.
6. **Note options: Move** — add a "Move..." option in the note's `...` dropdown to reassign the note to a different project or root workspace.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Browse Project Notes from Project Sidebar (Priority: P1)

A project member navigates to a project and sees a collapsible "Notes" section in the project sidebar (similar to the PINNED/RECENT sections in the workspace sidebar). The section lists up to 5 pinned notes and up to 5 recent notes scoped to that project, each showing the note title and a link to navigate directly to the note canvas.

**Why this priority**: This is the core feature — making project-scoped notes discoverable from the project context without leaving to the global Notes page. Every other story depends on notes being visible here.

**Independent Test**: Can be fully tested by navigating to any project with notes and verifying the Notes section appears in the project sidebar with correct pinned/recent listings.

**Acceptance Scenarios**:

1. **Given** a project has at least one pinned note, **When** a user opens that project's sidebar, **Then** a "Pinned" notes section is visible showing up to 5 pinned notes for that project, each with a clickable title.
2. **Given** a project has recent notes (not pinned), **When** a user opens that project's sidebar, **Then** a "Recent" notes section is visible showing up to 5 of the most recently modified notes for that project (excluding pinned ones).
3. **Given** a project has no notes at all, **When** a user opens the project sidebar, **Then** the Notes section shows an empty state with a "New Note" shortcut.
4. **Given** a user clicks a note title in the panel, **When** the click is registered, **Then** the user is navigated to the note's editing canvas.

---

### User Story 2 — Create a Note Scoped to the Project from the Panel (Priority: P2)

A project member wants to quickly create a new note associated with the current project. They see a "New Note" button or inline shortcut within the project notes panel that creates a note pre-linked to the project and navigates them to the note canvas.

**Why this priority**: Reduces friction for creating project-linked notes; secondary to browsing which is P1.

**Independent Test**: Can be fully tested by clicking the "New Note" action in the project notes panel and verifying a new note is created, linked to the project, and the user is navigated to the note editor.

**Acceptance Scenarios**:

1. **Given** a user is in the project sidebar notes section, **When** they click "New Note", **Then** a new note is created pre-linked to the current project and the user is navigated to the note editor.
2. **Given** a guest-role user is viewing the project sidebar, **When** the notes panel is displayed, **Then** the "New Note" button is hidden (guests cannot create content).

---

### User Story 3 — Notes Panel Matches Workspace Sidebar Visual Style (Priority: P3)

The project notes panel (both the Pinned and Recent sub-sections) uses the same visual language as the workspace sidebar's PINNED/RECENT notes sections: same icon sizes, typography, hover states, and section headers.

**Why this priority**: Visual consistency; purely a polish concern once the functional panel exists.

**Independent Test**: Can be validated by side-by-side screenshot comparison of the workspace sidebar notes sections and the new project sidebar notes sections.

**Acceptance Scenarios**:

1. **Given** the project sidebar notes panel is rendered, **When** compared side-by-side to the workspace sidebar notes sections, **Then** icon sizes, text size, hover styles, and section header labels are visually identical.
2. **Given** the notes list is longer than 5 items, **When** the panel is displayed, **Then** only 5 items are shown with a "View all" link pointing to the project-scoped notes list.

---

### Edge Cases

- What happens when a note appears in both pinned and recent lists? The note is shown only in Pinned; the Recent sub-section excludes pinned notes (same behaviour as workspace sidebar).
- What happens when the project notes API call fails or is slow? The panel shows skeleton loaders during fetch and a non-blocking inline error message on failure; the project layout does not crash.
- What happens on mobile where the project sidebar collapses to a tab bar? The Notes panel is not shown in the mobile tab bar (tab bar shows fixed nav items only); notes remain accessible via the global Notes page.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project sidebar MUST include a "Notes" section below the navigation links, containing two sub-sections: "Pinned" and "Recent".
- **FR-002**: The Pinned sub-section MUST display up to 5 notes with `isPinned = true` linked to the current project, ordered by most-recently-modified.
- **FR-003**: The Recent sub-section MUST display up to 5 notes linked to the current project (excluding pinned notes), ordered by `updatedAt` descending.
- **FR-004**: Each note entry MUST display the note title (truncated to one line) as a clickable link navigating to the note's editor page.
- **FR-005**: When a project has no notes, the Notes section MUST show a minimal empty state with a "New Note" action.
- **FR-006**: The Notes section MUST include a "New Note" action that creates a note pre-linked to the current project and navigates to the note editor. This action MUST be hidden for guest-role users.
- **FR-007**: When more than 5 notes exist in either sub-section, a "View all" link MUST be shown, pointing to the Notes page filtered by the current project.
- **FR-008**: The Notes panel visual style (section headers, item rows, icons, hover states) MUST match the workspace sidebar PINNED/RECENT notes sections.
- **FR-009**: The Notes section MUST be rendered only in the desktop sidebar (medium breakpoint and above); it MUST NOT appear in the mobile tab bar.
- **FR-010**: Note data for the panel MUST be fetched scoped to the current project, requesting no more than 10 notes per call.

### Functional Requirements (v2 — Enhancement Features)

- **FR-011**: The workspace sidebar PINNED notes section MUST display a muted project name label after each note title when the note's `projectId` is set.
- **FR-012**: The project sidebar notes panel MUST NOT include a "New Note" button; it MUST display only the Pinned and Recent lists.
- **FR-013**: The workspace sidebar "New Note" button MUST open a TemplatePicker modal before creating a note (4 SDLC templates + blank option), reusing the `TemplatePicker` component built in feature 018.
- **FR-014**: After template selection, the system MUST present a project selector step allowing the user to assign the new note to a project or the root workspace.
- **FR-015**: The note view header MUST display a breadcrumb path of `Notes > [Project name] > [Note name]` when the note has a `projectId`; the project name segment MUST link to the project overview page.
- **FR-016**: The note view options menu MUST include a "Move..." action that opens a project picker allowing the user to reassign the note to a different project or root workspace (no project).

### Key Entities

- **Note**: A workspace note. Relevant attributes: `id`, `title`, `isPinned`, `projectId`, `updatedAt`. Notes are linked to a project via `projectId`.
- **Project**: The project context. Relevant attributes: `id`, `name`, `workspaceId`. Used as the filter scope for the notes panel and as label/picker options.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can reach a project-linked note from the project sidebar in 2 clicks or fewer (open project → click note title).
- **SC-002**: The Notes panel data appears within the same page load as the rest of the project sidebar with no additional perceptible delay.
- **SC-003**: 100% of notes created via workspace sidebar "New Note" that have a project selected are correctly linked to that project.
- **SC-004**: The Notes panel is visually consistent with the workspace sidebar notes sections when reviewed side-by-side.
- **SC-005**: The note view breadcrumb correctly resolves and displays the project name segment for all notes with a `projectId`.
- **SC-006**: After using "Move...", the note's `projectId` is updated and the breadcrumb reflects the change without a full page reload.

## Assumptions

- Notes are already linkable to projects via `projectId` in the data model (`Note.projectId?: string`).
- The existing notes list API supports filtering by `projectId` (`project_id` query param on `GET /workspaces/{id}/notes`).
- The project panel will use a direct data query with `projectId` filter rather than the workspace-scoped MobX `NoteStore`, since `NoteStore` is not project-aware.
- The `canCreateContent` permission check (role is not guest) applies identically to the project sidebar as it does to the workspace sidebar.
- `PATCH /workspaces/{id}/notes/{noteId}` already accepts `projectId` in the request body (mapped from `UpdateNoteData.projectId?: string`).
- The `TemplatePicker` component and `NoteTemplate` type from feature 018 are fully built and available at `features/notes/components/TemplatePicker.tsx`.
