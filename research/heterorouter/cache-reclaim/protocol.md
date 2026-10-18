# Exact missing experiment: retain or discard copied expert backing pages

Status: **not executed**. This is the preregistration template for the one study
in [the decision memo](README.md), not runnable evidence or permission to acquire
a model/host. No substitute weights, synthetic storage speed, machine purchase
or full-model generation is part of this packet.

## Gates before an experiment can count

1. An already permitted copy of the recommended GLM-5.2 int4-g64 container must
   exist on actual file-backed storage. Record repository revision, license,
   full content-hash manifest, tokenizer/config hashes, per-tensor shape/offset/
   length/fd and format/scale geometry. Check that routed gate/up/down tensors
   resolve to g64; do not assume every model tensor has the same format. Check
   contiguous same-file weight ranges for the synchronous path. A failure is a
   blocked experiment, not authorization to repack or bypass a format guard.
   Hash before cache preparation; a full-file hash itself warms file pages.
2. Pin engine `e0db083cdc9e563e0766cc6fc661ef23c32298e0`; record the complete build
   command, compiler/runtime versions, binary hash, target ISA, linked allocator,
   flags and startup decisions. The inspected upstream CPU build target is
   `make -C c glm`; actual compiler/backend support must be verified there.
   Retain failures. No alternate precision or fast-math kernel is introduced.
3. Record physical CPU/NUMA topology, quota/affinity, RAM/swap, filesystem/mount,
   model inode/extent layout, storage/controller path, available bytes, power
   policy and other device users. Do not identify real NVMe from a guest label.
   Use an isolated existing test host/cgroup if available, without disabling
   resource guards or affecting other users' page cache. A 32 GiB RAM limit does
   not create the missing hundreds of GB of persistent model storage.
4. Freeze one code-explanation prompt, e.g. “Explain why an asynchronous expert
   loader must complete before a token's weighted expert result is accumulated.”
   Tokenize once with the pinned real tokenizer; retain exact UTF-8 and token
   IDs. Supply a fixed 64-token continuation from the same task's permitted
   reference fixture. The experiment never generates a continuation. Record
   `prompt_ids`, `full_ids`, vocabulary and lengths; do not reuse the tiny oracle.
5. Obtain an **independent oracle for the effective weights in this exact
   quantized container**, with provenance. The existing
   [`make_glm_oracle.py`](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/c/tools/make_glm_oracle.py)
   illustrates HF quantize/dequantize round-trip references only for a tiny
   random fixture. It does not supply this oracle. An original FP8 model's
   predictions alone are not a g64 oracle. Before timing, both arms must pass
   same-container teacher-forced predictions/finiteness with zero allowed
   mismatches, and unchanged router IDs/weights on retained selected steps.
   Retain expected and actual predictions. Compare actual runtime weight/scale
   bytes with an independent file-range reader as a separate load-integrity
   check; that hash check alone is not numerical correctness.

Native teacher-forcing validation accepts `tf_pred` (one prediction for every
`full_ids` position); `c/oracle.h` validates its shape/range/prefix. Use separate
processes for correctness and timing. The native strict mode deliberately
rejects combination with `REPLAY`; do not suppress that rejection or report a
replay exit 0 as a strict oracle pass. Conceptual commands, **not run**:

```sh
# The named variables and frozen CPU/loader/cache environment require real metadata.
# Do not set REF_FORCE or a nonzero ORACLE_TF_MAX_MISMATCHES.
env -u DROP -u REF_FORCE ORACLE_STRICT=1 TF=1 SNAP="$SPOJ_MODEL" REF="$SPOJ_ORACLE" \
  "$SPOJ_ENGINE" "$SPOJ_CAP" "$SPOJ_EBITS" "$SPOJ_DBITS"
env -u REF_FORCE ORACLE_STRICT=1 TF=1 DROP=1 SNAP="$SPOJ_MODEL" REF="$SPOJ_ORACLE" \
  "$SPOJ_ENGINE" "$SPOJ_CAP" "$SPOJ_EBITS" "$SPOJ_DBITS"
```

