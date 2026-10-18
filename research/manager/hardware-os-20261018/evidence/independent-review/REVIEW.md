# Independent review: ACCEPT at bounded research scope

Task `hardware-os-20261018-1801`; reviewer `/root/hardware_validator`.
Frozen revision: `e9f9d08f8bfb5ded804cc5f79fb0f2b4c913b064` in detached
`/workspace/spoj-hardware-review`. Reviewed 2026-10-18 UTC. Exact model/provider
identifiers were not exposed. No children spawned, source changes, installations,
downloads, model runs, remote connections or host changes. Reviewer and authors
are distinct workers on the same host: this is not independent hardware replication.

**ACCEPT** the conditional arithmetic, retained source evidence and local transport
correctness at their stated scopes. No actionable source/manuscript defect found.
Physical inference performance, numerical model correctness, actual device support,
new-OS benefit and hardware purchase/TCO remain **UNRESOLVED**. This is not product
acceptance or merge readiness. The recorded product check failed offline because
Torch was unavailable; native Mac acceptance remains unexecuted.

## Checks and results

1. Checked all source/output hashes in original architecture execution metadata,
   all files in the transport SHA256 manifest and transport environment source
   hashes. Architecture source is `be571681d52f75313642c5f4cb6aa1f3157ae98e4ba5df8bc31906a44a287e6d`;
   inputs `edcc241a1636e7b5dbe099fce67ee69cd78d9235622bd43efe721406db2e3bed`.
2. Reran all eight architecture tests successfully. Full 1,620-row output exactly
   matches original bytes, SHA256 `9fc32da25c70984c66335078cbb288db7fc021ecd6b44f7aa91dbe6a5b2b868b`.
   Independently recalculated every row's six bandwidth/latency quantities and
   conditional classification using separate Fraction expressions in the validator.
   Counts remain 1,248 near-weight conditional wins, 372 without a robust winner,
   zero weight-staging wins. Counts are not workload probabilities.
3. Independently checked `3*4096*14336*2*0.5=176160768` bytes =168 MiB, versus
   `2*4096*2=16384` activation request/result bytes: ratio10,752. Decimal Gb/s
   conversion and 80% efficiency are applied once. PCIe is separately modeled.
   Intervals represent optimistic versus serial assumed pipelines, not measured
   confidence intervals. Full GPU reference is9.6ms for g=.2ms but fit is unknown.
4. **Exploratory adversarial extension outside the frozen grid:** cold32,
   gpu=.2ms, cpu=100ms, line400Gb/s, one flow, RTT=.2ms. Weight staging serial
   =391.8096384ms; near-weight optimistic lower=3209.6ms. This gives a robust
   weight-staging win under the same20% criterion. It challenges any universal
   near-weight recommendation and supports the manuscript's slow-CPU caveat.
   It does not modify the preregistered grid or its counts.
5. Amdahl arithmetic distinguishes latency reduction from speedup: removing5%
   saves at most5% latency, speedup1/.95=1.05263; removing20% gives1.25x, not1.2x.
   Removing half of40% also saves20%. Fractions must be truly removable,
   nonoverlapped time; mean fractions do not establish p99 gains.
6. Inspected frozen C source before execution. Strict GCC flags compile cleanly.
   Ran smallest independent `tcp normal`, `unix normal`, `tcp corrupt`; parent
   exits0/0/42, all child exits0. Positive sessions each contain152 successful
   whole-response verifications; corruption is detected. Each minimal three-run
   experiment transfers18,023,680 application bytes; no full original90MiB suite
   was repeated. Frozen C hash
   `735f77f06a7b7dab408a82248f20662b2a0f1f1b6ad5cc121155d47284a6ffeb`.
7. Independently parsed all original request logs and process statuses:1,520
   correct positive exchanges, exact90,117,376 application bytes including
   warmups and corrupt reply. Verified per-session medians and both128B/16KiB
   order reversals across all five pairs. These observations identify confounding;
   they neither isolate OS instruction costs nor measure physical NIC performance.
   Setup/default socket buffers/verification/fork COW/scheduler effects remain
   disclosed. No reliable tail or inference speedup estimate follows.
8. Retained original compile failure is real: attempt1 return1 under-Werror;
   git diff to successful source changes only the corruption index to127 for
   the predeclared128-byte negative control. No benchmark threshold was altered.
