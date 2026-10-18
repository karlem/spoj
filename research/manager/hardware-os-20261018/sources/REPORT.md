# Hardware and OS decision packet

Task `hardware-os-20261018-1801/hardware-sources`; issue #9; worker `/root/hardware_sources`.
2026-10-18 UTC. Scope: primary-source inspection and inferred resource bounds, **not inference benchmarks**. Exact runtime model/run identifiers were not exposed. Manager owns shared records; this worker only writes its scratch directory. No external code executed, model downloaded, host configuration changed or hardware purchased.

## Decision

**Pursue measurement of memory locality and the bytes that actually cross a link. Do not start a new OS.** Network is not generally more important than GPU for local inference. The limiting component depends on whether weights/KV fit, whether work is dense or sparse, batch size, and which synchronization lies on the next token's critical path. Fiber is a physical transport choice; it does not create GPU compute, memory bandwidth, coherent pooled RAM or a scheduler.

The useful architecture to test first is an existing inference engine with resident hot state and an agent-aware userspace admission/suspension policy. Keep each request's KV with its compute unless a measured capacity benefit exceeds replay/restore costs. Prefer independent jobs/agents across machines before dividing a single token across a slow network. If one model cannot fit, layer partitioning can buy capacity even when it does not improve single-stream latency. This is a capacity tradeoff, not a failed design.

## What the wire actually carries

| Placement/mechanism | Repeated wire traffic | Consequence |
|---|---|---|
| Independent inference replicas/coarse jobs | Requests, tool/results, output tokens; weights initially loaded/cached | Network can be almost irrelevant to per-token compute after loading. Batch locally and avoid repeated cold loads. |
| Layer/pipeline partitioning | Hidden activations across stage boundaries; weights stay at owning stage | Each token's dependencies cross stage boundaries; one stream cannot hide all stages behind other work. Concurrency/microbatches can improve utilization. |
| Tensor parallelism | Collective activations/reductions per layer, sometimes multiple per layer | Repeated message startup and synchronization matter, even when the payload is small. Measure collective latency, not only bulk bandwidth. |
| MoE expert parallelism | Routed activations/results when experts remain resident remotely | Capacity distribution can work; imbalance, all-to-all and token dispatch overhead can dominate at small batch. |
| Streaming/offloaded weights or experts | Weights/expert bytes on cache misses, plus staging | This can turn storage/PCIe/network into the critical bandwidth bottleneck. Measure misses, not total parameter size alone. |
| KV offload/migration or disaggregated prefill/decode | KV blocks plus metadata/ownership transition; alternatively tokens for replay | Large payloads can dominate resume/first-token latency. Application/tool/RNG state remains a separate correctness obligation. |

These are architectural deductions, not performance claims. Actual bytes depend on layout, attention design, compression, collective algorithm and cache reuse. Attention KV reads also grow with context and can defeat a weights-only model.

Illustrative byte geometry, explicitly **assumed**: an 8-billion-parameter dense model at 4 bits/weight is 4 decimal GB before scales/metadata. Reading all weights once per batch-1 decode token has lower-bound time `4 GB / effective local bandwidth`. Streaming those same bytes over a 400 Gb/s link would require at least 80 ms, before overhead; **a normal layer-partitioned deployment does not resend all weights each token**. A 4,096-element FP16 hidden vector is only 8,192 bytes per token per stage boundary. A hypothetical 32-layer implementation with two such collective inputs per layer presents 524,288 input bytes/token to collectives, but network bytes and startup count depend on the collective algorithm and node count. These examples show why identifying traffic is prior to buying cables.

Batching reuses weights across tokens/requests and can raise arithmetic intensity; prefill is usually a different matrix workload from batch-1 decode. Neither a FLOPS number nor a bandwidth number alone predicts tokens/s. Queueing/batching can improve throughput while worsening an individual agent's latency, so measure both.

## Link and memory limits, without misleading units

All GB/s here are decimal `10^9 bytes/s`; Gb/s are decimal `10^9 bits/s`. These are nominal vendor specifications or dimensional ceilings, **not sustained payload measurements**.