If quantized math and the independent reference disagree, diagnose and publish
the mismatch before changing the acceptance contract. Do not transfer SPOJ's
Qwen float32 tolerances (`rtol=1e-5, atol=1e-6`) to an unverified GLM quantized
path. They remain unchanged for the existing proof. No independent trained-model
oracle result is available today.

## Qualify the strongest applicable existing engine

First reproduce the candidate methods in the pinned upstream tuner: applicable
thread/NUMA settings, PIPE and reader count, direct I/O and smaller expert-cache
budgets while preserving dense/KV/workspace/OS reserves. Also qualify existing
mmap and Linux io_uring if supported by this build/platform and the same oracle.
This is bounded baseline selection, not new engine implementation. Save each
candidate's raw outputs, failures and full configuration; don't equate the
coordinate-descent tuner's result with an exhaustive optimum.

The unmodified GLM tuner generates calibration tokens and sets `REF_FORCE`.
Those actions conflict with current constraints. Use its inspected candidate
logic with the independently supplied fixed replay instead; do not call
`create_replay`, set a force flag, download weights or claim a tuner run occurred.

Select by paired end-to-end outcomes, under the identical quality contract and
memory limit. Keep TTFT/prefill and decode separate, as well as total cost. A
native replay does not expose user-visible first-generated-token latency;
report time to first forced step as such. If direct/mmap wins, stop the proposed
buffered weight-page-retention comparison for that regime. Direct fallback and
buffered scale traffic still need path verification. A slower buffered-only A/B
is not evidence of advantage over the winning engine.

For a winning buffered-slab regime, freeze its complete configuration. **Only
`DROP` presence changes:** A unsets it; B sets `DROP=1`. `DROP=0` enables it too.
Keep file layout, kernel path, threads, loader backend, prompt, tokens, budgets,
adaptive-policy settings, starting cache history and request concurrency fixed.
Record RSS-guard/cache-controller actuations as possible mediators, including
their overhead; do not silently disable existing safety logic. io_uring's advice
is per completed read, so don't apply the synchronous path's four-call assumption
unless actual traces establish that geometry.

## Measurements and bounds before changing implementation

Use uninstrumented end-to-end timings and low-cost per-run counters first. For
one selected expert miss, correlate request/token/layer/expert/slot IDs with
loader enqueue/start/end, range read, advice, ready publication, consumer wait
and contribution completion. Record monotonic clock domains and any lost events.
Capture two fixed decode positions and two fixed layers, capped at 32 misses;
retain full-range hashes plus bounded value samples, not an unbounded tensor dump.

| Measurement | What it distinguishes; limit |
| --- | --- |
| `/proc/PID/io` rchar/syscr versus read_bytes, cgroup `io.stat`, block issue/completion events | Logical operations versus actual guest block traffic. Shared devices/stacking can confound attribution; neither alone proves host physical media service. |
| smaps_rollup RSS/PSS/anonymous/file, cgroup anon/file/events, sampled file residency | Allocated capacity versus resident bytes, potentially competing caches. cgroup file charging follows ownership/first touch; verify sharing and attribution. `mincore` presence is not a future-hit guarantee. |
| PSI, reclaim/page-fault events, CPU samples and off-CPU/scheduler traces | Pressure and stalls versus CPU service. A page-cache miss serviced by `pread` is not necessarily a userspace major fault. |
| Loader timestamps and device queue/issue/completion intervals | Work waiting for a reader, loader elapsed service, device queue/service, and exposed consumer delay are different intervals. Never sum overlapping durations into a request latency. |
| Raw end-to-end session/prefill/64-step/repeat times and failures | Whether a mechanism change matters to the fixed workload after initialization, adaptation, and cleanup. No full-model-generation capability is inferred. |

