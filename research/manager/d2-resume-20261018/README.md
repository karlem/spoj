# Tool waits: reusable KV capacity is not released memory

**Decision: use existing mechanisms as the baseline; useful SPOJ advantage remains
UNRESOLVED.** Generic token replay and KV save/restore are already implemented.
The next useful experiment is to test the existing idle-session cache on an actual
two-session tool workload, not implement another suspension format.

This packet answers a narrower question now, without a model or remote machine:
what state is available in current implementations, and what cost boundaries
could defeat a proposed suspend/resume benefit? Tracking: issue #9. User deferred
the Droplet; this work used local Python and HTTP source retrieval only.

## The finding that changes the proposed experiment

Pinned llama.cpp allocates KV buffers at context creation. Erasing a sequence
removes cell ownership so other requests can reuse cells; it does **not** free
those backend buffers or shared model weights. It also already automatically
caches idle slots in host RAM and clears cells with unified KV when a new task
arrives. The correct baseline includes that feature and its RAM budget.

These are different outcomes:

| Observation | What it can establish |
|---|---|
| More free KV cells | Another request may fit within the existing pool |
| Lower allocated VRAM/RSS | Memory may be available outside that pool; erase alone does not establish it |
| A KV snapshot in RAM | Capacity has moved or been duplicated; total memory may increase |
| A saved/restored slot file | KV/tokens restored; complete sampler/application continuation is not established |

ServerlessLLM's inspected migration path transfers token histories and rebuilds
KV at the destination. That is another implemented baseline. It initializes a
target instance before releasing the old one; source shutdown does not establish
lower cluster-wide memory or cost.

Exact pins: ServerlessLLM `9f50241baa5386e06a9321c51f19a9ef5f964c2b`, llama.cpp
`5aeac37a35b44fde4bdffaec9159f2fcb253b622`. See
[source report](sources/REPORT.md) for functions, line references, state inventory,
implementation caveats and the retained HTTP 404. No upstream project was run.

## What the local calculation established

The [preregistered protocol](protocol.md) and [input grid](inputs.json) use an
explicit assumed dense GQA KV layout: 32 layers, 8 KV heads, head size 128,
2 bytes/element. All shared weights remain resident. We evaluated 864 deterministic
parameter combinations and nine tests, including wrong-state metadata, same-memory
offload, retained allocator pools, export unfinished at tool return, and exact
threshold boundaries. These are **arithmetic results, not measured model speeds**.

For an illustrative maximum 250-ms added resume time, assuming 5-ms restore overhead
or 20-ms replay overhead, the following necessary rates result:

| Context tokens | Assumed full KV payload | Minimum effective restore bandwidth | Minimum effective token-replay rate |
|---:|---:|---:|---:|
| 8,192 | 1 GiB | 4.08 GiB/s | 35,617 tokens/s |
| 32,768 | 4 GiB | 16.33 GiB/s | 142,470 tokens/s |
| 131,072 | 16 GiB | 65.31 GiB/s | 569,878 tokens/s |

These are **requirements**, not predictions of any hardware. Metadata, allocator
rounding, queueing, validation, contention and non-overlapped copies can make the
requirements stricter. Prefix reuse, shared KV, compression and different model
layouts can change the payload/reconstruction work; none is represented here.

With export time E and wait W, freeing all exclusive KV cells after export saves
at most `max(0, 1-E/W)` of their original wait occupancy. The 25% screening gate
requires `W >= E/0.75`. Long waits can amortize export, but they **cannot hide
restore latency after the tool returns** unless a separately justified prediction/
prefetch policy is introduced. This test assumes no advance knowledge of return.

For example, an assumed 4-GiB KV at 32 GiB/s takes 130 ms each to export/restore,
including the illustrative fixed cost. A five-second wait frees 97.4% of its
original logical slot occupancy-time, but exports/restores 8 GiB and needs a
4-GiB checkpoint plus source/destination overlap. Physical savings require a
separate capacity domain **and** an allocator release path; neither follows from
slot erasure. With 16 GiB KV at the same rate, restore alone takes 505 ms and
fails the resume gate even after a two-minute wait.

Fast replay can also beat snapshotting: at 8,192 tokens and an assumed 100,000
prefill tokens/s, replay adds 101.92 ms, versus 130 ms for 1-GiB restore at
8 GiB/s. Replay avoids KV transfer but repeats compute/weight traffic, which this
rate-only model does not separately price. No energy conclusion follows.

Grid counts (not probabilities): replay has 96 logical-slot candidates and 48
conditional physical candidates; snapshot has 192 and 48 respectively. All
physical candidates assume `allocator_releases=true`; zero exist when false.
Repeated values across unused dimensions inflate these counts by construction;
they are not performance statistics or success rates. All 864 rows explicitly
mark inference correctness unverified and accepted inference result false.
Resident is a comparator with zero added resume time, not a failed implementation.

## State and baseline gates before a real result

The saved sequence does not by itself preserve sampler RNG or the application
transcript, tool-call ownership and external side effects. Current server files
can append draft/context-checkpoint state, so they must not be described as just
plain KV. A new tool turn and interruption in the middle of stochastic generation
have different state requirements. Matching serialized shapes does not establish
matching model weights; pin/check model, tokenizer, adapters, engine and backend.

The smallest next test uses an **already authorized available model**, one idle
session plus a competing request, and the same recorded tool result for every
arm. Compare resident, exact token replay, upstream slot save/erase/restore,
and built-in idle-slot RAM cache with unified KV. Start greedy, text-only and
without speculative decoding. Record actual allocated memory, reusable cells,
host cache bytes, full resume latency and output equality, including wrong-model
and insufficient-capacity negative cases. A separate worker restores the saved
artifact in a fresh compatible context. No model download is authorized here.

If the upstream idle cache already meets the workload, configure/integrate it.
Only a demonstrated gap justifies a new mechanism. If physical release is the
goal, qualify actual context teardown/allocator release and count reload costs.

## Evidence, reproduction and limitations

- [Source/input hashes and raw command results](evidence/attempt-1/execution.json).
- [Complete 864-case JSON](evidence/attempt-1/grid.stdout) and
  [nine-test output](evidence/attempt-1/unit.stderr).
- [Offline product-check attempt](evidence/product-check/execution.json): exit 1,
  missing cached Torch dependency. Product tests did not run; no dependencies
  were downloaded and no product acceptance or merge-ready result is claimed.
- Independent review is recorded in `evidence/independent-review/` when complete.

From this directory, with Python 3.12 stdlib:

```sh
python -B -m unittest -v test_cost_model
python -B cost_model.py > /tmp/d2-grid.json
cmp /tmp/d2-grid.json evidence/attempt-1/grid.stdout
# Optional resource-limited harness; choose a new output directory:
python -B run_evidence.py /tmp/d2-review-new
```

The source researcher and later validator are separate agents on this same host.
There are no real tool-wait traces, model inference, physical memory observations,
distributed runs or measured throughput improvements. D7 remains blocked on its
separate artifact/oracle/storage prerequisites. Native Mac/product gates remain.
