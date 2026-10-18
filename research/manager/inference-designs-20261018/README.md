# Three inference-engine designs worth trying

Status: research proposals under issue #9, not accepted product architecture.
The first two are active design hypotheses; the third is a queued model/runtime
co-design direction. No engine, GPU kernel, new OS or hardware was built here.
Prior D1/D2 and [hardware research PR #14](https://github.com/karlem/spoj/pull/14)
remain relevant; this packet does not repeat their performance experiments.

**The proposed change in abstraction is to make state ownership, dependencies,
and resource reservations explicit.** That is not itself a novelty claim.
SGLang already exposes branching and shared-prefix caching, Parrot uses semantic
variables to expose application dependencies, and modern engines implement
distributed attention. Our designs must earn their additional complexity against
those systems, rather than against an intentionally weak request-per-process
implementation.

The user's `karlem/skills` library is pinned at
[`c41b2b27`](https://github.com/karlem/skills/tree/c41b2b27c91da7155d555eb4946ece348ac08657).
Its architecture, concurrency, systems programming, reliability and networking
procedures shape the contracts below. Its book coverage is explicitly partial;
neither the books nor physical performance have been independently reproduced.
See the [fundamentals review](sources/fundamentals/REPORT.md) and
[seven-family prior-art review](sources/prior-art/REPORT.md) for exact pinned
sources, inspected sections, excerpts and limits.

## Design 1: an engine with explicit branch lifetimes and memory reservations

### Workload and possible advantage

A coding agent reads a long repository context, explores four candidate changes,
waits for tests, abandons three candidates and continues one. Several such agents
share a device. A request scheduler can see ready tokens, but may lack information
about which branches belong to the same task, which state will survive selection,
and which waits have deadlines. Providing that information could improve memory
admission, cancellation and completed-task latency under pressure.

This is a hypothesis about **policy and lifetime information**, not about inventing
prefix sharing. If SGLang plus its existing application interface already exposes
enough information, implement the experiment as an extension and reject the need
for a separate engine. Parrot is a required application-scheduling comparison.

### Interface and intermediate representation

The application submits operations, revealing new dependencies as tools finish:

```text
open(model_identity, tenant, memory_budget, deadline) -> session
prefill(session, exact_inputs) -> state
fork(state, branch_ids, branch_rng_streams) -> branch_states
generate(branch_state, output_limit, deadline) -> event_stream
await_tool(branch_state, call_identity, deadline) -> suspended_branch
append_tool_result(branch_state, call_identity, result) -> ready_branch
select_one(branch_states, selected_id) -> selected_state
cancel(branch_state, expected_generation) -> cancellation_receipt
close(session) -> release_logical_ownership
```

An online DAG contains Generate, AwaitTool, Score, SelectOne and Cancel nodes.
Dependencies can reference immutable outputs; unknown tool results are not
predictable inputs. The runtime does not speculatively execute external effects.
`select_one` chooses one branch; it does not merge incompatible hidden states.
Combining text from several branches requires ordinary model evaluation of the
combined context. Optional application hints must never change output semantics.

Each state handle identifies:

```text
tenant/session/branch; generation; committed input position;
model + tokenizer + adapter + quantization + backend/KV-format identity;
position/attention-mask/multimodal-input identity;
immutable prefix block references; private tail; RNG stream/counter;
logical owners; in-flight kernel/DMA pins; reservations; deadline;
tool-call/output identities and last accepted application event
```

Every mutating operation carries an expected version and stable operation ID;
replaying the same ID with different parameters is an error. The table above is
an interface sketch, not an implemented API.

These are logical capability handles, not pointers that remain valid across
workers. Prefix reuse requires exact compatible inputs and positional semantics,
not similar meanings. Cross-tenant sharing is disabled unless its isolation and
side-channel policy is separately specified. Model weights may be immutable and
shared while session KV, sampling and tool state remain isolated.

### Data structures and scheduling

1. Keep immutable published KV pages and a private writable tail per branch.
   A fork shares only committed pages. Copy a partially filled writable page or
   seal it before sharing; never let two branches append through one mutable tail.
2. Start with one serialized metadata owner per session. Its atomic state change
   defines fork, commit, select and cancel ordering. Do not begin with a custom
   lock-free page allocator. GPU work runs asynchronously outside that lock.
3. Maintain separate ledgers for logical KV, physically resident pages, in-flight
   pins, reserved future growth, weights, workspace, staging and allocator slack.
   A logical release does not immediately create usable GPU capacity.
4. Admission reserves a bounded generation quantum and necessary working buffers.
   If growth cannot be reserved, wait, reject, evict/recompute compatible state,
   or offload under an explicit policy. A deadline is a target; overload does not
   become solvable because it has a timestamp.
5. Schedule ready work with existing continuous batching, plus task/branch
   information. Compare ordinary fairness/deadlines before inventing a utility
   predictor. A task's speculative branches cannot consume unlimited credits.
6. Cancellation prevents new work and publication for the old generation. Reclaim
   physical pages only when logical ownership, all kernel/DMA pins and any
   migration readers are gone. Already delivered output is not retractable.

### Sequential contract and harmful history

States: READY -> RUNNING -> READY, or WAIT_TOOL; SELECTED/COMPLETED/CANCELLED are
terminal for the relevant branch operation. A RUNNING step owns an unpublished
tail version. Commit publishes that version once if generation still matches.
Cancel changes the generation under the same owner, rejects later old results,
and queues physical retirement. An in-memory commit is not a durable checkpoint.
Crash recovery requires the separate D1/D2 complete-state contract; arbitrary
external tool effects are not exactly-once because a token engine says so.

Counterexample: kernel K reads page P; cancel drops its last logical reference;
allocator reuses P for branch B; K later reads B's bytes. Reference-counted
application handles alone permit this corruption. A completion pin remains until
the actual device/transport use completes, even if the cancelled result is ignored.
Tests must exercise both cancel-before-commit and commit-before-cancel histories.

### Bounds that constrain the idea

For L=32, Hkv=8, d=128 and FP16 K/V, KV occupies 128 KiB per token across layers.
Four branches with an 8,192-token prefix and 1,024-token private suffix each need:

| Accounting | KV capacity, excluding other allocations |
|---|---:|
| Copy every complete branch | 4.5 GiB |
| Existing exact prefix sharing | 1.5 GiB |
| Proposed design's same prefix sharing | 1.5 GiB |

The proposed sharing saves **zero** against that strong existing baseline.
Additional benefit must come from admission, less wasted work, or better retirement
and wait policies, and must exceed metadata/pinning/reservation costs.

Little's law also constrains idle state: in a stable illustrative flow, four new
blocked sessions/s with a 20 s mean tool wait means 80 blocked sessions on average.
At 1 GiB each, retaining all of them needs 80 GiB. This is an average, not a p99
bound. Admission changes effective arrivals; eviction incurs restore/recompute.
An OS rewrite cannot remove these obligations.

### Smallest discriminating prototype

**P0, no GPU:** a bounded metadata-state machine and fake device-completion queue.
Enumerate fork/append/cancel/select and completion interleavings; compare against
the sequential contract. Inject duplicate and stale completions, cancellation
during copy, allocation failure, exhausted credits and timeout. Assert no shared
tail mutation, no late publication, no overcommit, no reuse before completion,
and eventual retirement after all uses finish. P0 tests correctness, not speed.

**P1, one existing engine:** add the operation/lifetime manifest above an existing
SGLang fork/cache path. Do not replace its attention kernels. Compare (a) stock
prefix sharing and continuous batching, (b) strongest available application-aware
baseline, and (c) the same engine plus hints/credits. Match cache budgets, seeds,
model/precision, work, hardware, arrivals and tool-result replay.

Proposed workload matrix: four branches, prefix 8K, private generation up to 1K;
tool waits 0/2/20 s; cancellation after 64/512 generated tokens; arrivals calibrated
to approximately 30/70/95% of measured baseline capacity. Use both a fully declared
trace and traces with unpredictable waits; disclose whether future lifetimes are
known. Fixed seeds alone do not guarantee bitwise sampling equivalence across
different batch/kernel paths; freeze an appropriate numerical/output policy.

Primary outcome: correct completed tasks within the same resource budget and
declared deadlines. Record p50/p95 task latency, deadline misses, live/reserved/
pinned bytes, wasted tokens, restore traffic, and scheduler CPU time. Proposed
go/no-go: at least 20% lower p95 complete-task latency at matched arrivals and
quality, or useful added capacity meeting the chosen SLO. Stop if stock APIs give
the same result, hints depend on an oracle, or work is merely shifted off-budget.

## Design 2: attention workers that own their KV shards

### Change the physical execution contract

Keep sequence KV shards at workers; send queries to those owners and reduce their
partial attention results. The coordinator owns model execution and ordering.
The owner may be a second GPU, or experimentally a CPU/RAM donor. This is an
explicit operator boundary, not a remote-memory load instruction.

The mechanism already exists in forms of decode context parallelism. Pinned
vLLM documentation covers GQA and MLA; SGLang has an MLA-oriented distributed
path. Flash-Decoding uses the reduction inside a GPU. Ring Attention's circulating
K/V blocks and overlap regime are a different traffic schedule. The question here
is whether **heterogeneous owners and agent-state lifetimes** give useful capacity
within a real task SLO after paying for slow owners and synchronization.

### Attention algebra and protocol

For one query head, shard r owns a disjoint set of visible positions I_r:

```text
s_i = q dot k_i / sqrt(d) + attention_bias_i
m_r = max(s_i)
l_r = sum(exp(s_i - m_r))
u_r = sum(exp(s_i - m_r) * v_i)

m = max_r(m_r)
l = sum_r(exp(m_r - m) * l_r)
u = sum_r(exp(m_r - m) * u_r)
attention(q) = u / l
```

An empty shard is an explicit identity element. An all-masked query yields no
attention result in the analytical fixture; a real model must use its own defined
mask semantics. GQA maps each query head to its actual KV head; query traffic and
result vectors still scale with Hq, not Hkv. Implementations may use equivalent
normalized output plus log-sum-exp summaries.

This equals full softmax attention in real arithmetic. Floating-point reduction
order, accumulation precision and kernels change numerical error; no bitwise
FP16 equivalence is implied. Compression, dropping shards or approximate attention
would be separate quality-changing experiments.

```text
coordinator -> owner:
  operation_id, session/branch, generation, layer, input_position,
  committed_prefix, pending_step_id, exact shard/visibility map,
  model/KV/position/mask identity, query, optional new local K/V,
  result_credit, deadline

owner -> coordinator:
  matching identities, covered positions/partition version,
  valid/empty status, stable summary, completion/error status
```

The logical KV prefix is committed through position j-1. A step at j appends
private pending K/V for each layer and evaluates against the committed prefix
plus that step's pending position. After all required layers and sampling finish,
the coordinator publishes j and its output under one generation. A partial step
cannot be exposed as a complete resumable state. Physical position blocks can be
assigned across owners, but the visible logical sequence remains ordered.

Every response must match the request snapshot and partition version. Coverage
must be disjoint and complete; a duplicate counts once. A missing/stale shard is
not zero. Retry only the same deterministic logical operation or rebuild from a
compatible complete state; never mix results from old and new ownership epochs.
Identity checks prevent accidental mixing, not malicious computation (D3 remains
separate). DMA completion and publication ordering are explicit, not inferred
from coherent allocation or a successful send call.

### Resource ownership and failure behavior

The coordinator reserves query, response/reduction and output capacity before
dispatch. Each owner reserves KV append and kernel workspace credits. Use a
deterministic acquisition order or all-or-release admission so partial credit
acquisition cannot deadlock a layer. Credits bound outstanding work; they do not
guarantee that a slow worker meets deadlines. Avoid holding global metadata locks
while waiting for a device or another owner.

On timeout/cancel, fence publication and stop admission, then drain outstanding
uses before releasing memory. On owner loss, exact attention cannot proceed with
its shard omitted; recover/replicate/recompute or fail the request. Replication
and checkpoint traffic must be charged. This prototype starts with fail-and-
reconstruct behavior, not an unimplemented transparent recovery guarantee.

### Traffic and critical-path bounds

Example assumptions: Hq=32, Hkv=8, d=128, 32 layers; Q/K/V FP16,
summary (m,l,u) FP32. One remote owner's per-layer query is 8,192 bytes; its
summary is 16,640 bytes. A new K/V position is another 4,096 bytes sent to its
owner when remote. The query+summary total over all 32 layers is 794,624 bytes
per remote owner per decode step, before new append bytes and protocol overhead.

At a 64K context, total KV is 8 GiB; two balanced owners hold 4 GiB each. A
raw-copy baseline would move the remote 4 GiB per decode step. Query+summary
exchange is much smaller, but **raw copying is not the strongest competing
algorithm**. Existing DCP already avoids that transfer. All required KV still
must be read where it resides, and Hq arithmetic still must be performed.

For parallel fan-out at layer l, the critical path includes the slowest owner:

```text
T_layer >= max_owner(dispatch + queue + local_attention + return)
           + nonoverlapped reduction/publication work
T_decode >= sum of dependent layer critical paths + other model work
```

Do not add times that overlap; trace the real DAG. Equal byte partitions need
not balance service times. Capacity constrains rebalancing; moving KV also costs
time and temporary memory. For 32 fully dependent remote rounds, RTT alone costs
0.64/6.4/32 ms at 0.02/0.2/1 ms respectively, before compute and queues. Increasing
bandwidth does not remove this serial floor. More owners also increase exposure
to stragglers; independent-delay formulas are not warranted without evidence.

This design expands or relocates KV capacity. It does not provide capacity for
weights that cannot fit, and does not eliminate dense/MLP compute. Many independent
agents on resident engines may be a better use of the same machines.

### Smallest discriminating prototype

**P0 completed here:** [binary64 algebra fixture](check_designs.py), comparing
monolithic attention with streamed shard summaries and forward/reverse merges.
It covers GQA, empty/uneven shards, one token, explicit visible-position masks
and extreme finite scores. It does not implement positional encoding, additive
attention biases, quantization, backend layouts or their compatibility checks.
432 comparisons pass (240 empty cases); max absolute error 1.11e-16 at a 1e-10
tolerance. An asymmetric wrong-GQA mapping is detected. This is arithmetic
evidence only, not full model, GPU, concurrency or network correctness.

**P1:** implement the owner protocol against deterministic CPU arrays first;
inject missing/duplicate/stale/late results and pending-append cancellation. Check
snapshot coverage, private tails, fencing, bounded credits and retirement. This
can run locally without pretending loopback timing represents hardware.

**P2:** use an existing authorized model/engine and two qualified devices. Compare
one-host reference where it fits, engine DCP on supported homogeneous hardware,
heterogeneous resident attention, and independent-agent placement. For a capacity
case the single host may be infeasible; report added feasible context separately
from a speed claim. Include context 8K/64K as supported, decode and prefill
separately, batch 1 and actual concurrent agent load, balanced and slow-shard cases.

Profile per-owner KV read throughput, attention work, query/summary and append
traffic, queues, reduction, copies, residency, complete-task latency and energy if
metered. Compare identical model/precision/mask semantics; define numerical and
task-quality gates before trials. Proposed success: capacity within declared SLO
or 20% lower p95 task latency at matched resources, without output-quality loss.
Reject a performance claim if faster local/DCP execution wins after equal budgets,
if a donor's bandwidth/latency floor misses the SLO, or if benefit requires omitted
state, unchecked accuracy changes or hidden additional hardware.

## Design 3, queued: an engine for bounded recurrent state

This changes the model contract, not just transformer execution. A recurrent or
state-space model carries a fixed-size learned state per layer rather than an
ever-growing full attention KV history. The engine treats that state as a versioned
object, forks it for alternatives, and schedules state transitions at its owner.
Hybrid models can retain attention in selected layers, so capacity is not generally
constant for the whole model. [Mamba/Mamba-2 primary sources and pinned recurrent-state code](sources/prior-art/REPORT.md)
are a starting point, not
evidence that this is suitable for every agent task.

An API would expose `advance(state, tokens)`, `fork(state)`, `snapshot(state)` and
`restore(identity, snapshot)`, with explicit model-specific state shape and
precision. Forking still needs a state copy or a correct lazy-copy mechanism;
in-place recurrent updates cannot be shared by diverging branches. Arbitrary
edits to past inputs require replay or extra checkpoints. Bounded state can lose
information needed for exact retrieval, long-range dependencies or tool use.

First comparison should use existing authorized model artifacts, with real code,
retrieval and multi-tool tasks at matched quality and total resources. Measure
state bytes per session, fork/update/restore costs, complete-task success, latency
and energy. Token throughput alone cannot establish equivalence between differently
trained models. Training or architectural changes would need a separate approved
experiment and budget. No training, model artifact or quality test ran here.

## What belongs in hardware or a new OS?

The contracts suggest useful hardware/software boundaries: memory allocated by
declared lifetime; device-visible queues with bounded credits; completion records
that release ownership; explicit placement; observability of copy/compute/wait;
isolation for state handles. Existing operating systems and devices already
provide parts of this. Document the missing guarantee before proposing new silicon.

A minimal research runtime could use supported kernels/drivers and expose those
contracts to an engine. A more radical OS would need to own scheduling, memory,
device queues, isolation, tool/process compatibility and recovery. First isolate
one contract that cannot be met efficiently with current mechanisms. The same
Amdahl, bandwidth and causality bounds apply to a new OS; no benchmark here
establishes removable kernel overhead. No purchase or fresh-kernel project is
recommended solely because the architecture is being reconsidered.

## Recommended order and evidence limits

1. Start Design 1's metadata/interleaving prototype and existing-engine API audit.
   Its correctness questions are testable without hardware and closest to agent
   behavior. Prefer an upstream extension if the application contract suffices.
2. Keep Design 2 as an explicit capacity/heterogeneity experiment after machine
   inventory and a model/task SLO exist. Its algebra is known and checked here;
   its distributed lifecycle and physical benefit remain unresolved.
3. Queue Design 3 for model-quality evaluation. It offers a deeper change in
   context-state scaling, with a correspondingly different correctness question.

Rejecting a separate implementation after finding a strong existing mechanism
is a useful outcome. Sources support the mechanisms and reveal collisions;
they do not validate this proposed composition or establish worldwide novelty.
Research checks, independent design review and product/native-Mac acceptance are
separate. Raw analytical results are in `evidence/analysis-attempt-1/`; source
provenance and independent review accompany the final packet.

The required offline product check exited 1 before test collection: the isolated
cache lacks `nvidia-nccl-cu13==2.30.7`, required through Torch. No dependency was
downloaded. Native-Mac/product acceptance remains blocked and is not inferred
from the analytical fixture. See `evidence/product-check/`.