Use perf/software/hardware events and kernel/eBPF tracepoints **only where
supported**. Start at a low sample rate; record symbols, lost samples and event
availability. For CPU-only this needs neither Nsight nor Instruments. Neither
tool nor profiling permissions are assumed here. Compare untraced, counters-only
and traced matched runs: flag >2% paired elapsed-time perturbation and estimate
uncertainty. If overhead is material or uncertain, keep the trace explanatory
and use untraced runs for the effect size. Add no optimization while tracing.

Fill [bounds.json](evidence/bounds.json) from actual range bytes, matched sustained
read throughput and **exposed** affected critical-path time. Derive maximum
benefit after overlap; include advice CPU/LRU-drain cost and lost file-cache
reuse. If even the ideal bound cannot support a preregistered useful gain, stop.
The current missing inputs prevent a credible numerical speedup ceiling.

## One-factor comparison, controls and statistics

Vary the implicated constraint, not the architecture: three recorded memory
limits at 1.00, 0.85 and 0.70 times a preselected safe limit, above measured
dense/KV/workspace needs. If a limit is unsafe or cannot be imposed, mark that
cell unavailable; do not crash repeatedly or lower safety reserves. Qualify the
strong baseline separately at each limit; freeze it for each cell's A/B.

Within each fresh-process paired session, measure initialization and first
replay, then the identical replay again to expose warm reuse. Record resident
state before each phase. Do not call a run “cold” unless a targeted, private-file
cache preparation succeeds and sampled residency confirms it. File-range advice
is advisory; do not use global `drop_caches` on a shared machine. Retain every
failed preparation. If warm-state matching cannot be established, report it and
do not infer a cold/warm causal result.

Run 4 paired pilot sessions for observability/bounds, excluded from the final
effect estimate. If gates pass, preregister 20 fresh-process A/B pairs per
eligible memory cell with balanced randomized AB/BA order and a saved seed.
Include a matched A/A null-control set (at least 10 pairs). Repeated forced steps
within a process are correlated; the independent unit is a paired session, not
each token. Report raw samples, paired session-time differences and a paired
bootstrap 95% interval (10,000 resamples, saved seed), failures and memory peaks.
With only these sessions, do not claim a reliable p99. If uncertainty is too
large for the decision threshold, conclude inconclusive rather than keep sampling
until significant. Report startup-inclusive and steady replay outcomes separately.

Negative controls: low-pressure cells should not show the proposed reclaim win;
the exact repeated input can expose lost file-cache reuse where owned-cache
eviction actually occurred; A/A should show run-order noise. Direct/mmap winners invalidate applicability rather than
serve as artificially disadvantaged arms. Track advice calls/return values,
actual removed/resident pages, physical read traffic, cache hits, controller
decisions, transient memory, unused speculative bytes, errors, timeouts and
bounded cleanup. No failures disappear from the denominator.

## Independent decision

Before data collection, fix the useful-gain threshold (suggested default: a 5%
reduction in startup-inclusive session time) and reject any correctness failure.
Pursue an upstream configuration/tuning contribution only if the paired interval
excludes zero, the prespecified threshold is met, and lower exposed pressure
stalls explain the outcome after accounting for overhead/re-reads. State the
specific winning memory/reuse region and every losing cell. An unchanged end-to-end
result, no pressure, ignored advice, or a better existing I/O path supports
rejection. No present result establishes any of these outcomes.

An independent reviewer must recover pinned source/hash manifests, validate the
real model/oracle and baseline selection, reproduce cache preparation and at
least one winning and one losing/control cell, check raw failures, recompute the
paired statistics and reconcile counter/timeline attribution with elapsed time.
This packet's [review](evidence/independent-review.md) covers only source analysis,
readiness evidence and experiment design. Mac acceptance, multiple machines,
total-memory reduction, speedup and useful assistant quality remain unclaimed.
