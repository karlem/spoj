# Fundamentals review: persistent inference state and KV-owning attention workers

Run: `inference-designs-20261018-1841`. Worker: `/root/inference_fundamentals`.
Harness: Codex collaboration child; model identifier unavailable. Research only;
no product implementation, new infrastructure, physical inference experiment, or
performance result. This worker authored the analysis; independent review is pending.

## Evidence and use of the requested skills

`karlem/skills` is pinned at
[`c41b2b27c91da7155d555eb4946ece348ac08657`](https://github.com/karlem/skills/tree/c41b2b27c91da7155d555eb4946ece348ac08657).
I read nine SKILL.md files, the focused references below, and the book-coverage
record. The repository explicitly says every book has **partial coverage** and
no authorized full edition was available. These are source-backed engineering
procedures, not evidence that this run read or validated whole books. This run
also directly read the primary material identified under P1–P3 below.

| Skill and focused reference | Procedure actually applied here |
| --- | --- |
| [architecture-patterns](https://github.com/karlem/skills/blob/c41b2b27c91da7155d555eb4946ece348ac08657/architecture/architecture-patterns/SKILL.md), selection and fitness | Replace “agent aware” with stimulus/environment/response/measure scenarios; compare a single-process design before distributed deployment. |
| [architecture-tradeoffs](https://github.com/karlem/skills/blob/c41b2b27c91da7155d555eb4946ece348ac08657/architecture/architecture-tradeoffs/SKILL.md), boundaries | Locate atomic ownership changes and chatty dependencies; count serial calls and failure surfaces. |
| [distributed-systems](https://github.com/karlem/skills/blob/c41b2b27c91da7155d555eb4946ece348ac08657/architecture/distributed-systems/SKILL.md), failure-ledger and consistency | Name authoritative state, commit/ack boundaries, operation identities, stale-owner fencing, and crash windows. |
| [concurrent-programming](https://github.com/karlem/skills/blob/c41b2b27c91da7155d555eb4946ece348ac08657/concurrency/concurrent-programming/SKILL.md), correctness and progress | Define a sequential object contract; construct harmful interleavings; separate linearizability, reclamation, and liveness. |
| [systems-programming](https://github.com/karlem/skills/blob/c41b2b27c91da7155d555eb4946ece348ac08657/engineering/systems-programming/SKILL.md), memory and I/O | Give each allocation an owner, extent, aliases, and release condition; handle partial transfers and bounded framing. |
| [production-reliability](https://github.com/karlem/skills/blob/c41b2b27c91da7155d555eb4946ece348ac08657/reliability/production-reliability/SKILL.md), retries and containment | Bound active and waiting work, include queue time in deadlines, separate cancellation from reclamation, and prevent retry amplification. |
| [network-engineering](https://github.com/karlem/skills/blob/c41b2b27c91da7155d555eb4946ece348ac08657/networking/network-engineering/SKILL.md), paths and transports | Count serial RTTs, payload bytes, in-flight credits, and acknowledgment meaning; distinguish bandwidth from latency. |
| [linux-performance](https://github.com/karlem/skills/blob/c41b2b27c91da7155d555eb4946ece348ac08657/performance/linux-performance/SKILL.md), experiments | Set measurement boundaries; include failures, offered load, growing queues, resource cost, matched baselines, and Amdahl/Little limits. |
| [systems-profiling](https://github.com/karlem/skills/blob/c41b2b27c91da7155d555eb4946ece348ac08657/performance/systems-profiling/SKILL.md), profiles | Attribute CPU time, runnable delay, device time, and suspended logical tasks separately; do not call event-loop idle time request latency. |

The designs and thresholds below are **proposals derived from these procedures**.
The skills do not establish inference novelty or measured advantage.

## H1: persistent branch/state graph

### Mechanism and smallest useful structure

Represent a session as an owner-serialized graph of immutable prefix pages and
private append tails. Expose `fork`, `append`, `suspend`, `resume`, `cancel`, and
`release` against an expected branch version. Use one owner event loop or short
mutex-protected metadata operations first; no custom lock-free allocator is
justified before contention evidence.

Each branch records identity, parent/prefix root, committed token length, version,
state, owner generation, outstanding operations, and admission reservations. A
replayable execution snapshot also needs model/adapters, token positions and
attention rules, KV format/precision, and sampling/RNG state. A token/KV snapshot
alone is not an application or tool-effect snapshot. Forking independent random
streams is an explicit API choice; cloning one RNG state silently can make
branches produce identical draws.

Share only state whose full semantic identity matches: model and adapter identity,
prefix tokens and positions, cache format and numerical contract, and applicable
isolation domain. A content hash is an index, not permission to disclose another
tenant's state. Matching only text or token count is insufficient. Appending a tool
result changes the branch's prefix; it does not allow arbitrary hidden-state reuse.

### Sequential contract and ownership

| Operation | Proposed atomic metadata effect | Physical work and lifetime |
| --- | --- | --- |
| `fork(parent, expected_version, operation_id)` | Validate identity/version; reserve capacity; publish child and its page references together. | Shared pages remain immutable; partial final page uses copy-on-write before mutation. |
| `append(branch, expected_version, operation_id)` | On completed/validated compute, publish the new token/KV prefix and next version together. | Compute writes staged private state. Old version remains authoritative until publication. |
| `suspend` / `resume` | Record the permitted state transition and remaining budget. | Suspension does not by itself checkpoint, offload, or release KV. Those require separate explicit operations. |
| `cancel` | Publish cancellation/tombstone so subsequent result commits fail validation. | Stop new work; already launched kernels/transfers may continue. Return a distinct “drained” completion only after resource use ends. |
| `release` | Remove the graph edge under the same ownership protocol. | Reclaim only after graph references, outstanding read/write pins, transfers, and possible publishers are all gone or safely fenced. |

A successful metadata operation must correspond to a legal sequential history
respecting nonoverlapping operations (P1). That is a correctness specification,
not a claim that this proposed implementation has been proved linearizable.

**Safety invariants:** (1) a visible branch version names one mutually consistent
token/KV prefix; (2) immutable pages never change while shared; (3) no result from
an obsolete version or canceled generation commits; (4) physical storage cannot
be reused while any CPU/GPU/NIC operation can still access it; (5) page references,
reservations, and publication change under one authoritative protocol; (6) an
operation ID replay with different parameters is rejected.

**Admission invariant:** uniquely resident bytes + promised private growth +
working/staging buffers + bounded message queues + metadata + reserved drain or
quarantine capacity must fit the selected pool budget. Account actual allocation
granularity and quantization metadata. A page reference count of zero is not
permission to reclaim a page still pinned by a device. Count reservations exactly
once and bound both admitted branches and waiting requests. Require maximum
generation length or incremental admission; unbounded future tokens cannot be
reserved in finite memory.

**Liveness assumptions:** each admitted operation has finite work, the owner and
devices make progress, ready work receives fair service, and external waits have
an explicit deadline or cancellation policy. Deadlock freedom alone does not
ensure a branch finishes. A hung device may force quarantine or process/device
recovery; do not promise bounded normal reclamation when completion cannot be
established. Bound quarantine and stop admission instead of reusing unsafe pages.

### Small counterexamples to test first

1. Fork reads a prefix pointer; concurrent cancel drops the last reference and
   frees it; fork publishes the stale pointer. Fix by serializing reference
   acquisition/publication with release, not by making just the counter atomic.
2. Kernel starts reading page A; cancellation frees A; allocator gives its address
   to branch B; A's kernel or DMA accesses B's data. Fix with in-flight pins and
   completion-aware reclamation. A tagged pointer can detect ABA yet still leave
   this use-after-free unsafe.
3. Append computes at version v; cancel commits; delayed completion publishes v+1.
   Fix by validating the version and cancellation state at publication.
4. Tool effect commits remotely; response is lost; resume retries under a new ID.
   Duplicate external effects are possible. Keep tool operation identity and
   reconciliation outside the inference-state commit unless a real shared
   transaction boundary exists. Do not claim exactly-once tool execution.

### Memory bound, baseline, and rejection

For shared prefix storage P and k branches each retaining private suffix S,
ideal data storage is `P + k*S` versus `k*(P+S)` for full duplication. Ideal saving
is `(k-1)*P`, before page slack, metadata, snapshots, staging, and pinned retired
pages. This is an accounting bound, not novelty: paged/prefix-sharing engines may
already realize it. Compare against their strongest available configuration,
including ordinary copy-on-write and prefix caching, not a forced full-copy
baseline. Reject H1 as a performance contribution if lifecycle integration cannot
improve completed-task cost beyond that baseline, or synchronization and retention
erase the gain. Correctness and explicit interfaces can still be useful engineering.

The companion literature assignment identifies SGLang's fork/prefix-cache support
and Parrot's application dependency treatment as concrete comparison targets. Their
pinned capability evidence belongs in that companion report; this worker has not
independently inspected those implementations. These existing features mean that
“supports branches and application dependencies” is not a novelty claim by itself.

## H2: KV-owning attention workers

### Mechanism and scope

Keep model weight computation at the coordinator or existing execution engine.
Partition a sequence's KV positions among workers. For each layer and query,
dispatch Q to those owners; compute local attention summaries where KV resides;
combine the summaries; return the attention result to the next model operation.
This investigates KV locality/capacity and memory bandwidth. It is **not** a
solution to weight capacity, transparent remote RAM, or an established performance
win. Start with explicit messages over qualified transport; RDMA changes the
transport implementation and lifetime obligations, not the state contract.

For a shard with allowed score set x and value vectors v, compute
`m = max(x)`, `l = sum(exp(x-m))`, and `u = sum(exp(x-m)*v)`.
Combine shards using `M = max(m_i)`,
`L = sum(exp(m_i-M)*l_i)`, `U = sum(exp(m_i-M)*u_i)`, result `U/L`.
This is the exact-real algebra for a partition of one attention operation.
Floating-point order, accumulation precision, quantization, and kernel choices
change numerical results; require declared tolerances and downstream quality
checks. The companion literature worker should establish closest inference prior
art; this worker does not assert novelty for the reduction.

### Protocol invariants and failure ledger

Each request and response carries session/branch/version, model and mask identity,
layer/head shape, committed prefix length, query operation ID and fingerprint,
partition-map generation, owner generation, and exact position range. The
coordinator accepts one matching contribution for each disjoint range that exactly
covers the visible allowed prefix. Duplicates, overlap, gaps, wrong generations,
and changed parameters are errors. Causal/window masks and position encoding must
match the baseline; not every stored position is visible to every query.

Append K/V to its position owner in staged storage. Publish its readable committed
prefix only after the required device/transfer completion. A query observes a
stable prefix; it cannot combine half of an append with an old shard. Migration
copies/validates state and switches an authoritative generation while fencing old
owners; simple lease expiry cannot prevent a paused worker from later responding.
The smallest prototype can omit migration and fail a request on worker loss.

| Failure/interleaving | Required behavior |
| --- | --- |
| Slow or lost shard | Wait within remaining deadline or fail/retry the same logical query; never silently substitute zero while claiming exact attention. |
| Empty valid shard | Use an explicitly defined empty summary; avoid `-inf - -inf` NaNs. Distinguish “has no visible keys” from “did not respond.” Define all-masked behavior against the baseline. |
| Response lost after computation | Duplicate computation may be safe; accept at most one contribution under the same operation identity. Do not count retries as useful throughput. |
| Stale response after migration/cancel | Validate generations at the coordinator and reject; old writable authority must also be fenced at the protected resource. |
| Cancel during send, kernel, or DMA | Stop admission and future commits; retain buffers/pages until completion or documented device recovery establishes safe reuse. |
| Congested donor or stalled receiver | Enforce byte and operation credits at both ends; cap queued age; propagate remaining deadline; prevent one branch from occupying all slots. |

The Linux DMA API (P2) specifically requires waiting for DMA activity to finish
before unmapping; coherent DMA memory still requires appropriate ordering
barriers. These establish why lifetime/ordering is real work. Actual CUDA, verbs,
driver, and NIC APIs need their own version-specific completion/coherence review;
Linux driver guidance is not a substitute for those contracts.

### Bytes, work, and serial dependency bounds

Let N be visible tokens, hq query heads, hkv KV heads, d head dimension, and s the
bytes per stored KV element. Per layer, KV data size is `2*N*hkv*d*s`; L layers
multiply this by L, ignoring padding, metadata, compression scales, and replication.
For a dense decode query, ideal attention arithmetic is approximately
`4*N*hq*d` floating-point operations plus softmax. Grouped-query heads may share
KV reads only if the implementation actually reuses them.

With p independent shard RPCs, query traffic is approximately
`p*hq*d*s_query`, and replies are
`p*hq*(d*s_accumulator + 2*s_scalar)` for u, m, l. Include framing, retries, transport
overhead, and new K/V append traffic `2*hkv*d*s` per new token per layer. These are
payload formulas for this specified protocol, not wire measurements. Sharding
does not reduce the aggregate KV scan; it distributes it across memory systems.

P3 supports the Roofline bound `performance <= min(compute ceiling, bandwidth *
operational intensity)` at a declared memory boundary. Equivalently a shard cannot
take less than `max(F/C, D/B)` under ideal overlap. Use measured sustainable B and
the actual bytes reaching that boundary; NIC line rate and DRAM pin rate are not
application bandwidth. Aggregate bandwidth can grow only with independent paths,
balanced shards, adequate compute, and no common bottleneck.

If L attention operations on a token depend serially on prior results, p parallel
shard requests do not remove the per-layer wait. A communication-only lower bound
has approximately L serial RTTs for warm request/response execution, with payload
serialization and queueing added according to the actual path. More independent
sessions can improve throughput without removing one session's token latency.
Completion waits for the slowest required shard; component p99s cannot simply be
summed or multiplied into a valid end-to-end p99.

BDP is `B_bytes_per_second * RTT_seconds`; usable in-flight capacity W bounds one
idealized flow near `W/RTT`, subject to congestion control, flow control, sender
and receiver progress. Credits much smaller than BDP can limit bulk throughput;
credits large enough to fill the path also consume memory and can worsen queues.
Do not size these from nominal link bandwidth alone.

Compare (a) full-local supported attention if it fits, (b) strong KV paging/offload
at the same memory budget, and (c) established context/sequence parallel attention
where supported. Reject H2 for a tested workload if donor scan/compute, fan-out
tails, per-layer RTTs, and coordination exceed saved local traffic or capacity
benefit. Changing model quality or silently omitting a shard is not a valid win.

The companion assignment identifies vLLM grouped-query decode context parallelism
and SGLang multi-head latent-attention decode context parallelism as concrete
comparison targets. Verify their exact model support, partition/reduction behavior,
hardware requirements, and versions using the companion sources. A comparison on
an unsupported model must not be used to imply that existing KV ownership or
distributed attention reductions are absent. H2 needs a measured gap beyond them.

## Measurable quality scenarios and smallest discriminating tests

These are proposed fixture parameters, not measured requirements from users or
production SLOs. Register exact model/dtypes, tolerances, workload, hardware, and
performance threshold before running physical inference.

| Stimulus and environment | Required response | Observable test |
| --- | --- | --- |
| H1: four branches share a prefix, then diverge; two are canceled during compute | Preserve surviving state; stop canceled commits; reclaim only after completion | Compare outputs to independent unshared reference; log unique/reserved/pinned bytes and every transition. |
| H1: delayed completion races fork/cancel/release | Legal sequential history and no premature reuse | Enumerate a small bounded history and inject the four counterexample schedules above; then platform-appropriate sanitizers. A passing fixture is not a general proof. |
| H1: one tenant submits branches beyond memory and queue credits | Reject or defer within bounded count/bytes/age; preserve another tenant's admitted progress | Track errors, queue growth, memory, useful completions, and recovery after overload ends. |
| H1: a tool waits while other branches are ready | No worker or device slot held merely for an external wait, apart from explicitly retained state | Separate ready, device-running, tool-wait, and resume spans; compare strong existing engine policy. |
| H2: uneven shards, empty shard, causal/window mask, extreme scores | Same permitted attention operation under declared numerical contract | Compare monolithic and reduced attention; test explicit all-empty behavior and FP tolerances. |
| H2: duplicate, delayed, stale-generation, overlapping, or missing replies | Accept exactly one valid full coverage; fail incomplete coverage | Protocol fixture with operation IDs and range/generation corruption. |
| H2: cancel while one shard/device transfer is delayed | No further commit; retain every live buffer; eventually drain under stated progress assumption | Completion ledger plus reuse poisoning; test device hang as separate failure requiring bounded quarantine/rejection. |
| H2: increase p or link rate at fixed N and offered load | Any gain must survive full-path costs and quality checks | Compare end-to-end task/token distributions, failures, traffic, scan bytes, compute time, and queue age; include warm and cold runs separately. |

For both designs, record admitted logical operations, physical attempts, completed
useful tasks, rejections, and timeouts separately. Open-loop load needs scheduled
send delay/loss accounting; closed-loop load can hide collapse by reducing offered
rate. Little's law `mean L = arrival rate * mean W` requires compatible boundaries
and steady state; it does not turn p99 latency into a correct pool size.

For any OS/runtime optimization, a serial Amdahl bound is
`speedup <= 1 / ((1-f) + f/s)`, where f is the measured removable fraction and s
its acceleration. It challenges impossible claims; queueing changes and tails
need measurement. No new kernel recommendation follows before such a bottleneck
is observed and smaller mechanisms are compared.

## Direct primary sources, limitations, and publication

- **P1:** [Herlihy and Wing, Linearizability (1990)](https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf).
  Read abstract, introduction, and history/definition sections 2.1–2.2. Supports
  the sequential specification and real-time-order correctness target, not a
  liveness or implementation proof for H1.
- **P2:** [Linux v6.18 DMA API howto](https://raw.githubusercontent.com/torvalds/linux/v6.18/Documentation/core-api/dma-api-howto.rst).
  Read coherent/streaming mappings, barrier example, map/unmap/sync contracts.
  Supports driver-level ordering and lifetime requirements; GPU/RDMA backend
  qualification remains open.
- **P3:** [Williams, Waterman, Patterson, Roofline author preprint](https://people.eecs.berkeley.edu/~kubitron/courses/cs252-S10/handouts/papers/RooflineVyNoYellow.pdf).
  Read sections 1–4; the copy identifies revisions in August/October 2008. Supports
  an upper-bound/bottleneck model using memory traffic and sustainable bandwidth,
  not prediction of this unbuilt distributed engine's performance.

Provenance includes exact requested URLs, retrieval times, status, body sizes and
SHA-256 hashes. Two guessed Roofline URLs failed (404 and 403); an OSTI URL
returned an unrelated GASNet paper and was excluded after title inspection. A web
search tool returned an empty error and supplied no evidence. All are retained.

Only `REPORT.md`, `provenance.json`, `public-evidence.json`, `COMMANDS.md`, and the
MIT license for karlem/skills original material are intended for repository
publication. Full fetched skill files and primary papers remain scratch artifacts;
book/source rights do not transfer to this report. Total download volume is below
6 MiB. No external source code was executed. The source identity checks, reads,
and analysis are completed; physical inference and backend contract validation
remain unresolved.