| Item | Source support | Correct interpretation |
|---|---|---|
| H100 SXM local HBM | NVIDIA product specifications: 80 GB, 3.35 TB/s | 3,350 GB/s advertised device-memory bandwidth. Not a GPU purchase recommendation or attained model rate. |
| ConnectX-7 model MCX75310AAC/AAS-NEAT | Manual: 400 Gb/s Ethernet; PCIe Gen4/5 x16; OSFP IB/Ethernet port | 50 GB/s line-rate byte ceiling before framing/protocol, PCIe, DMA and software costs. Exact SKU/firmware/port mode matter. |
| Nominal 100 Gb/s Ethernet | Unit conversion only; no particular card qualified | 12.5 GB/s ceiling, not 100 GB/s. |
| 400 Gb/s link versus above HBM | Arithmetic `3350/50 = 67` | 67-fold nominal byte-rate gap, **not** 67-fold inference speed ratio. Local DRAM is a third tier with platform-dependent channel/NUMA rates; no invented DRAM benchmark. |
| PCIe interface | ConnectX-7 manual: Gen5 x16, 32 GT/s per lane | Lane width, generation, shared upstream switch/root path and actual negotiated state must be measured. Vendor aggregate bidirectional numbers must not be used as single-direction payload bandwidth. |

The NIC manual separately describes electrical protocols and optical protocols delivered through modules. A compatible DAC, AOC or optical module/fiber can carry the selected link; matching connectors is insufficient. Audit rate, lane count/breakout, module support, reach, connector/polarity, optical power and thermals. A short direct cable is a sensible two-node control; optical is useful for reach/layout, not an automatic throughput upgrade at an unchanged negotiated line rate. Bidirectional links do not grant double bandwidth to a one-direction transfer. Simultaneous traffic, shared lanes, collective topology, host copies and memory traffic can contend.

GPUDirect RDMA creates a supported direct DMA path between an NVIDIA GPU and a NIC; it is **not cache-coherent general-purpose remote memory**. The inspected NVIDIA guide requires attention to shared root complexes, topology, BAR mappings, registration lifetime and explicit CUDA ordering. Paths traversing CPU interconnects may perform poorly or fail. Its stated IOMMU limitation requires 1:1 mappings, and it documents driver/peer-memory dependencies. Do not change IOMMU/security settings as a casual benchmark setup. The guide names Tesla/Quadro support; that does not certify an arbitrary consumer GPU, nor every modern GPU/driver combination. Exact GPU, NIC, driver, kernel and `dma-buf`/peer-memory path must be qualified together. Test host-staged TCP/RDMA as controls; enabling RDMA alone does not prove GPU-direct traffic.

## Apple/Thunderbolt compatibility is specific

The retrieved MLX distributed guide documents MPI, TCP ring and JACCL. Its current **documented MLX JACCL setup and configuration helper** require a directly connected full mesh. This does not establish that every revision or lower-level JACCL library transport universally lacks ring capability; earlier issue #7 library evidence must retain its narrower scope. Pin the engine/library versions and supported topology at experiment time.

The guide says macOS 26.2+ and Thunderbolt 5 Macs provide RDMA and that enabling it requires local recovery-mode setup, not remote sudo. Its "order of magnitude lower" communication-latency claim is vendor/project documentation, not reproduced here. For `n` nodes a simple full mesh requires `n(n-1)/2` links and `n-1` suitable endpoints per node; a ring requires fewer links but is a different baseline. The guide also documents multiple cables per peer for large-message striping and asymmetric-link limitations. Ports/controllers and cable compatibility still need inventory. Its configuration operations change networking and are not executed or authorized by this source task.

Start with two Macs if already available: one direct TB5 link, supported JACCL, TCP ring over the same physical path, and one-node execution. Preserve the same model, quantization, context, batch and correctness criterion. A cable marked USB-C is not sufficient qualification.

## Existing OS and engine mechanisms come first

