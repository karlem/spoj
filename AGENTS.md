# SPOJ agent rules

**The canonical local experiment specification is indexed in `docs/specs/README.md`. Work is limited to that approved experiment and eligible GitHub issues.**

## Authority and entry gate

- The human is the final authority. Escalate conflicting instructions or unclear requirements to the human; do not silently improvise.
- Once installed and approved, the canonical specification indexed in `docs/specs/README.md` is authoritative for product behavior. Do not invent requirements or treat this bootstrap documentation as a product specification.
- GitHub Issues define executable implementation work. An issue must reference the canonical spec, state acceptance criteria and validation, and have satisfied dependencies before work starts. An issue that conflicts with the spec is blocked until resolved.
- Without an approved canonical spec, report `BLOCKED: canonical product specification not yet installed`. With a spec but no eligible issues, report `IDLE: no eligible GitHub issues`.
- Idle agents must never invent work, requirements, or tickets. Human-directed factory maintenance is allowed; it does not authorize product implementation.

## Execution rules

- Before managing, implementing, reviewing, or fixing an issue, read `docs/engineering/factory.md` for roles, routing, worktree ownership, and evidence requirements.
- Each implementation agent owns one issue at a time: one issue, one branch, one isolated worktree, one owning writer. Concurrent writers must use separate worktrees. Reviewers inspect without becoming simultaneous writers.
- Stay within the active issue. No opportunistic refactors unrelated to it. Proposed scope changes require human resolution before implementation.
- Run `scripts/check.sh` and all issue-required validation. Deterministic checks must pass; never bypass failures, weaken checks to obtain a pass, or represent skipped validation as success. The Phase 0 check is not product-validation evidence.
- Use a reviewer independent from the implementer where practical. High-blast-radius changes require strong review. Disclose any lack of independence; the human decides whether to accept it.
- Reviewers report findings rather than automatically editing. Fixers make targeted corrections, then checks and affected review must be repeated.
- Failed or ambiguous work must escalate with evidence. After two failed worker attempts on an issue, stop retrying and escalate to a frontier worker or the human through the manager.
- Report blockers explicitly: state, reason, evidence, and the decision or input needed to resume. Stop safely when blocked; do not keep mutating files or start substitute work.
- Destructive actions, history rewrites, deletion of worktrees containing work, and irreversible external actions require explicit human authority for that action. A task assignment does not grant blanket destructive authority.
- The human authorizes merge. A merge-ready result must identify the issue and spec revision, implementation commit, checks and outcomes, independent review and resolved findings, remaining limitations, and artifacts. Completion requires evidence, never merely an agent's claim.

## Records

- Use `WORKING`, `IDLE`, `BLOCKED`, `REVIEW`, `FAILED`, and `DONE` as defined in the workflow. `DONE` does not mean merged.
- For model attempts, follow `.factory/README.md`; record actual outcomes in `.factory/model-runs.jsonl`. Never fabricate runs, costs, reviews, or completion.
- Before installing a specification, follow `docs/specs/README.md`. Before recording an architecture decision, follow `docs/decisions/README.md`.
- Repository correctness must remain reproducible with git, files, scripts, and CLI commands. cmux and Herdr are optional operating surfaces, not sources of requirements or required test infrastructure.
