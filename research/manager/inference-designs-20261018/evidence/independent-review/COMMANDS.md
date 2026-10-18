# Reviewer commands

All author/source reads used the frozen detached review tree or source-worker
scratch. Only `/workspace/scratch/inference-validator` was written.

```sh
python3 -B /workspace/scratch/inference-validator/run_review.py
```

This ran the exact two commands recorded in `execution.json`, with enforced child
limits and captured stdout/stderr. `audit.py` reads retained original source bodies
from `/workspace/scratch/inference-fundamentals` and
`/workspace/scratch/inference-prior-art`; those full third-party originals are not
part of the public packet. Reproduction elsewhere requires retrieving the pinned
URLs and preserving their expected hashes, or supplying those captured sources.

Read-only repository checks:

```sh
git -C /workspace/spoj-inference-designs-review rev-parse HEAD
git -C /workspace/spoj-inference-designs-review diff --check 72219b9b4ba769e8d1f88454953d191684355adc..HEAD
git -C /workspace/spoj-inference-designs-review status --porcelain=v1
```

All exited 0; HEAD was `f9730ed4c6e0ee15b063320d4359645acd904f34`, whitespace
check output and status output were empty. The already captured failed offline
product check was inspected, not rerun or bypassed.
