# All eleven skills applied to the current SPOJ workstreams

2026-10-18. Installed from `karlem/skills@c41b2b27c91da7155d555eb4946ece348ac08657`.
All 44 files in the 11 skill folders match the pinned source byte for byte;
[manifest](evidence/skills-install.json). The project-local installation is
[`.agents/skills`](../../../.agents/skills/README.md). A second byte-verified copy
is installed in this worker account's personal `/home/agent/.agents/skills` root,
so it survives branch switches here; other workers/accounts are unaffected.
A new agent session is
needed for normal host discovery; these files were explicitly read and applied
in the current session. Upstream's offline validator passed structure/link and
evaluation-wiring checks; it does not measure effectiveness on SPOJ or certify
the underlying source claims.

Assessment scope: issue-1 / PR #3's two-worker proof; local-tcp-demo / PR #6's
three-worker TCP evidence; research/heterorouter / PR #8's algorithms and systems
studies. [Exact branch revisions](evidence/repo-snapshot.json) are frozen. This
is an evidence review, not eleven new implementation assignments. Existing
acceptance requirements, especially native Mac validation, stay in force.

| Skill, applied question | Current evidence and limit | Consequence for this investigation |
| --- | --- | --- |
| [distributed-systems](../../../.agents/skills/distributed-systems/SKILL.md): what invariant crosses the process boundary? | `tcp_worker.identity`, `TCPSession._recv` and `verify_tcp_trace` check run/worker/request identity and token-slot coverage against frozen weights. The current replay confirms the saved bounded transcript. No cross-host, retry/durable-effect or distributed-recovery evidence exists. HetRoute simulation is not that evidence. | Keep model expert selection separate from infrastructure placement. One local I/O-policy experiment needs no distributed service, consensus or exactly-once claim. |
| [linux-performance](../../../.agents/skills/linux-performance/SKILL.md): which constrained resource explains latency? | The current host has a 4-CPU quota and 32 GiB limit; allowed-vCPU count alone would misstate capacity. The tiny proof has no model-sized storage working set. Existing research's calculated bandwidth limits are not profiles. | Collect matched physical I/O, anonymous/file residency, reclaim and exposed stalls. Do not infer a network or OS bottleneck from architecture. Missing physical measurements block optimization. |
| [systems-profiling](../../../.agents/skills/systems-profiling/SKILL.md): are we measuring CPU, wait, or overlapped service? | Bounded tensor/TCP traces explain correctness, not a flame graph or storage timeline. Colibri's summed loader service differs from main-thread wait. Restricted `strace` failed; the authorized own-child readiness retry succeeded. Perf binary and tracepoints are absent, while a narrow perf API permission probe succeeded. | Preserve permission contexts and failures. Start with counters and untraced latency; compare instrumentation overhead before accepting a timeline. No invented profile fills the missing trained workload. |
| [architecture-tradeoffs](../../../.agents/skills/architecture-tradeoffs/SKILL.md): which new boundary buys a measured benefit? | The coordinator/worker boundary exists for the approved correctness proof. There is no measured requirement for a new OS, remote memory service, scheduler service or additional framework. Current research has multiple hypotheses rather than a selected product architecture. | Use an existing per-range OS API inside an existing engine. A separate OS/runtime is not justified by the available benefit bound. |
| [database-internals](../../../.agents/skills/database-internals/SKILL.md): what is the storage/cache/durability contract? | SPOJ has no database, WAL or bot-state recovery path. `FrozenState` and trace hashes provide provenance, not transactional durability. Colibri's immutable checkpoint and replaceable expert cache expose a relevant cache hierarchy. | Distinguish logical reads, file cache and physical I/O. Database recovery mechanisms are out of scope; do not add a database to satisfy this lens. |
| [systems-programming](../../../.agents/skills/systems-programming/SKILL.md): where are copies, ownership and allocations? | `ExpertShard` owns detached CPU tensors and the TCP codec explicitly serializes bytes. In Colibri, a buffered fill copies into owned slabs; mmap is already an alternative. LRU promotion swaps buffers. Advice does not free slabs. | Trace offsets, scale geometry and buffer lifetime before claiming duplicate bytes or zero-copy. Verify contiguous ranges and actual completed fd; `DROP=0` is an enabling presence flag, so baseline must unset it. |
| [production-reliability](../../../.agents/skills/production-reliability/SKILL.md): can failure consume unbounded resources? | `tcp_wire` bounds header/payload and uses deadlines; `TCPSession.close` has bounded worker cleanup. Existing tests cover faults in the local milestone; none establishes production service availability or pressure recovery for streamed models. | Include allocation failures, short/error reads, memory events, retries, timeouts and cleanup in every experiment result. A killed/failed run cannot become a fast sample. Add no production subsystem now. |
| [concurrent-programming](../../../.agents/skills/concurrent-programming/SKILL.md): what publishes a completed expert safely? | The correctness proof checks assignments/aggregation and ownership. Colibri's PIPE has generation-tagged work acquisition, distinct workspace slots and completion waits; io_uring has a different completion/finalization path. Source inspection is not a new race-freedom proof. | Do not move advice before completed copies or publish a partially loaded slot. Freeze applicable loader mode and record its actual path. Do not change synchronization along with the cache knob. |
| [architecture-patterns](../../../.agents/skills/architecture-patterns/SKILL.md): what observable quality scenario should choose the design? | The approved numerical scenario has an oracle, tolerances and negative tests. “Affordable local AI OS” still lacks a concrete task/SLO and physical capacity/latency baseline. A fixed-token source study does not establish assistant usefulness. | Use a bounded pressure/reuse scenario and predeclare correctness, benefit and failure gates. Keep this research decision separate from a product ADR or spec expansion. |
| [design-patterns](../../../.agents/skills/design-patterns/SKILL.md): which variation needs an abstraction? | `qwen3_adapter` contains the pinned HF contract, while `tcp_wire` contains framing. The frozen guards deliberately constrain substitutability; an arbitrary backend is not automatically compatible. | The studied variation already has one environment switch. No transport/plugin hierarchy, custom allocator wrapper or general policy framework is needed. |
| [network-engineering](../../../.agents/skills/network-engineering/SKILL.md): what path and bytes were actually observed? | The raw trace contains init, request and result frames over historical loopback TCP. This does not measure remote links, RTT, sustainable bandwidth, routing or hardware contention. Simulated perceived rates remain assumptions. | Keep network measurements out of this one local storage experiment. Any later remote comparison must include weight initialization and actual link/queue evidence; neither RDMA nor a second box is implied here. |

Concrete source locations: [adapter and provenance](../../../spoi/src/spoi/qwen3_adapter.py),
[framing/deadlines](../../../spoi/src/spoi/tcp_wire.py),
[session and cleanup](../../../spoi/src/spoi/tcp_session.py),
[worker identity](../../../spoi/src/spoi/tcp_worker.py),
[assignments](../../../spoi/src/spoi/partition.py),
[transcript oracle](../../../spoi/src/spoi/verify_tcp_trace.py),
[approved contract](../../../docs/specs/local-tcp-parity.md).
The independent review and source manifest are linked in the [decision memo](README.md).

The useful project state is a guarded local correctness proof plus inspectable
research artifacts. It is not yet a measured affordable inference advantage.
The next missing evidence is a physical, quality-preserving comparison against
the strongest existing engine configuration; more architecture does not replace it.
