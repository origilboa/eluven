# ADR 003: Cross-application untrusted content integrity

**Status:** Accepted  
**Date:** 2026-06-05

## Context

Manuscripts and knowledge-base documents are untrusted input. Students, authors, or org members can embed visible or hidden instructions to steer AI review output. This affects EPR, SPR, and all future modules sharing the document pipeline.

## Decision

Implement platform-level document integrity at shared trust boundaries:

1. `DocumentIntegrityService` at processing time (all document types)
2. `UntrustedContentWrapper` in `ContextAssembler` (all untrusted context blocks)
3. Platform integrity directive (`InstructionLayer` platform, `thread_type = NULL`)
4. User acknowledgment gate before AI stream and workflow start

No module-specific security branching.

## Consequences

- New modules inherit protection without extra work
- Human review remains the ultimate backstop; technical controls are defense-in-depth
- Phase 4 dual-pass extract-then-evaluate deferred for high-stakes threads

## Module onboarding checklist

- [ ] New untrusted content source? Classify and route through wrapper
- [ ] Uses existing TaskDocument pipeline? Inherits scan + gate automatically
- [ ] Do not duplicate anti-injection prose in ActivityLibrary instructions
