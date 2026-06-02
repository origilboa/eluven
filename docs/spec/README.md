# .cursor/rules — Eluven

These files define the project-specific instructions for Cursor + Claude. Place the contents of this folder in `.cursor/rules/` at the root of your repository.

## Spec documents in this folder

| File | Purpose |
|------|---------|
| `academic_research_platform_concept_v1_2.docx` | Product concept and module specification |
| `eluven_data_model_v1_0.docx` | Entity schemas, indexes, API specification |
| `eluven_process_and_plan_v1_6.docx` | **Current** process and development plan (post MVP audit) |
| `eluven_process_and_plan_v1_5.docx` | Prior plan version (superseded by v1.6) |

Regenerate after major milestones: `python scripts/generate_plan_v1_6.py` (requires `python-docx`).

See also: [docs/open-questions.md](../open-questions.md) for post-audit follow-ups.

## Files

| File | Applies to | Purpose |
|------|-----------|---------|
| `00-session-protocol.mdc` | All files | How to work with this project — read before every session |
| `01-project-overview.mdc` | All files | Domain model, architecture principles, always active |
| `02-tech-stack.mdc` | All files | Tech decisions, libraries to use and avoid, always active |
| `03-conventions.mdc` | Code files | Repo structure, naming, security rules |
| `04-ai-patterns.mdc` | Backend AI/RAG code | Bedrock integration, context assembly, structured output |
| `05-infrastructure.mdc` | infra/ and config files | SST patterns, AWS services, EC2 dev environment |
| `06-testing-logging.mdc` | Test files | Testing strategy, structured logging patterns |
| `07-rtl-i18n.mdc` | Frontend files | Hebrew/RTL support — critical MVP requirement |

## Platform
- **Name:** Eluven
- **Domain:** eluven.ai
- **Repo:** github.com/[your-username]/eluven

## How to use in Cursor

1. Copy all `.mdc` files to `.cursor/rules/` in your repository root
2. Cursor automatically loads rules matching the current file's glob pattern
3. Files with `alwaysApply: true` are loaded for every conversation
4. Use **Composer with plan** for new features — review the plan against the spec before approving execution
5. Use **Agent mode** for scaffolding — it will follow these rules when generating code

## How to use in Claude Code

```bash
claude --context .cursor/rules/
```

## Rules to add during build

| Before this | Add this file |
|---|---|
| Data model session | `08-data-model.mdc` |
| API build | `09-api-patterns.mdc` |
| Document pipeline | `10-document-pipeline.mdc` |
| Workflow engine | `11-workflow-engine.mdc` |
| Frontend build | `12-frontend-patterns.mdc` |
| Instruction work | `13-instruction-layer.mdc` |

## Keeping rules up to date

When significant architectural decisions are made, update the relevant rules file and commit alongside the code change. Rules are living documentation — they should reflect current decisions, not historical ones.

Version: 1.2 | May 2026
