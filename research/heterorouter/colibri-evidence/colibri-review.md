# Independent Colibri/capacity source review

Read-only review of research/heterorouter/capacity-and-colibri.md and colibri-source-manifest.json against selected upstream primary source files in /workspace/scratch/colibri-study. No Colibri compilation, tests, model download, inference, benchmark or network execution. No repository edits.

## Outcome

APPROVED as static source research and clearly marked research proposals. No blocking factual findings.

Independently recomputed SHA256 and byte lengths for all 16 manifest files: each matches. Manifest pins JustVugg/colibri e0db083cdc9e563e0766cc6fc661ef23c32298e0. These hashes verify inspected local selected files against the saved manifest; upstream retrieval provenance is the recorded parent process, not a new independent network fetch.

## Checked claims

- colibri.c cluster_moe_batch at 3414 assigns (expert_id+layer)%worker_count, builds per-expert row items, sends one worker request and reads its response before proceeding to the next worker. Coordinator retains and applies gate weights to returned unweighted expert outputs.
- cluster_worker_run allocates one ESlot per layer (including the extra layer slot), reloads a slot miss from model storage and calls expert_ffn. Its entry point initializes model configuration/storage rather than ordinary tiered GPU engine initialization. The documented claim is correctly scoped to this inspected GLM path, not all architectures/backends.
- docs/cluster.md explicitly requires the same converted model locally and describes persistent TCP delegation with coordinator generation/routing/KV. No disjoint full-model storage or adaptive bandwidth-aware scheduler is established.
- tier.h score is (heat<<8)|recent, with recent=max(255-age,0); because ranges do not overlap this equals256*heat+recent. LFRU promotion requires greater than cold score+floor(cold/4)+1024. repin_pass_limit halves session heat at the pass end.
- route_trace.h rt_decay defaults to1.0 (no change); optional COLI_USAGE_DECAY scales persistent counters when rt_save runs. The draft appropriately distinguishes this from stale no-decay documentation.
- repin_pass wrapper at7970 passes16, not the four-swap prose bound. Other call sites have separate limits. CUDA promotion at9755 uses hh>ch+1, so the draft correctly avoids a universal LFRU25%-margin claim.
- autotune default min_gain=.03; hit gate allows0.5percentage-point loss; p99/TTFT permit20% regression when present. Missing baseline/trial metrics make these gates nonblocking. Winner is confirmed before a later baseline. Serving-output drift rejects a candidate; no universal semantic-quality or speed guarantee is claimed.
- CACHE_ROUTE.md distinguishes changing expert IDs from PILOT prefetch; the proposal correctly keeps approximation outside the existing strict-parity contract.

Capacity accounting, move-activations-versus-weights comparison, safe migration sequence and future policy comparisons are explicitly proposals, not observed implementation/benchmark outcomes.8192float32 elements give32KiB per row; two rows give64KiB, and100MiB/64KiB=1600. Unified-memory non-additivity and attention/router/KV/workspace/headroom reservations correctly prevent aggregate-byte sums from being presented as sufficient feasibility proof.

## Nonblocking precision note

The hardware/model/engine tuning fingerprint in autotune.py hashes an identity payload containing model paths/file sizes/mtimes, engine size/mtime and selected hardware fields; it is not a cryptographic content digest of model/engine artifacts. The draft does not claim otherwise, but avoid strengthening this wording into immutable artifact validation later.
