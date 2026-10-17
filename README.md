# SPOJ

SPOI lab: begin with a tiny Qwen3 MoE block executed natively on macOS. The approved experiment checks expert ownership and numerical correctness across processes before later multi-device capacity experiments.

Current implementation and agent ownership are tracked in [issue #1](https://github.com/karlem/spoj/issues/1). Its draft implementation has passed an initial native Mac smoke; full validation and independent review remain pending.

The human remains the final authority. Read [AGENTS.md](AGENTS.md) before operating agents.

## Start here

- [Specifications](docs/specs/README.md): canonical local experiment and human authorization.
- [Factory workflow](docs/engineering/factory.md): roles, model routing, worktrees, review, status, and Codex/OpenCode/cmux/Herdr usage.
- [Decisions](docs/decisions/README.md): record future decisions and their rationale.
- [Issue template](.github/ISSUE_TEMPLATE/agent-task.md): future executable work with scope, acceptance criteria, and evidence.
- [Model run records](.factory/README.md): lightweight JSONL format; the log intentionally starts empty.

Run the verification entry point from the repository root:

```sh
./scripts/check.sh
```

The check entry point runs the locked Python product test suite for issue #1. See [the experiment README](spoi/README.md) for environment setup and smoke execution. The initial native Mac smoke passed; the full suite and independent review remain pending. Follow [issue #1](https://github.com/karlem/spoj/issues/1) for the current GitHub handoff and writer ownership. Future CI should invoke this same check entry point.

The intended progression is `grill-me` (grilling) → final specification → `to-spec` → committed spec → `to-tickets` → GitHub Issues → manager → worker → checks → independent review → targeted fixes → merge-ready result → human merge decision. These are workflow stages; this bootstrap does not install commands or orchestrators with those names.

V0 uses files, git, GitHub Issues, shell scripts, and agent CLIs. No autonomous product agents should start before the entry gate is satisfied.
