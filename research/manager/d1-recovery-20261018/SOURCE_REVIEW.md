# D1 source qualification: recoverable inference

Run `d1-recovery-20261018-1705`. Source qualification and a separate independent
review were performed on 2026-10-18. No model or GPU experiment was run.

## Decision

- **REJECT** a standalone SPOJ KV-checkpoint/recovery system as a novelty claim.
  GhostServe and LUMEN already occupy erasure-coded/continuous checkpoint recovery,
  and DéjàVu implements full KV replication.
- **UPSTREAM** a narrower request-correctness envelope around an existing recovery
  engine: generation-fenced ownership, a durable client-ACK/output watermark,
  sampler/application state, compatibility identity and checkpoint integrity.
- **UNRESOLVED** any useful measured SPOJ performance advantage. The inspected
  systems do not establish the proposed benefit on affordable SPOJ hardware, and
  the available environment lacks a complete runnable upstream artifact/model/GPU.

The residual is a composition contract. The bounded review found no inspected
system documenting the entire contract; this is not a global novelty proof.

## Primary material

| System | Pinned material | What is established | Material limitation |
| --- | --- | --- | --- |
| GhostServe | [MLSys 2026 paper](https://proceedings.mlsys.org/paper_files/paper/2026/file/d99e8e80a6c41e148db686918dd7eab3-Paper-Conference.pdf); [demo `db586c8`](https://github.com/kennethzhao24/GhostServe-MLSys26/commit/db586c884dc2d3df11d779fb12bb1daac4e62491) | Paper reports chunk erasure parity, hybrid reconstruction/recomputation and intra-node GPU recovery. | Public demo lacks the launch/bench scripts and hook sources named by its README/server; kernels are prebuilt binaries. Paper assumes restartable intra-node GPUs. Treat results as reported. |
| LUMEN | [arXiv 2606.17787](https://arxiv.org/abs/2606.17787) | Paper reports gateway token history, request-to-holder placement, continuous CPU KV checkpoints, atomic page visibility, token-position hashes and suffix recomputation. | No public source was found in the bounded search. Gateway/controller HA, client ACKs, ownership fencing, RNG/app state and compatibility identity are not specified. |
| DéjàVu | [ICML 2024](https://proceedings.mlr.press/v235/strati24a.html); [source `07e76be`](https://github.com/msr-fiddle/dejavu/commit/07e76be97a1b3b09b4a3bbe0adcfd000406e1b57) | Incremental asynchronous KV replication to a neighbor and controller rollback to latest replicated `(microbatch, step)`. | Full KV replica; static FasterTransformer context; replication progress is not a durable client-delivery watermark. |
| Llumnix | [OSDI 2024 paper](https://www.usenix.org/system/files/osdi24-sun-biao.pdf); [current source `aa9097c`](https://github.com/llumnix-project/llumnix/commit/aa9097c899fd2f290e031f8a88f854afe4f0b415) | Live/pre-stop migration from a responsive source and current in-memory output ordering metadata. | Paper aborts a failed instance's running requests. The evaluated artifact branch is unavailable; current rearchitecture must not be conflated with the paper artifact. No durable ACK/fence was found. |
| vLLM | [current source `ff01a6b`](https://github.com/vllm-project/vllm/commit/ff01a6b14f329ccd4162fce309913542e2abcd5b) | Current sentinels abort in-flight work, clear state and can reinitialize process groups. KV-load failures can reschedule/recompute blocks. | Engine reinitialization and KV-load recovery are not hard-worker-loss session continuation. Its DP reinit epoch is not a request-ownership fence. |

## State and failure boundary

Existing systems cover individual pieces: replicated/checkpointed KV, gateway token
history, request-to-holder placement, atomic page visibility, replication-step
watermarks and in-memory output ordering. The following conjunction was not found in
the five inspected systems:

```text
session/request ID + attempt generation + exclusive lease/CAS fence
+ durable produced/emitted/client-ACK token watermarks
+ sampler/RNG and application/tool-state version
+ model/tokenizer/backend/ABI compatibility digest
+ checkpoint locator and integrity digest
```

A new owner must acquire the next generation atomically, reject stale-generation
output, restore only a compatible checkpoint, and re-deliver output above the durable
ACK watermark with client-side index/digest deduplication. This can improve correctness;
it cannot make checkpoint restoration faster by itself.

Exactly-once wire delivery is impossible to infer from a lost-ACK test. The fixture
tests exactly-once **client acceptance** using stable token indexes and digests; the
same token may be sent twice after an ACK loss.

## Dimensional bound

Aggregate unsharded KV bytes per sequence token are

```text
q = 2 * layers * KV_heads * head_dimension * bytes_per_element
```

For `32 * 8 * 128 * FP16`, `q = 131,072 B = 128 KiB/token`; therefore 8,192,
32,768 and 131,072 tokens require exactly 1, 4 and 16 GiB respectively before
allocator/layout overhead. Per-GPU residency depends on the actual tensor/KV-head
sharding; the values above are cluster-total protected bytes and must be multiplied
by concurrent sequences/batch occupancy.

An `N:K` parity scheme adds a `K/N` capacity lower bound: `8:2 = 25%`, while
`8:1 = 12.5%`. GhostServe's reported 8:2 configuration therefore fails the frozen
literal 15% protected-KV memory-overhead gate, although it is 75% less capacity than
a full replica. DéjàVu/LUMEN copy about 100% of protected KV before extra buffers.

Memory and network cannot be summed as one percentage. Future gates must report at
least:

1. extra resident bytes / active KV bytes;
2. steady checkpoint bytes / newly produced KV bytes;
3. throughput and latency overhead separately.

Parity capacity does not bound traffic: GhostServe gathers shards and offloads parity,
and LUMEN streams new pages. Reported negligible TTFT/TPOT impact is not proof of a
15% byte budget.

## Next performance experiment (blocked)

With an already authorized deterministic model and complete runnable upstream
artifact, compare replay, the strongest available upstream checkpoint mechanism, and
that mechanism plus the correctness envelope. Use matched model/tokenizer/backend
revisions; deterministic decoding first; 8K/32K contexts if locally supported;
checkpoint intervals 256/1024 tokens. Inject process loss, a stale checkpoint suffix,
lost ACK, delayed stale-owner output, checkpoint corruption and incompatible identity.

Pass only if p95 fault-to-first-correct-new-token is at least 2x faster than replay,
there are no accepted gaps/duplicates/stale outputs, and both separately declared
resident-byte and steady-traffic caps pass. Record output equivalence, RNG/app state,
replayed tokens, bytes, memory, throughput and every fault schedule.

The current CPU fixture tests only the control contract. It does not unblock or
substitute for this performance experiment.
