# SPOJ

SPOI lab: begin with a tiny Qwen3 MoE block executed natively on macOS. The approved experiment checks expert ownership and numerical correctness across processes before later multi-device capacity experiments.

Current manager state:

```text
IDLE: no eligible GitHub issues
```

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

It currently succeeds and explicitly reports that no product-specific checks are configured. This does not validate any product behavior. Once the stack is established, this script becomes the canonical entry point for formatting, linting, type checks, unit tests, integration tests, and relevant deterministic validation. Future CI must invoke this same script.

The intended progression is `grill-me` (grilling) → final specification → `to-spec` → committed spec → `to-tickets` → GitHub Issues → manager → worker → checks → independent review → targeted fixes → merge-ready result → human merge decision. These are workflow stages; this bootstrap does not install commands or orchestrators with those names.

V0 uses files, git, GitHub Issues, shell scripts, and agent CLIs. No autonomous product agents should start before the entry gate is satisfied.