| Mechanism | Existing baseline and decision |
|---|---|
| NUMA placement/CPU affinity | Linux memory policies support process/thread/VMA-level placement with `mbind`/related interfaces; cpuset constraints interact. Measure local/remote placement and CPU affinity first. Binding to an undersized node can cause allocation pressure; interleaving is not always better. |
| Faults and TLB pressure | Process-local prefaulting and supported locked staging buffers are candidate controls; limits and driver registration lifetime matter. Linux THP supports per-region advice and reports a tradeoff between TLB/fault benefits and allocation/compaction latency. Do not globally enable hugepages based on a slogan. |
| Asynchronous I/O | `io_uring` has shared submission/completion rings; SQ polling can avoid submission syscalls through a kernel polling thread. This is not universal zero-copy or removal of the Linux kernel. CPU/power, unsupported operations and filesystem/direct-I/O alignment are costs. |
| Avoiding duplicate caching | The existing pinned Colibri packet already qualifies mmap, direct I/O, io_uring, parallel/pipelined reads, cache-budget tuning and RSS guard. Compare its strongest applicable configuration; do not compare a new design only to naive blocking reads. |
| Idle agent state | D2 already found llama.cpp host idle-slot caching and token/KV save/restore/replay alternatives. Logical KV cell reuse is not physical VRAM/RSS release. A new OS cannot make retained application buffers disappear safely without an allocator/ownership mechanism. |
| Network kernel bypass | GPUDirect/RDMA or a dedicated userspace network dataplane may reduce a traced bottleneck. These require compatible drivers, safe buffer lifetimes, isolation, failure handling and sometimes dedicated polling cores. |

One relevant precedent is IX (`550bf28a4ddd5fafcec707a14acd502712a10dae`): a protected network dataplane design from Stanford/EPFL. Its pinned README documents a separate control/dataplane, DPDK, narrow Intel NIC requirements, kernel modules and hugepage/NIC setup. It establishes that specialized dataplanes are real; it provides **no evidence of an LLM or GPU advantage** and is not a turnkey replacement for the current engine. No IX code was run. Its MIT-style license is retained beside the README.

A reasonable software design is: ordinary supported OS/drivers -> existing engine -> explicit memory and I/O accounting -> local admission and batching -> agent wait/resume state machine -> optional locality-aware coarse scheduler. Implement the smallest missing component only after the trace shows it is missing. A fresh kernel would add GPU/NIC/storage driver support, security/isolation, process/tool compatibility, updates, telemetry and recovery to the burden before demonstrating one token of benefit.

For a mean or summed critical path with removable fraction `f`, even perfect removal yields at most `f` fractional latency reduction (`speedup <= 1/(1-f)`). Thus a 20% token-latency screening target requires at least 20% *removable, non-overlapped* baseline token time; if an intervention only halves that overhead, it requires at least 40%. This bound must not be misapplied to p99 by substituting mean fractions. Profile relevant slow tokens separately. A new OS hypothesis is falsified for this workload if the bottleneck is absent, the bound is too small, or existing userspace/engine tuning captures the gain.

## Reconciliation with accepted research

At `c6cefdd90f6fe1f80d71c024e52065eb1147e826`, the D7 decision was an **upstream Colibri configuration experiment**, not a new OS mechanism. `DROP=0` still enables its presence-tested switch; baseline must unset `DROP`. Range `POSIX_FADV_DONTNEED` does not remove owned slabs/copies. The prior physical experiment remains blocked on a permitted artifact, file-backed capacity, independent oracle and single-token observation hook. The documented recommended artifact was 429 GB versus approximately 26 GB then available; that capacity observation is historical, not a current-host inventory.

D2 in `/workspace/spoj-d2` establishes source behavior and assumed-cost calculations, not measured inference speed. Its 1/4/16 GiB KV examples and replay/restore limits should be reused; this report does not repeat its 864 scenarios. Long tool waits may amortize export but cannot automatically hide restore after the tool returns. Networked KV placement has to beat local cache/replay, including overlap, host RAM and metadata.

## At most three lab configurations, selected by role

No prices or purchase recommendations are given: inventory and complete-system costs are unavailable. Borrow/use existing hardware first.

