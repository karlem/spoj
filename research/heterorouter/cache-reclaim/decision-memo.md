# SPOJ: investigate one existing memory/I/O choice

2026-10-18 · **Provisional decision: pursue one upstream configuration experiment;
do not implement an OS, allocator or kernel change.**

**Problem.** For a model larger than RAM, buffered streamed expert loads can
leave file-cache pages resident alongside owned expert-cache slabs. Under memory
pressure, that second reuse tier might displace more valuable residency—or might
be exactly what makes repeated loads fast. SPOJ currently proves a tiny local
MoE execution boundary; it has no trained-model streaming measurement.

**Mechanism.** Pin Colibri `e0db083` and evaluate its existing `DROP` switch,
which issues range `POSIX_FADV_DONTNEED` after expert reads. This changes backing
page retention; it removes neither the read copy nor the owned slab. No new OS
component is necessary. Colibri already has mmap, direct I/O, io_uring,
parallel/pipelined reads, cache-budget tuning and an RSS guard. They must be
qualified first; a faster existing path can invalidate this experiment.
Both switch states already belong to upstream: their winner is part of the
strongest baseline, not evidence that SPOJ outperforms Colibri.

**What the primary source established.** `DROP=0` enables the switch because the
code tests variable presence; the control must unset it. The native timing
replay discards logits. Batched teacher-forcing validation does not alone check
its single-token path, and self-consistency is not an independent oracle.
These details materially change the required controls and acceptance checks.

**What remains unmeasured.** No permitted trained checkpoint was found locally.
The selected recommended GLM-5.2 int4-g64 artifact is documented upstream as
429 GB, versus about 26 GB available workspace storage. There is no artifact
hash/header, actual storage timeline, sustainable bandwidth, affected
critical-path fraction or observed optimization effect. Source-derived g64 byte
geometry and `1/(1-p)` bound are retained, with missing physical inputs null.
Synthetic timings would not close this gap.

**Exact next experiment.** On an existing permitted file-backed host/artifact,
freeze token inputs and an independent same-container oracle, qualify the best
quality-preserving configuration, then compare unset `DROP` with `DROP=1` only
if buffered slabs win. Use pressure/reuse controls, paired sessions, untraced
latency plus residency/reclaim/physical-I/O evidence, and retain failures. Stop
if the measured ceiling is too small, correctness fails, or existing I/O paths
win. Positive evidence could support an upstream tuning/configuration
contribution. No new SPOJ mechanism or novelty is established.

All eleven installed skills have an individual [current-state assessment](skills-review.md).
See [primary source, execution diagram and bounds](README.md), the
[preregistered missing experiment](protocol.md), [actual validation](evidence/validation.json)
and [independent review](evidence/independent-review.md). Review is by a separate
agent in the same session, not an external reproduction. Native Mac acceptance,
multi-machine correctness, speedup, reduced total memory and full-model
capability remain unclaimed.
