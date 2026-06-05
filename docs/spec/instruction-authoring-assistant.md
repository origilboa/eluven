# Instruction Authoring Assistant

## Overview

The Instruction Authoring Assistant helps users draft and refine `InstructionLayer` content across platform, org, user, cluster, task, and thread levels, plus ActivityLibrary default instructions.

## Review modes

| Mode | Trigger | Blocks save | Output |
|------|---------|---------------|--------|
| **Integrity check** | `POST /instructions/assistant/integrity-check` | Yes | Structured JSON with `approval_token` on pass |
| **Integrity review (chat)** | Stream with `integrity_review: true` | No | Conversational checklist feedback |
| **Completeness review** | Stream with `completeness_review: true` | No | Advisory gaps vs inherited layers |
| **Remediation** | `POST /instructions/assistant/integrity-check/remediate` (SSE) | No | Guided fixes; may propose draft or partial fix |

## Save gate

All instruction saves require `integrity_approval_token` bound to:

- `user_id`
- `scope_key` (assistant scope or instruction set / activity entry key)
- `content_hash` (SHA-256 of normalized draft)
- 30-minute TTL

Endpoints enforcing the gate:

- `POST /instructions/{level}` (create version)
- `POST /admin/activity-library` and `PATCH` when `default_instruction_content` is non-empty
- `POST /activity-library/manage` and `PATCH` when `default_instruction_content` is non-empty

## Runtime precedence

At thread execution, `ContextAssembler` injects `docs/instructions/instruction-layer-precedence.md` and labels each inherited block with `## InstructionLayer: {level}`.

## Frontend surfaces

All nine instruction editor surfaces use `InstructionAuthoringWorkbench` + `useInstructionDraftGate`:

- Instruction Studio (platform / org / user)
- Cluster, task, thread instruction panels
- Activity Library quick create / edit (instructions tab)
- Activity type wizard (instructions step)