9. Verified12 available original source-document hashes and sizes against source
   manifest; all10 public excerpts match the designated lines of retained text.
   The failed Intel guessed URL has no raw body and is explicitly excluded from
   claims. Original redirected Intel pages are hashed but likewise excluded.
   Public excerpts/hashes are appropriately smaller than wholesale vendor HTML.

## Source and architecture interpretation

- H100 original table column order confirms SXM80GB/3.35TB/s, distinct from
  NVL94GB/3.9TB/s.400Gb/s is50 decimalGB/s raw ceiling, hence3350/50=67 nominal
  byte-rate ratio, not inference speedup. ConnectX-7 document distinguishes
  electrical protocols from optical module protocols; fiber alone changes
  neither scheduling nor GPU coherence.
- GPUDirect originals substantiate root-complex/topology constraints, memory
  registration and ordering, and documented IOMMU constraints. These are
  qualification requirements, not certification of arbitrary consumer devices.
- Current MLX original guide says macOS26.2/TB5 and direct fully connected mesh;
  enabling RDMA requires local recovery setup. Prior accepted pinned repository
  audit records nested JACCL ring implementation. Current packet correctly keeps
  guide/wrapper versus library/version claims separate. Historical JACCL code
  was not newly retrieved/executed by this reviewer; the prior audit was read.
- Cold expert and coarse whole-layer paths are not matched algorithms: the latter
  moves dense/attention/KV and whole-layer residency. Its apparent reduction in
  RPC count is a design bound, not an engine implementation or correctness result.
- No actual GPU/CPU service rates, cache-miss distributions, batch expert unions,
  physical bandwidth, energy or capacity budgets were measured. Coarse latency
  also omits embedding/head/application costs as disclosed. These limitations
  prevent recommending hardware or concluding network dominates GPU.
- Existing runtime/OS mechanisms are strongest-baseline candidates, not measured
  winners. A new OS remains unjustified without a causal real-workload trace and
  evidence that smaller interventions cannot capture the removable fraction.

## Reproducer, enforcement and retained validator failures

`validate.py` contains exact test/compile/transport invocations and assertions.
Each subprocess has256MiB address-space,30s CPU,16MiB file-size, no-core limits;
transport timeout20s and5s socket timeouts. Entire audit had a280s shell timeout
plus5s kill grace. Compiler and grid also receive those limits. Python driver is
not separately RLIMIT_AS-limited, but inputs/output are bounded small files;
no claim of a host-wide memory cap. Each completed full harness attempt took
about0.34s at the outer execution wrapper. Both minimal transport runs total
36,047,360 application bytes, within100MiB. No inference checkpoint was involved.

Two reviewer-harness provenance parsing failures are retained:

- `validate-attempt1.py`, `attempt1-driver.stderr`: all experiments and earlier
  assertions succeeded, then KeyError on optional `extracts` for a no-excerpt
  source row. Fixed only the scratch audit's optional metadata handling.
- `validate-attempt2.py`, `attempt2-driver.stderr`: all experiments succeeded
  again, then attempted to open a raw file for the intentionally failed404 URL.
  This was another reviewer metadata assumption, not a source/evidence defect.
  Experimental reruns stopped after this failure. The successful experiment
  stdout/stderr currently retained are from attempt2; attempt1 experiment logs
  were superseded by deterministic output names, while both audit failures remain.

`audit-retained.py` then completed all arithmetic/hash/source checks by reading
retained experimental artifacts, with **no new subprocess or benchmark execution**.
`audit.stdout` reports PASS for9 checks; `validation.json` records the evidence
and adversarial result. The corrected full `validate.py` is provided as a future
reproducer but was not executed a third time. Exact actual subprocess statuses
were asserted before each metadata failure; the retained C final records also
contain0/0/42 and all child exits. No author files were edited to fix this audit.

Useful files: `unit.stderr`, `grid.stdout`, `compile.stdout/stderr`,
`tcp-normal.stdout`, `unix-normal.stdout`, `tcp-corrupt.stdout`,
`validation.json`, `audit-retained.py`, both failed audit scripts/logs, and
`SHA256SUMS`. Raw source originals remain read-only in
`/workspace/scratch/hardware-sources`; published source metadata is in the frozen
repository `sources/` directory.

Recommendation: PURSUE only the next bounded inventory/real-trace experiment on
an existing authorized machine/model, then compare existing engine/placement and
transport baselines with fixed outputs and end-to-end metrics. UNRESOLVED for
physical advantage, purchase, product acceptance and fresh-OS implementation.
