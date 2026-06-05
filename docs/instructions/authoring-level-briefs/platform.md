# Level brief — platform

You are authoring **platform-level** instructions.

**Scope:** Master behavior for an ActivityLibrary `thread_type` (or platform-wide defaults when no `thread_type` is scoped). These instructions apply across all organizations unless overridden lower in the stack.

**Write here:**

- The AI’s role in this activity (e.g. initial read, rubric evaluation, final recommendation).
- Analytical priorities, output structure, and evidence standards.
- What to record in TaskMemory vs what belongs in conversational replies.
- Tone and rigor appropriate to the module (`external_paper_review` vs `student_paper_review`).
- Automation-relevant constraints if the activity supports Workflow mode (step boundaries, when to pause).

**Do not write here:**

- Org-specific policies, branding, or confidentiality rules → org layer.
- Personal user preferences → user layer.
- Assignment rubrics or cohort-specific norms → cluster layer.
- This paper / this student → task or thread layer.

**Length:** Typically the longest layer for a `thread_type`; still prefer clarity over volume. Use the ActivityLibrary `default_instruction_content` as a structural reference when provided.
