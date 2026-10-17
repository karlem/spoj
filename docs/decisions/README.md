# Architecture decisions

No SPOJ architecture decisions have been made. Add a decision only when an actual requirement or engineering constraint requires one; do not infer a stack from the factory tooling.

Use `NNNN-short-title.md` for a concise record. Link its driving issue and spec section where applicable. Proposed decisions are not approved requirements. The human approves consequential choices before dependent implementation proceeds.

Copy this outline when a decision is needed:

```markdown
# NNNN: Title

Status: proposed | accepted | superseded
Date: YYYY-MM-DD
References: issue, spec section/revision, approval evidence

## Context
The concrete constraint or problem requiring a decision.

## Decision
The choice, alternatives considered, and why this choice fits.

## Consequences
Tradeoffs, risks, validation evidence, and follow-up work if authorized.
```

Preserve accepted records. If a decision changes, add a new record and link the superseding decision from the old one.