1. **Single-host reference:** one existing sufficiently large-memory machine, preferably the user's intended deployment hardware, with supported local engine and local SSD. Freeze CPU/GPU/model, populated memory channels, capacity, SSD, OS and power envelope. Role: establish local latency, bandwidth, residency and whether distributing is necessary. A memory-heavy retired server is eligible only after DIMM/channel/NUMA, ISA, cooling and wall-power audit; low sticker price/TDP are not total cost or measured energy.
2. **Two-node Apple capacity/latency test:** two already available TB5 Macs with adequate unified memory and qualified macOS/MLX revisions, direct compatible TB5 link, ordinary management network. Role: compare one-node, existing TCP-ring and documented JACCL transport, including capacity benefit. Local recovery setup requires separate host-owner action/authorization. Ports/topology, actual payload and synchronization are the evidence, not a cable label.
3. **Two-node Linux RDMA control:** two already available Linux GPU hosts with qualified GPU-direct support and paired RDMA NICs (e.g. an appropriate ConnectX class), adequate electrically wired PCIe slots, matching supported direct DAC/optics and sufficient host DRAM. Role: strongest feasible low-latency interconnect versus host-staged/TCP controls. Audit root complex, NUMA, PCIe switch oversubscription, BAR/IOMMU/driver support, link mode and cooling. If unavailable, retain UNRESOLVED rather than substitute a loopback claim.

Compare equivalent aggregate model capacity and complete systems when choosing one big host versus multiple small hosts. Include adapters, cables, switches if needed, DRAM, SSD, cooling, wall power and idle power. A two-node direct-link experiment avoids a switch confounder; it is not evidence for an arbitrary larger topology.

## Next minimal experiment packet

**Question:** on the intended local model/workload, is the single-token path dominated by local memory/compute, communicated activations, or recoverable software overhead?

**Baseline:** one host where the same model fits; strongest supported existing engine configuration. For distributed tests, compare the already supported transport/topology with matched placement, not an invented engine. For agent waits retain the D2 resident/idle-cache/replay baseline. If one-node capacity is insufficient, state that explicitly and compare an appropriate capacity-matched reference; do not claim a latency win over an impossible run.

**Inputs to obtain:** exact machine/SKU, memory/channel population and GPU VRAM, PCIe tree/NUMA, NIC firmware/driver/link, TB ports/macOS if relevant; allowed existing model path/hash/quantization; context and output lengths; intended batch/concurrent agents; representative wait distribution; correctness reference. OS changes, checkpoint downloads and larger-memory runs remain outside this packet's current authorization.

**Method:** inventory first; measure effective one-direction/bidirectional payload and latency at 8 KiB, 512 KiB and a bounded 64 MiB transfer, both idle and under inference contention. Measure host-host and GPU-GPU separately only when supported. Then trace one model on matched cold/warm, batch-1 and bounded batched cases; retain per-token latency, TTFT, useful output throughput, queueing, actual network/PCIe/storage bytes, faults, CPU time, context switches, RSS/VRAM and power if a meter exists. Use existing tools only: examples are `lscpu`, `lspci -tv/-vv`, `/sys` and `/proc`, `numactl --hardware`, `nvidia-smi topo -m`, NIC/RDMA inventory, and supported engine logs; absence/permission failures must be recorded. Hardware counters and perf/eBPF need availability and permission checks. Do not infer application overhead by subtracting unrelated maxima.

**Future screening criterion:** predeclare the target latency statistic before collection; aim for at least 20% lower token latency with matched output correctness and no hidden throughput/memory/energy regression. This is research screening, not product acceptance. Report TTFT/resume tails separately. For this source task the decision criterion is narrower: establish compatibility constraints and an upper bound that could reject unnecessary OS/interconnect work; that criterion is satisfied as source evidence only.

**Falsifiers:** traffic is negligible or hidden; local HBM/compute dominates; memory already fits locally with better latency; copying/staging/registration erases RDMA benefit; collectives add more startup than parallel compute saves; existing NUMA/cache/I/O tuning removes the gap. Stop there rather than building a new OS.

**Execution status:** physical inference, distributed throughput, compatibility on user hardware and independent hardware validation are UNRESOLVED. Current run limit is five minutes/experiment, 2 GiB memory and 100 MiB data; no large-model experiment is implicitly authorized by this design. A future packet must choose a valid fixture or obtain revised resource authority before physical execution.

## Evidence/provenance

