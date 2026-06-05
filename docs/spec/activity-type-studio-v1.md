# Activity Type Studio v1

**Status:** Accepted  
**Date:** 2026-06-05  
**Scope:** Guided and quick creation of ActivityLibrary entries; AI-assisted instructions and prompts; org-scoped types.

## Summary

Activity Type Studio helps `app_admin` and `org_admin` authors create and maintain ActivityLibrary entries (`thread_type` definitions) with three Layer 0 agents:

| Agent | When | Purpose |
|-------|------|---------|
| Activity Type Orchestrator | Guided wizard only | Flow, decisions, validation |
| Instruction Authoring Assistant | Wizard, quick create, edit | `default_instruction_content` |
| Activity Prompt Authoring Assistant | Wizard, quick create, edit | `ActivityPrompt` list |

## Create paths

| Path | Entry | Orchestrator | Agents |
|------|-------|--------------|--------|
| Guided setup | Admin → Activity library → Guided setup | Yes | Instructions (step 4), Prompts (step 5) |
| Quick create | Admin → Activity library → Quick create | No | Instructions + Prompts tabs |

Both paths land in the same edit UI after save.

## Edit

Activity Library list + detail with section tabs: **Settings | Instructions | Prompts**. Specialist agents on Instructions and Prompts tabs (`AuthoringSplitLayout`).

## Instruction sync (decided)

On create or PATCH when `default_instruction_content` is non-empty, upsert matching `InstructionSet` at platform or org level for the `thread_type` — new version created and activated.

## Org scope (decided)

- `org_admin` manages `scope=org` entries via `/api/v1/activity-library/manage/*`
- Org entry with same `thread_type` as platform **shadows** platform for that org's users (existing read API behavior)

## API

### Platform (existing, enhanced)

```
GET/PATCH/POST  /api/v1/admin/activity-library/*
PUT             /api/v1/admin/activity-library/{id}/prompts
```

PATCH/POST sync `InstructionSet` when `default_instruction_content` changes.

### Org manage (new)

```
GET/POST/PATCH  /api/v1/activity-library/manage
GET/PATCH       /api/v1/activity-library/manage/{entry_id}
PUT             /api/v1/activity-library/manage/{entry_id}/prompts
```

Auth: `org_admin` or `app_admin`.

### Assistants (new)

```
POST /api/v1/instructions/assistant/stream
     authoring_target: activity_library_default (implemented)

POST /api/v1/activity-library/prompts/assistant/stream

POST /api/v1/activity-library/assistant/stream
     (orchestrator — guided wizard)
```

SSE events: `status`, `text`, `done`, `error`.

## UI

- `AuthoringSplitLayout`: `lg:grid-cols-2` form + assistant (matches Instruction Studio)
- `ActivityEntryDetailTabs`: shared quick create + edit
- Guided wizard: `/[locale]/admin/activity-library/create`

## Out of scope (v1)

- `automation_execution_spec` authoring UI
- Server-side draft persistence
- Prompt `stage` selector (API still writes `opening`)
