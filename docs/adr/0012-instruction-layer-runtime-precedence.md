# ADR 0012: Instruction layer runtime precedence

## Status

Accepted — 2026-06-04

## Context

Instruction content is authored across five `InstructionLayer` levels plus ActivityLibrary defaults. Authors need clear conflict resolution at runtime; thread AI must know which layer each block came from.

## Decision

1. Inject a static precedence directive (`docs/instructions/instruction-layer-precedence.md`) as the first system block in `ContextAssembler`.
2. Prefix each instruction system block with `## InstructionLayer: {level}`.
3. Keep platform/org blocks cache-eligible; lower layers remain uncached plain text.

## Consequences

- Thread AI can resolve contradictions using explicit layer labels and precedence rules.
- Authoring-time integrity checks reference the same precedence document via `load_precedence_text()`.
- Slightly larger system prompts; negligible cost vs document context.
