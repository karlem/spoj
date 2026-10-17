# Issue #1 Linux continuation evidence

State: BLOCKED on outstanding native Mac full-suite and fresh-environment acceptance. Cloud compatibility implementation and Linux validation complete; no active cloud writer after this handoff. PR #3 stays draft; no merge or #2 work is authorized.

Evaluated implementation: `e556069eea3e882903244514937b56eba057122b`, based on `0f67e73f02a22030222e5491cf27acdd8d8cda2a`. Approved spec: `e49f36f30312400a45c4d68d4a1db18328e64ef6`. Environment: Linux x86_64, Python 3.12.14, uv 0.12.23, torch 2.14.1+cu130, transformers 5.20.1, pytest 9.1.1, psutil 7.2.2. CPU float32 and eager experts; no pretrained checkpoints downloaded.

The frozen lock is unchanged (SHA-256 `84c7d962a98809b1d158c99bbf37426262a62451dabdd2efc2f82d244775f2e7`). Linux Torch's runtime build suffix caused the original literal guard to fail. Inspected installed Qwen router/expert/block source and Torch build metadata. The remedy allows exact platform/build pairs only: darwin/2.14.1 and linux/2.14.1+cu130. It does not strip suffixes or accept arbitrary builds. Qwen SHA-256 remains `58387f2cc22a706e7e4c7dabe6cf05cb1e9c9fe48c57e2f2a0fc5cbdb2132f4f`; Transformers, eager backend, schema, finite CPU float32 guards and parity tolerances remain unchanged.

## Executed validation

Working directory `/workspace/spoj`; `UV_CACHE_DIR=/workspace/.cache/uv`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`. Native spawn/shared-memory permission was enabled for process tests. Logs are locally under ignored `target/issue1-linux/`; durable summaries and smoke output are in PR #3 comments.

| Command | Exit | Result |
| --- | --- | --- |
| `uv sync --project spoi --frozen --python 3.12` (onboarding plus repeat) | 0 | 58 locked packages installed, repeat sync passed |
| `uv run --project spoi --frozen pytest spoi/tests/test_adapter.py -q` | 0 | 34 passed |
| `uv run --project spoi --frozen python -m spoi smoke` | 0 | two persistent workers, two requests, zero max absolute/relative error, exits [0,0] |
| `./scripts/check.sh` | 0 | 114 passed in 189.92s; script execs `uv run --project spoi --frozen pytest spoi/tests -q` |
| `UV_PROJECT_ENVIRONMENT=/workspace/spoj/target/issue1-linux/fresh-e556069 uv sync --project spoi --frozen --python 3.12` | 0 | fresh environment at previously absent path |
| same fresh environment, `uv run --project spoi --frozen python -m spoi smoke` | 0 | zero parity errors, two requests, worker exits [0,0] |

The full suite includes the 48 parity scenarios, controlled zero-hit/both-hit cases, compact shard integrity, protocol/timeout/crash/backpressure failures, and subprocess/named-shared-memory cleanup. No tests were skipped. The explicit full pytest entry was exercised through its exact `exec` wrapper, without a redundant second full run. Before the remedy, smoke exited 1 and both full-suite commands each reported 20 passed, 37 failed, 48 errors due to compatibility rejection; this failed evidence remains part of the onboarding history.

Normal and fresh smoke state hash: `54b4e4e45ab30b10964f10c20646abd4207d95617adf044b702a70111388ca47`. Expert ownership [0,1]/[2,3]; each worker's storage bytes [131072,65536]. Seeded state may differ across operating systems; each parity comparison uses the same local frozen state.

## Review and remaining acceptance

Independent read-only Codex sub-agent reviewed frozen e556069, including the existing numerical adapter, shard ownership, queue/deadline/cleanup implementation and new exact-build guard. No actionable findings. Reviewer ran no suites concurrently and made no edits. Exact serving model identifier unavailable; review is independent-agent review within the same harness, not external human review. Review record: https://github.com/karlem/spoj/pull/3#issuecomment-6234614429.

Native Mac smoke previously passed on the base implementation, but the full Mac suite and fresh smoke on the updated commit remain unrun here. Run the README's frozen sync, check script and fresh offline-HF smoke on native Mac/ARM, retaining actual versions and command output. Linux success does not satisfy native Mac acceptance, complete v0.1, permit #2, or authorize merge. No Mac host is attached to this cloud session. Future writers must explicitly transfer sole ownership in issue #1 before edits.
