# Source research command record

Date 2026-10-18 UTC; task hardware-os-20261018-1801/hardware-sources.
Only local-authored Python stdlib retrieval/extraction ran. External source/model code was not executed. Default per-source HTTP timeout25s and maximum body1MiB; actual retained raw bytes are recorded in summary.json. Eight source families; multiple Linux memory subpages and IX license are from those families. No installs or host changes.

Read `/workspace/spoj-hardware/AGENTS.md`, `docs/engineering/factory.md`, manager README/PROMPTS (Common contract, researcher, D5/D7). Read prior D2 report. Prior D7 memo/protocol extracted with:

```
git show c6cefdd90f6fe1f80d71c024e52065eb1147e826:research/heterorouter/cache-reclaim/decision-memo.md
git show c6cefdd90f6fe1f80d71c024e52065eb1147e826:research/heterorouter/cache-reclaim/protocol.md
```

Output was saved by local Python subprocess to `prior-decision-memo.md` and `prior-protocol.md` (exit0).

Successful retrieval/extraction scripts (Python3.12 stdlib):

```
python /workspace/scratch/hardware-sources/fetch.py
python /workspace/scratch/hardware-sources/followup.py
python /workspace/scratch/hardware-sources/final_fetch.py
python /workspace/scratch/hardware-sources/extract.py
```

All four scripts exit0; HTTP source failures/redirects are individually retained in manifest.json and are not successful source evidence. Scripts `fetch.py` and `followup.py` freeze the URLs used; `extract.py` strips HTML script/style and retains text with deterministic line boundaries. Selected text was inspected with `rg -n` and `sed -n`. Manifest retrieval timestamps are UTC request-start timestamps, not publication dates. Mutable upstream pages were not assigned fictitious commit revisions.

One exploratory inline helper execution failed exit1 before the successful `final_fetch.py`: using `exec` on the fetch helper under stdin left `__file__` as `<stdin>`, so its path resolved to the wrong directory. It attempted to read `manifest.json` there and raised `FileNotFoundError`. No additional source evidence was accepted from that invocation. The exact visible traceback is retained in failures.txt. A corrected fixed scratch path was used in final_fetch.py; this did not change the source claims. The two Intel newsroom redirects and guessed Intel product404 remain negative retrieval records.

Source inventory and calculations were inspected manually; no claims of independent validation, product tests or physical inference arise from this source task. Manager must arrange separate review. Local SHA256SUMS covers retained report/scripts/raw evidence; it excludes itself. `public-evidence.json` contains source URLs, sizes, hashes, status/failures and selected short extracts for manager publication without full vendor-page mirroring.
