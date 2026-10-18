# D2: can tool-wait KV eviction buy useful capacity?

Tracking: karlem/spoj#9. Run `d2-resume-20261018-1531`. Manager `/root`.
Started 2026-10-18T15:31:11Z; stop by 16:01:11Z. Base/prompt pack
`72219b9b4ba769e8d1f88454953d191684355adc`. Researcher `/root/d2_sources`;
independent validator assigned after source and outputs freeze. Serving model
and provider run identifiers unavailable. One complementary hypothesis D2;
D7 physical experiment remains blocked. No product implementation.

## Question, claim and falsifier — declared before execution

For an inference session waiting on an external tool, when can retaining tokens
or exporting KV free the constrained memory resource without an unacceptable
resume delay? Hypothesis: existing eviction/reconstruction mechanisms have
conditional useful regions, not a universal advantage or a new SPOJ mechanism.

This is **inferred arithmetic evaluated on assumed inputs**, not model execution,
real tool traces, an empirical latency distribution, or a physical benchmark.
We will reject a universal suspend/export recommendation if short waits, slow
transfers, the same physical memory domain, or cheaper replay defeat it.

Illustrative economic screening gates, not approved product SLOs:

- At least 25% reduction in *KV occupancy-time during the original tool wait*
  in the constrained physical capacity domain.
- At most 250 ms added time from tool completion until inference can resume.
- Report all transfer bytes, checkpoint capacity, transient capacity, and
  conservative post-return KV occupancy charges; do not call saving GPU memory
  a reduction in total system memory.
- Correctness is a separate **UNVERIFIED** gate. No economic candidate is an
  accepted inference result. Different model/backend/state formats must fail
  compatibility screening; compatible metadata alone does not prove parity.

## Model and strongest-baseline limitation

Compare keep-resident, drop KV/replay exact retained tokens, and full KV
export/restore. Pinned ServerlessLLM and a practical upstream session implementation
will qualify whether these mechanisms already exist; neither can be physically
benchmarked here. A cost formula is not a reimplementation or an optimization
against those systems. Warm shared weights stay resident for **all** policies.
No per-session credit for releasing shared model weights. Fixed model/backend,
token IDs/positions, sampler state and application/tool state must be preserved
before a real cycle could count. Replay feeds retained tokens rather than
resampling history. Numerical equivalence is not established here.

Dense full-context KV payload `S = 2 * layers * kv_heads * head_dim * bytes * tokens`.
This is explicitly a GQA layout assumption, not MLA/sliding-window/quantized
KV or a measured model. Metadata, allocator rounding and backend buffers are
not included in S; their absence makes the capacity estimate optimistic.
All policies retain token IDs (4 bytes/token assumption) plus unmodeled
sampler/application metadata. Nothing allocates an S-byte payload in this test.

Let `W` be the external tool wait, `E = 5 ms + S/Bwrite` the complete export,
`R = 5 ms + S/Bread` complete restore, and `P = 20 ms + tokens/prefill_rate`
token reconstruction. Assumed effective rates include payload movement only;
fixed overheads are illustrative. No overlap, compression, prefetch, batching,
contention, cancellation or advance knowledge of W. Export starts immediately
at pause, keeps source KV live through E, and completes even if the tool returns
early. Restore begins at max(W,E); no background generation happens.

Resident: wait occupancy S*W, added resume delay 0.
Replay: instant KV release (optimistic), wait occupancy 0, added delay P.
Export to a separate capacity domain: wait occupancy S*min(W,E), added delay
max(E-W,0)+R. Export within the same physical memory domain has wait occupancy
S*W at best (source replaced by checkpoint): **zero credited physical saving**.
For that case, logical device allocations are not additional physical capacity.

Export creates an S-byte checkpoint and moves 2*S bytes over a full cycle. Its
source and destination coexist at end of export, so conservative peak total
KV/checkpoint payload is 2*S. With a separate target, source-domain peak is S;
with one physical domain, peak is 2*S. RAM vs storage residency must be recorded
in a real run; checkpoint bytes do not automatically mean resident RAM. Replay
has zero KV transfer but must reread/use weights and perform prefill work; those
costs are represented only in its assumed effective rate. No energy claim.

Conservative source KV occupancy-time *after* tool return is charged as S*delay
for replay/export (full-size reservation throughout reconstruction/restoration).
This is reported separately from wait savings, **not subtracted as a causal net
benefit**: different readiness times and subsequent useful work make that
subtraction an unmatched comparison. Concurrent throughput needs actual traces.

Useful bounds: 25% wait-saving requires W >= E/0.75 for separate-domain export;
then E<W and the resume gate additionally requires R<=0.250 s. An export that
finishes after tool return cannot meet the wait-saving gate. Replay needs
P<=0.250 s; retaining tokens alone is not novel. An economic pass on any cell
permits only later real correctness/trace qualification, not a product decision.

## Frozen synthetic sensitivity grid and controls

- Layers 32, KV heads 8, head dimension 128, scalar bytes 2.
- Context lengths 8,192; 32,768; 131,072 tokens.
- Tool waits 0.05; 0.25; 1; 5; 30; 120 seconds.
- Symmetric effective export/restore bandwidth 0.5; 2; 8; 32 GiB/s.
- Prefill rates 2,000; 20,000; 100,000 tokens/s.
- Separate and same physical capacity domains. 432 deterministic cases.
- Negative controls: incompatible backend state; nonpositive/NaN inputs;
  tool return before export completion; same-domain false capacity credit;
  a boundary case at exactly the 25%/250ms thresholds.

All cases are a parameter sensitivity grid, **not a workload distribution**.
Counts cannot estimate fleet benefit, likelihood of a long wait, or p95/p99.
No fitted parameters, random seed, repeated timing or statistical CI is useful
for this exact arithmetic. Inputs/results are saved with SHA256 manifests.

## Execution, review and stop rules

Python 3.12 stdlib only. No external project execution or dependency install.
Each command <=300s, address space <=2GiB, bounded output below 100MiB; enforce
limits using resource limits and timeout. Retain stdout/stderr, exit codes,
timestamps and environment. Validate hand-computable cases and compare full
reproduction JSON, then independent worker checks formulas/cost accounting and
reruns frozen source in a separate scratch directory on this same host.

Run required product scripts/check.sh offline within budget; unavailable
dependencies mean a disclosed failed/unrun product gate, not waived acceptance.
No source/product change or merge-ready claim. At two failed attempts or two
cycles without new evidence, stop. Publish a bounded decision memo and evidence,
with one next real-trace assignment. Do not restart blocked D7 or SSH work.
