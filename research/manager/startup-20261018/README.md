# Manager startup acceptance — 2026-10-18

Tracking: https://github.com/karlem/spoj/issues/9
Charter: research/manager/README.md at 79a47daae7b61cd35428670e8a532faa9ae1b858.
Run ledger key: startup-20261018-1403 (locally assigned, not a provider execution ID).
Provider run ID and serving model IDs: unavailable.

First-run result: PASS for bounded delegation/execution/independent rerun/durable handoff. Full lifecycle acceptance remains pending cross-run resumption.

## Scope
Verify manager -> experiment worker -> independent validator -> durable evidence. Three deterministic local jobs exercise precommit rollback/retry, lost acknowledgement after commit, and duplicate delivery. A transactional unique-ID SQLite sink is compared to a naive append-only SQLite sink.

Predeclared gate: exactly three correct unique reopened results; reject three wrong-value/conflicting-ID cases; naive baseline has two duplicate rows. No inference, network, actual process kill or hardware performance claim.

## Evidence
- recovery_fixture.py: source frozen locally as 571d5dde2aac38a59f01022b39eac10150fc42bf; published source commit 580cb095e9642ad79a92b984ee205d8ea6569fc9.
- Source SHA256: f61e3dce52afde95f05c7d1cc62d8da110bae7b2e71806d90d0bd7e31102e62d.
- Input SHA256: df02c5bf848f4d30871d93f8c223c6ce6da23e9bebaf4fe3da0adadeced079af.
- experiment-evidence.json: raw output, timestamps, environment, command and limits from /root/startup_experiment.
- validation.json: separate /root/startup_validator rerun and review.
- GitHub-published source was fetched back and matches local evaluated bytes.

Reproduce from this directory with Python 3.12 and stdlib SQLite:
```sh
python3 recovery_fixture.py
# Independent checks on Linux with GNU timeout available:
timeout --kill-after=2s 300s python3 -B validate.py
```
Resource limits applied by workers are recorded in their evidence. This bounded fixture creates temporary local SQLite databases and removes them when it exits.

## Interpretation and remaining gates
Successful worker delegation, execution, separate validation and durable handoff establish one end-to-end startup run only. Cross-run resume/deduplication remains for the next invocation. No scheduler-level mutual exclusion guarantee was found; GitHub claims are advisory and uncertain ownership must cause read-only behavior.

Product scripts/check.sh is NOT RUN: it invokes uv/Torch pytest for the product checkout, outside this stdlib fixture environment. No dependencies were installed and no product acceptance or merge-ready status is asserted. Existing native Mac gates remain unchanged.

## Queue after startup
Next invocation first reads issue #9 and verifies this record, skips the already accepted fixture, then records successful resumption. Primary research candidate: D7 inference-aware OS/storage, starting with a precise falsifiable bottleneck and closest implemented baseline from existing #7/PR #8 evidence. No second hypothesis activated. Required output: raw source/trace prerequisites, mechanism bound, matched baseline, threshold and smallest experiment; do not build a new runtime/kernel before establishing a gap. Hardware-dependent claims remain UNRESOLVED without target measurements.

## External experiment machines
Plugin discovery found no SSH, DigitalOcean or Hetzner connector in the current directory search; that search is not exhaustive. No SSH or VM was configured. A possible next deployment is a dedicated VM plus a private GitHub experiment repository/self-hosted runner, subject to verifying job-trigger support and permissions. Do not attach a privileged runner directly to public SPOJ PR execution. No host provisioning or paid resources are authorized by this report.
