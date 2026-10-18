# Evaluation evidence for the restricted routing sketch

Evaluated implementation commit: `34c4badf265f4fceb06c1a7d651d11aa305f334e`.
Independent review: `independent-code-review.md`; source review is one directory up.
Python 3.12.14, uv 0.12.23, Linux x86_64/glibc 2.41.
Frozen product environment: torch 2.14.1, transformers 5.20.1, pytest 9.1.1,
psutil 7.2.2. `spoi/uv.lock` SHA-256:
`84c7d962a98809b1d158c99bbf37426262a62451dabdd2efc2f82d244775f2e7`.
The research code uses Python stdlib only and does not import these model packages.

`validation.json` identifies the evaluated commit and final research command exits.
`tests.log` retains all 12 passing tests. Full simulator inputs and bounded output
are `../online-results.json`; an independently rerun parsed JSON matched entirely.
No dependency, compatibility guard or numerical tolerance was changed.

## Observed failures retained

- Default `scripts/check.sh`: exit 2, UV cache under /home/agent is read-only.
  `sandbox-cache-failure.log` retains the output. The writable cache path is an
  environment setting, not a dependency/guard change.
- `UV_CACHE_DIR=/workspace/.cache/uv scripts/check.sh` in restricted sandbox:
  exit 1, 64 failed/58 passed/150 errors, with process/shared-memory/network
  restrictions. Full raw output is `sandbox-full-failure.log.gz`.
- Diagnostic frozen `pytest -x`: exit 1, 1 failed/34 passed; PyTorch shared-memory
  manager reports Operation not permitted. Raw output: `sandbox-first-failure.log`.
- Researcher's initial hand fixture expected the wrong gather destination;
  corrected the fixture's intended directional transfer times. Its observed
  assertion is described in `../online-validation-notes.md` (original full
  transcript was not captured to a file; no fabricated raw log).
- Parent review found reevaluation re-selected the gather server with true
  information. Corrected by freezing the perceived decision and adding a directed
  regression; this was a code-review finding, not an observed failing command.
- Parent's new unrelated-overload test failed exit 1 before the admission fix.
  `admission-regression-before-fix.log` retains it; final 12-test run passes.

The main repository suite requires authorized local IPC/socket access beyond the
restricted sandbox. The authorized run completed: **272 passed in 608.74s, exit 0**;
raw output is `repo-check-authorized.log`. It exercises unchanged product sources,
not the separately executed 12 research tests. No skip was counted as a pass.
A sandbox failure is not evidence of an incompatible locked package version.
The native Mac acceptance gate remains outstanding. No real model generation,
pretrained checkpoints, multiple machines, memory reduction or speedup is established.


## Frozen environment commands

To recreate the product environment, use Python 3.12 and
`UV_CACHE_DIR=/workspace/.cache/uv uv sync --project spoi --frozen`, then
`UV_CACHE_DIR=/workspace/.cache/uv scripts/check.sh` with local IPC/socket access.
The existing frozen environment was reused for this evaluation; the sync command
is a reconstruction instruction, not an additional claimed run.
For the research-only stdlib commands and JSON comparison, use
`../online-walkthrough.md`. These checks establish reproducibility of the declared
synthetic model and regression protection for unchanged product code, not physical
HetRoute performance, tensor parity of research scheduling, or Mac acceptance.
