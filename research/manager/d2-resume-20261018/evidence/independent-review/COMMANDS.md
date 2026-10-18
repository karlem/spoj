# Exact reproduction commands

Run from frozen `/workspace/spoj-d2-review`, commit `ad562a27560091abac92c3af38cb6062969f4ae0`.

Original independent rerun (output directory must be new):

```bash
mkdir -p /workspace/scratch/d2-validator
python -B research/manager/d2-resume-20261018/run_evidence.py /workspace/scratch/d2-validator/rerun > /workspace/scratch/d2-validator/runner.stdout 2> /workspace/scratch/d2-validator/runner.stderr
```

The frozen runner records each exact subprocess, timing, exit, source/output hashes and resource limits in `rerun/execution.json`. Both commands succeeded; unit suite ran 9 tests. It does not execute any upstream source.

Independent oracle + manifest + adversarial audit (scripts in this bundle):

```bash
python -B /workspace/scratch/d2-validator/run_audit.py
```

This invokes `/workspace/scratch/d2-validator/review_checks.py` with resource limits and a 300-second subprocess timeout. Audit command, exit, runtime and hashes are in `audit-execution.json`. Audit was also initially run through `timeout 300 python -B ...` before adding explicit candidate-count assertions, then the complete final script was run through `run_audit.py`. Both runs passed. Current raw output is from the complete final script.

Only validator scratch files were written. Evaluated source remains unchanged; no dependencies/network/model required.