Eight primary-source families were inspected: NVIDIA H100 specifications; NVIDIA ConnectX-7 manual; NVIDIA GPUDirect RDMA guide; MLX distributed guide; Intel Thunderbolt attempt(s); Linux memory documentation; Linux io_uring manual; pinned IX README/license. Mutable documentation is frozen locally by retrieval UTC and SHA256 in `manifest.json`; this is not a claim that it came from an immutable upstream revision. IX is pinned to an immutable commit. `raw/` retains fetched pages; `*.txt` are deterministic HTML text extracts with line references. Prior D7 memo/protocol were extracted from the stated git revision. No source implementation was copied into a new program.

Intel's original newsroom URL redirected to an unrelated newsroom home page and a guessed product URL returned 404; those do not establish any Thunderbolt rate. Failures are preserved. Any successfully retrieved alternate Intel page is separately identified in the addendum below. Manufacturer documentation claims remain distinct from actual hardware support or reproduced speed.

Documentation remains under its publishers' copyright/terms; raw pages are local audit artifacts, not a proposed wholesale public redistribution. Manager should publish this paraphrased report, URLs, hashes and minimal necessary extracts; retain IX's license if redistributing its README. `COMMANDS.md` records retrieval/extraction and the failed helper invocation. No product tests were run by this worker because no product code was changed.

Source locator index (line numbers refer to retained plain-text extracts):

| Source | Locations supporting decisions |
|---|---|
| [NVIDIA H100 specifications](https://www.nvidia.com/en-us/data-center/h100/) | `h100.txt:367` product column labels; `:400` memory/capacity/bandwidth; `:422` interconnect advertising. Do not interchange SXM and NVL columns. |
| [ConnectX-7 specifications](https://networking-docs.nvidia.com/connectx7hw/specifications) | `connectx7.txt:40` airflow/power; `:41` exact SKU; `:51` PCIe; `:57` Ethernet rate; `:105` optical/electrical distinction. |
| [GPUDirect RDMA](https://docs.nvidia.com/cuda/gpudirect-rdma/index.html) | `gpudirect.txt:62` support; `:346` registration expense; `:414` topology; `:431` IOMMU; `:524` memory ordering; `:1026` NIC/peer-memory path. This document contains versioned historical caveats; qualify against the actual installed stack. |
| [MLX distributed guide](https://ml-explore.github.io/mlx/build/html/usage/distributed.html) | `mlx-distributed.txt:1075` TCP ring and point-to-point restriction; `:1221` OS/TB5; `:1236` local recovery; `:1274` documented mesh; `:1373` multi-cable striping; `:1425` configuration helper. |
| [Linux NUMA memory policy](https://docs.kernel.org/admin-guide/mm/numa_memory_policy.html), [THP](https://docs.kernel.org/admin-guide/mm/transhuge.html) | `linux-numa.txt:69` memory policy/cpuset scope; `:136` VMA policy; `linux-thp.txt:93` TLB; `:146` per-region advice; `:191` defrag cost. |
| [io_uring manual](https://man7.org/linux/man-pages/man7/io_uring.7.html) | `io-uring.txt:37` shared rings; `:205` SQ polling and kernel thread. |
| [IX README at pinned commit](https://github.com/ix-project/ix/blob/550bf28a4ddd5fafcec707a14acd502712a10dae/README.md) | `ix.txt` overview, supported NICs, setup requirements; `raw/ix-license` accompanying license. |
| [Prior pinned MLX audit](https://github.com/karlem/spoj/blob/c6cefdd90f6fe1f80d71c024e52065eb1147e826/research/heterorouter/related-projects-and-papers.md) | Apple Silicon section: `b6642e604843776705b57b1eaecb6f57e519b793` nested JACCL source (`jaccl.cpp`) supports rings while high-level guide/configuration requires mesh. Reconciled prior evidence, not a new code execution. |

Intel addendum: the alternate `newsroom.intel.com/client-computing/intel-introduces-thunderbolt-5-connectivity-standard` also redirected to the same unrelated home page (same SHA256). **No TB5 80/120-Gb/s nominal-rate claim is used in this packet.** The required capability/compatibility statements come from MLX's guide; actual payload bandwidth must be measured. Source failures do not prove a product capability is absent.
