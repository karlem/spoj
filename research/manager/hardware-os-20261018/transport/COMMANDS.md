# Reproducer and evidence map

Working directory: `/workspace/spoj-hardware-transport`.
Protocol was committed as `7d0e113` before compilation or timing.
First source was committed as `6ef280b`; strict compilation failed. Evidence is
`raw-attempt1/compile.json` and `attempt1-driver.*`. Successful source was frozen as
`2a02ae97421521848f333c5550fbac74f3b209bf` before the second run.

The run command (both attempts, with first outputs preserved before retry):

```sh
timeout --signal=TERM --kill-after=5s 280s python3 research/manager/hardware-os-20261018/transport/run.py > research/manager/hardware-os-20261018/transport/driver.stdout 2> research/manager/hardware-os-20261018/transport/driver.stderr
```

The shell captured `$?` into `driver.exit` (1 on first attempt, 0 on second).
`run.py` compiles with `gcc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror`, captures
compiler status, runs the ten sessions and corruption control, and checks the
predeclared invariants, exact request counts and exact byte counts. Full absolute
commands are retained in `raw/compile.json` and `raw/*.process.json`.

To reproduce without overwriting retained evidence, copy `echo.c`, `run.py`, and
`PROTOCOL.md` into a new directory inside an independent git worktree, then run
`timeout --signal=TERM --kill-after=5s 280s python3 <new-directory>/run.py`.
Run records will be written beside that copied script. It requires GCC, Linux,
Python stdlib and git; no package or model downloads. Do not use the evidence
directory itself for reruns because the runner writes deterministic output names.
For smallest decisive verification, compile the frozen C source with the same
flags and run one `tcp normal`, one `unix normal`, and one `tcp corrupt` process
session with the same per-process limits from `run.py`; expected exits are 0/0/42.

- `raw/environment.json`: environment, source hashes, quota/affinity, frozen SHA.
- `raw/00-*` through `raw/09-*`: all positive raw request timers (warmups included),
  setup/socket options, parent and child resource use, totals and process exits.
- `raw/10-*`: deliberately corrupted response and expected rejection.
- `raw/summary.json`: asserted counts and descriptive session summaries.
- `driver.*`: whole experiment stdout/stderr/exit.
- `SHA256SUMS`: artifact hashes; excludes itself and ignored compiled binary.
- Binary SHA256 is retained in environment metadata; compile from source to rerun.

Product tests/installations were not run by this worker; manager owns the required
integrated check. No pushes, shared-issue writes, or external downloads occurred.
