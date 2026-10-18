# Projects and papers for capacity-first heterogeneous MoE inference

Date: 2026-10-17. Human-requested research continuation of issue #7/PR #8.
Objective: make a model runnable across heterogeneous usable memory when no
single device can host it, then improve measured service quality while retaining
its declared computation contract. Read capacity-and-colibri.md for memory tiers,
non-expert/KV/workspace reserves, activation-versus-weight movement and migration
invariants. This survey changes no implementation or approved local milestone.

## Evidence level and selection

Nine accessible primary repositories were read at pinned commits, with selected
implementation files from five and a KTransformers scheduling tutorial. Paths,
SHA-256 hashes and revisions are in related-projects-sources.json. Source depth
is stated per entry. No project was installed, built, imported, benchmarked or
used to download model weights. No headline speedup is adopted as our evidence.
Paper identities/links below come from authors' repository citations; their full
texts were not read in this survey. Earlier primary arXiv access was blocked by
this environment's proxy; no alternate route was used to bypass policy. Thus
this is a source-grounded shortlist and reading agenda, not completed paper
reproduction, an exhaustive literature review or a compatibility guarantee.

A useful system needs several mechanisms. Pipeline/tensor sharding and expert
parallelism are different ways of partitioning a model. A project supporting a
MoE model does not necessarily distribute its experts as indivisible units.
Single-host CPU/GPU offload is also different from multi-host execution.

## Ranked engineering shortlist

| Priority | Project | Lesson to extract | Boundary before adopting |
| --- | --- | --- | --- |
| 1 | [kvcache-ai/ktransformers](https://github.com/kvcache-ai/ktransformers/blob/7fbbc20d31265b266a16dd4a3929f2abf76681e6/README.md) | CPU execution as a first-class resource; CPU/GPU expert masks; uniform/frequency placement and dynamic updates | Hybrid serving stack/hardware-specific kernels, not verified arbitrary multi-host CPU/GPU routing |
| 2 | [PKU-SEC-Lab/HybriMoE](https://github.com/PKU-SEC-Lab/HybriMoE/blob/508a85b9a43dff37124370d8816e411e74827803/README.md) | Joint CPU/GPU scheduling, score-aware expert cache and impact-driven prefetch as author-described goals | Research prototype based on KTransformers; local CUDA/host-memory assumptions do not establish WAN scheduling |
| 3 | [efeslab/fiddler](https://github.com/efeslab/fiddler/blob/227715bfd6e8c731b29548eab01d9919c4fe9564/README.md) | Send activations to resident CPU experts instead of always staging their weights to a GPU | Small 16-bit Mixtral prototype; hard-coded cost estimates and source/comment objective mismatch require audit |
| 4 | [exo-explore/exo](https://github.com/exo-explore/exo/blob/bc412e2230f395e652c23426a5eb88dfa515769b/README.md) | Capacity-based model splitting, topology/backend filtering and device discovery | MLX-oriented stack; do not assume a supported mixed NVIDIA/CPU/Mac cluster or expert-granular scheduling |
| 5 | [b4rtaz/distributed-llama](https://github.com/b4rtaz/distributed-llama/blob/4074c0f3fc02800346ccd6df3293915d4276c3d2/README.md) | CPU/Ethernet execution and explicit cross-node model-memory splitting | Tensor parallelism, not identical to expert sharding; power-of-two/node/head/quantization restrictions |
| 6 | [Relaxed-System-Lab/HexGen](https://github.com/Relaxed-System-Lab/HexGen/blob/949414d1be18e504752508c0559cb966ddf999f4/README.md) | Asymmetric tensor/pipeline groups across heterogeneous GPUs; partition dense layers too | Inspected Llama/CUDA implementation is not a ready mixed CPU/GPU MoE scheduler |
| 7 | [EfficientMoE/MoE-Infinity](https://github.com/EfficientMoE/MoE-Infinity/blob/96a95527028f434f94a616c487094714ef10436b/README.md) | Activation tracing, cached expert residency, prefetch and transfer observability | Current README explicitly supports single-server multi-GPU, not multiple machines; current code differs from paper version |
| 8 | [bigscience-workshop/petals](https://github.com/bigscience-workshop/petals/blob/22afba627a7eb4fcfe9418c49472c6a51334b8ac/README.md) | Split model blocks among machines and study wide-area collaborative inference | Layer/block serving rather than our expert-level boundary; no present-deployment availability or model fit verified |
| specialist reference | [deepseek-ai/DeepEP](https://github.com/deepseek-ai/DeepEP/blob/b5a33eefda39485f438dc764695b71ba7b9249b6/README.md) | Separate token dispatch/combine and expert compute; explicit async completion and redundant-expert movement | Current requirements target Linux, Hopper-or-newer NVIDIA, NVLink/RDMA; not a generic Ethernet/CPU transport |

## Specific implementation lessons, with their actual limits

### KTransformers: an execution/placement baseline

[The pinned CPU-GPU expert scheduling tutorial](https://github.com/kvcache-ai/ktransformers/blob/7fbbc20d31265b266a16dd4a3929f2abf76681e6/doc/en/kt-kernel/experts-sched-Tutorial.md) documents
GPU expert masks, uniform/frequency/front-loading/random placement, recorded
expert distributions and dynamic expert updates. The source project describes
CPU kernels, NUMA-aware inference and SGLang integration. For our experiments,
borrow the *baseline definitions*: fixed budget, uniform versus measured-demand
placement, and an explicit dynamic update switch. Test prefill and decode
separately. We did not inspect the forked SGLang implementation of these flags,
so the tutorial is documented capability, not an independent code audit.
The root README now includes fine-tuning work; it is distinct from the inference
mechanisms of interest here. Do not substitute fine-tuning benchmark claims.

### HybriMoE: cache value differs from lifetime frequency

[KScoreAwareCache](https://github.com/PKU-SEC-Lab/HybriMoE/blob/508a85b9a43dff37124370d8816e411e74827803/ktransformers/operators/experts.py#L662) stores a score per
layer/expert. update_priority_scores takes the p highest-ranked router scores,
uses the first input row, updates those entries with an exponential moving blend
(default alpha .5), and decays other entries. Its p is a rank count (default12),
not cumulative-probability top-p sampling. It selects low-score victims and
high-score prefetch candidates. The examined implementation is therefore a
concrete demand/score adaptation example, not proof of batch-aggregated optimal
placement or the full paper's claimed impact model. Compare it with Colibri's
frequency/recency policy on identical traces and with an eviction/migration
budget. Preserve gate-selected experts; cache priority alone is not permission
to replace logical experts.

Independent static review found an additional score-alignment concern:
`current_priority_scores[mask]` is in ascending expert-ID order, but its assigned
`top_p_scores` remain in descending score order. For ranked IDs `[2,0]` with
scores `[.9,.8]`, the indexed assignment associates `.9` with expert0 and `.8`
with expert2 rather than their corresponding ranked scores. This observation
needs a targeted runtime test before adopting the code; we did not run or fix
upstream. The eviction helper's flat score indexing must also be read with its
callers: the inspected loaded-expert dictionaries use global `expert_uid` keys,
so absence of a separate layer argument is not itself evidence of an offset bug.

### Fiddler: moving activations can beat moving weights

[FiddlerMixtral](https://github.com/efeslab/fiddler/blob/227715bfd6e8c731b29548eab01d9919c4fe9564/src/fiddler/mixtral.py#L13) loads the actual Mixtral model and
assigns CPU/GPU locations; the README explains why small activations can be
cheaper to move than expert weights for small batches. This directly matches
our large-RAM CPU-node idea, although extending PCIe-local execution to a network
requires measuring serialization, link latency, contention and service times.

Two important source details: the constructor sets latency_cpu=7 and
latency_gpu=70 with a TODO to derive them from device configuration. In the
prefill branch (around lines550–590), a comment says minimize the maximum of CPU
and GPU cost sums, but the enumerated configurations are scored by one sum of
selected per-expert costs. Those are different objectives. Treat this as a
bounded source observation requiring further audit, not a paper-level finding
or a verified bug/performance result. Do not copy these constants, silently
resolve the mismatch or call this a measured heterogeneous scheduler.

### exo: reserve capacity before loads finish

[memory_once_loaded](https://github.com/exo-explore/exo/blob/bc412e2230f395e652c23426a5eb88dfa515769b/src/exo/master/placement.py#L161) subtracts pending shard
allocations from reported available RAM so simultaneous loads cannot spend the
same apparently free memory. The inspected placement code filters connected
cycles, memory, model/backend compatibility and RDMA eligibility. Its selected
cycle ranking includes already-downloaded model fraction and available RAM.
[Placement helpers](https://github.com/exo-explore/exo/blob/bc412e2230f395e652c23426a5eb88dfa515769b/src/exo/master/placement_utils.py#L47) include proportional
layer allocation and per-node fit validation.

This is useful capacity/admission engineering. It does not prove a complete
runtime/KV/workspace budget, arbitrary mixed-backend compatibility, or a globally
latency-optimal expert assignment. The README's topology-aware feature claims
must not be generalized beyond the inspected selector. RDMA over Thunderbolt
requires appropriate devices/OS; it is not an ordinary Ethernet feature.

### Distributed Llama: a practical alternative partition boundary

The primary README describes tensor parallel execution over Ethernet, RAM split
across nodes, and Qwen3 MoE CPU/Vulkan support. It also states node counts must be
powers of two, maximum nodes are constrained by model KV heads, and only certain
model/buffer quantization pairs are supported. The root loads and forwards
weights; initial full-model memory materialization was **not** audited. Before
using it as aggregate-capacity evidence, inspect loader peak memory as well as
steady state. We read its README only; no inference or transport code audit.

### HexGen: expert sharding will not place the whole model

[gen_hetero_groups.py](https://github.com/Relaxed-System-Lab/HexGen/blob/949414d1be18e504752508c0559cb966ddf999f4/hexgen/hexgen_core/gen_hetero_groups.py) constructs groups from supplied
hetero_config and pp_partition. It explicitly supports different tensor-parallel
group sizes at different pipeline stages. The supplied partition is not proof
that this helper solves the placement optimization. The core documentation
explains group leaders and cross-stage activation communication. Learn how to
express asymmetric groups and place non-expert layers; do not claim its inspected
Llama/CUDA path implements our CPU-resident expert strategy or reproduces its
paper's optimization/measurements.

### MoE-Infinity: observe residency and prefetch work separately

[ExpertTracer](https://github.com/EfficientMoE/MoE-Infinity/blob/96a95527028f434f94a616c487094714ef10436b/moe_infinity/memory/expert_tracer.py) stores per-sequence layer/expert
selection counts and historical trace collections, and defines I/O stages for
routing, lookup, transfers, wait, computation, eviction, and prefetch lifecycle.
[The prefetch surface](https://github.com/EfficientMoE/MoE-Infinity/blob/96a95527028f434f94a616c487094714ef10436b/moe_infinity/memory/expert_prefetcher.py) includes phase-specific counters and
checks for native scheduling/timing capabilities. Borrow its *observability
questions*: issued versus completed, useful versus late/wasted, queue wait versus
service, and resident bytes. We did not audit its predictor or end-to-end safety.
Hardware/runtime dependencies and CUDA assumptions remain. The current README
explicitly distinguishes the public implementation from its paper version.

### Petals and DeepEP: learn at two different network scales

Petals' primary README describes hosting model blocks across machines and lists
both MoE and dense model families, plus a private-swarm option. Learn about
cross-host layer serving and availability as a comparison boundary; do not infer
expert-granular adaptive placement, support for our example Kimi artifact, or a
working public service from README examples. Its paper links are verified below;
its serving/failover code was not inspected in this pass.

DeepEP's pinned README separates dispatch, expert GEMMs and combine, requires
waiting for asynchronous events before using results, and leaves replication
planning/rerouting to the caller. Its newer interface is EPBuffer; older examples
may target different revisions. The selected requirements include Linux,
Hopper-or-newer NVIDIA, CUDA13.1+, NVLink and RDMA. Useful as a transport-contract
reference or future homogeneous-GPU backend, not a drop-in CPU/ordinary-Ethernet
library. No performance numbers or correctness from either project were adopted.

## Papers to read next, tied to specific questions

These identities and links were verified in the corresponding primary repository
citations. **Full paper text not read in this survey**: the questions are a
reading agenda, not claimed extraction of their exact algorithms/theorems.

| Order | Paper | Question to answer from full primary text |
| --- | --- | --- |
| 1 | [Fiddler: CPU-GPU Orchestration for Fast Inference of Mixture-of-Experts Models](https://arxiv.org/abs/2402.07033), 2024 | When does CPU-resident execution beat GPU weight staging, and how is the cost model calibrated? Reconcile the prototype's comment/code objective discrepancy. |
| 2 | [HybriMoE: Hybrid CPU-GPU Scheduling and Cache Management for Efficient MoE Inference](https://arxiv.org/abs/2504.05897), 2025 | How are computation scheduling, cache scores and prefetch impact jointly defined? What transfers to a network boundary? |
| 3 | [MoE-Infinity: Efficient MoE Inference on Personal Machines with Sparsity-Aware Expert Cache](https://arxiv.org/abs/2401.14361), 2024 | Which trace information predicts future expert demand, how is causality retained, and how much speculative traffic is wasted? Map paper mechanisms to the changed public implementation. |
| 4 | [HexGen: Generative Inference of Large Language Model over Heterogeneous Environment](https://arxiv.org/abs/2311.11514), ICML2024 per primary README | How are heterogeneous memory, compute and interconnect constraints coupled in partitioning? Which assumptions require GPUs or fast collectives? |
| 5 | [Distributed inference and fine-tuning of large language models over the Internet](https://arxiv.org/abs/2312.08361), NeurIPS2023 per primary citation | What must cross slower links, where does request/KV state live, and how are unavailable hosts handled? |
| supplementary | [Petals: Collaborative Inference and Fine-tuning of Large Models](https://arxiv.org/abs/2209.01188), ACL2023 system demo per primary citation | What is the concrete block-serving interface and operational capacity model? |
| supplementary | [KTransformers: Unleashing the Full Potential of CPU/GPU Hybrid Inference for MoE Models](https://doi.org/10.1145/3731569.3764843), SOSP2025 per primary citation | Which hardware-aware inference mechanisms are essential, and which are specific to local NUMA/CPU/GPU kernels? |

HetRoute remains the already-read joint-routing primary paper in this workstream.
The surrounding papers can supply execution, caching and placement mechanisms;
none should be assumed to solve the entire proposed mixed-device system.

## Recommended learning sequence and bounded experiment questions

Start with Fiddler for the activation-versus-weight boundary, then
KTransformers/HybriMoE for CPU/GPU placement and caching. In parallel conceptually,
learn capacity/admission from exo and whole-model partitioning from HexGen.
Compare with Colibri's measured adaptation and MoE-Infinity's trace lifecycle.
Use Petals for slower-network architectural questions and DeepEP only when its
hardware assumptions match. This is study order, not a deployment/install plan.

Possible later simulations, not implemented by this survey:

1. **Execution-location break-even:** same required experts, fixed memory and
   precision; compare CPU execution plus activation transport with staging exact
   weights to GPU. Use measured service/transfer curves and separate prefill/decode.
2. **Placement adaptation:** fixed demand trace and past-only observations; compare
   static, frequency-only, decayed score/recency and cost-aware placement. Hold
   capacity fixed and count migration bytes, transient duplicate residency,
   misses, tails, and adaptation under a workload switch.
3. **Parallelism boundary:** compare expert-level dispatch against layer/pipeline
   and tensor partition models for the same capacity target; charge collectives,
   link latency and synchronization. Do not compare unlike model/quality settings.

First require feasible per-host/tier placement, including all non-expert runtime
state. Then report absolute latency/throughput and failures for the feasible
configuration; a model that cannot load on one device has no useful single-device
speedup ratio. Numerical validation remains independent of scheduling scores.
No new machines, checkpoints, full-model generation, #2 work, product changes,
merges or native Mac acceptance claims result from this survey.


## Affordable local AI as a foundation for an AI OS

Human clarification, 2026-10-17: the eventual application is a useful local AI
assistant/AI OS on affordable hardware. SPOJ can investigate the inference and
resource-management foundation. This does not authorize building an agent OS,
new kernel, full-model runner or hardware deployment now. Distinguish three
layers: agent/tool/context management; model execution/placement; host OS/drivers.
A lean host OS or faster control language is a hypothesis to test, not a remedy
for an unmeasured bottleneck.

Five additional primary repository READMEs were read at pinned revisions below.
Their hashes/revisions and static-only scope are recorded in
`local-ai-os-sources.json`. No full paper text or implementation code was audited
in this extension; no setup scripts, builds, downloads of weights or benchmarks
were executed. Paper links/identities are from these primary READMEs.

| Primary source / reading | Useful question | Limit |
| --- | --- | --- |
| [OpenCPIL/prima.cpp](https://github.com/OpenCPIL/prima.cpp/blob/288df6a2cc2120387e12d6f40798f30cc525c9ea/README.md); [Prima.cpp: Fast 30-70B LLM Inference on Heterogeneous and Low-Resource Home Clusters](https://iclr.cc/virtual/2026/poster/10008093), ICLR2026 per author citation | Direct baseline for home-device layer placement, profiling, CPU/GPU offload and deciding that a weak device should receive no work | README-level inspection only; mmap/prefetch claims are not bounded all-RAM capacity or latency guarantees. GPU-support descriptions need reconciliation before a cross-platform claim. |
| [Tiiny-AI/PowerInfer](https://github.com/Tiiny-AI/PowerInfer/blob/8bd56d69906c9d2dba4d3bf6899763401e01a9a4/README.md); [PowerInfer: Fast Large Language Model Serving with a Consumer-grade GPU](https://arxiv.org/abs/2312.12456) | Hot/cold neuron placement and sparse CPU/GPU co-computation on consumer hardware | Uses activation-sparse models/predictors and a special format; not automatically compatible with an unchanged arbitrary Qwen/MoE checkpoint. |
| [PowerInfer-2](https://arxiv.org/abs/2406.06282), linked in the PowerInfer primary README | What memory/execution scheduling can make smartphone inference practical? | Paper lead only, full text/code not examined; reported TurboSparse-model results cannot be transferred to arbitrary models or hardware. |
| [FMInference/FlexLLMGen](https://github.com/FMInference/FlexLLMGen/blob/004ffef82b46e8dc8685c55d0cdda650bdaf1269/README.md); [FlexGen paper](https://arxiv.org/abs/2303.06865) | How should weights, activations and KV cache be placed among GPU, CPU and storage, and how can scheduling overlap movement? | Its primary target is high-throughput large-batch processing, not low-latency interactive agent turns. |
| [agiresearch/AIOS](https://github.com/agiresearch/AIOS/blob/292d98f78c835499df18cdb6de6325bba1895862/README.md); [AIOS: LLM Agent Operating System](https://arxiv.org/abs/2403.16971) | How should an agent layer schedule model calls, manage contexts/memory and coordinate tools? | README explicitly places the AIOS kernel above the host OS kernel. It does not establish faster device execution through replacing Linux/macOS. |
| [ix-project/ix](https://github.com/ix-project/ix/blob/550bf28a4ddd5fafcec707a14acd502712a10dae/README.md) | Under what conditions does protected dataplane / kernel-bypass networking reduce software I/O overhead? | Historical specialized OS research reference, not an inference benchmark or recommended default platform. README specifies DPDK and particular Intel NICs; accelerator/backend compatibility is unverified. |

Prima.cpp deserves earlier baseline consideration than an assumption that no
existing system attempts the whole home-cluster problem. Its README describes
profiling compute, disk, memory and OS behavior, selecting device/layer assignments,
CPU/GPU offload and piped-ring/prefetch strategies. It documents dropping weak
nodes rather than forcing every device to participate. However, its benchmark
table includes an Apple Metal device while its FAQ says GPU support is CUDA-only;
this inconsistency must be resolved against the exact backend/source before
claiming a supported mixed GPU deployment. Its memory-pressure statements rely on
mmap/page-cache behavior, not evidence that all weights reside in aggregate RAM.
No headline model-size, memory-pressure or speed claim is adopted here.

### Networking versus OS versus memory: distinguish mechanisms

- **Memory feasibility and locality:** sufficient usable RAM/VRAM, including
  dense/KV/workspace state; bytes resident per tier; page faults and expert loads.
- **Compute and memory bandwidth:** expert/kernel time, memory traffic and CPU
  versus GPU service curves. Resident weights still need to be read each use.
- **Communication:** payload bytes, serialization/copies, directional transfer,
  queue wait, RTT and the number of dependent request/response crossings.
- **OS/control overhead:** CPU time in scheduling, syscalls, wakeups, context
  switches, allocation and polling, plus background interference. OS overhead can
  matter, but is not established by observing that two machines are involved.

A higher-bandwidth link does not remove latency from many small, sequential
crossings. For an illustrative arrangement with 32 dependent layer boundaries,
each requiring a 2 ms remote round trip, that structure contributes about 64 ms per
forward before computation/extra transfer; this is not a measurement or a universal
bound for arbitrary overlapped/batched execution. Kernel bypass can reduce the
software part of a transfer, not abolish propagation, wire serialization or
model dependencies. RDMA/zero-copy can help specific paths without replacing the
whole OS, but require suitable hardware and compatible software.

Python control code already calls native PyTorch/C++/accelerator kernels. A C++
or Rust rewrite only accelerates the measured portion actually replaced. As a
hypothetical Amdahl calculation, if all removable control overhead is 5% of the
critical path, eliminating it entirely gives at most `1/(1-.05) = 1.053x` speedup.
This is not the overhead fraction of SPOJ; it explains why profiling must precede
choosing a language. A smaller OS may recover RAM or reduce contention, which are
useful independent effects, but they need measured capacity/latency evidence.

### Define 'fast enough' around the application

For a future local AI OS, specify representative tasks, model-quality/tool-use
success, context sizes, acceptable first-response and full-turn time, concurrent
agents, resident working set, and power/cost limits. Report per-turn latency and
tails alongside TTFT and token rate; tool execution, prompt preparation and
context growth also contribute. A small model meeting the task target may be a
better configuration than a large distributed model. This is an evaluation
question, not a claim that a smaller model is adequate for the target tasks.

Possible later falsifiable comparisons, not started here:

1. Lean host configuration versus ordinary host setup at fixed kernels, workloads,
   memory reserves and device clocks: measure reclaimed memory, context switches,
   scheduler delays and end-to-end latency; reject claims based only on process
   count or an idle microbenchmark.
2. Local resident expert versus remote resident expert versus GPU staging at fixed
   expert identity and precision: separately measure service, queue, transport and
   load costs with controlled cold/warm state and batching.
3. Existing partitioned engine versus a minimal experiment at the same task/model
   target: include startup/steady-state capacity, topology, rejected requests,
   quality, and end-to-end interactive latency. Model selection and approximation
   are separate experimental changes, not silent expert-routing modifications.

No single bottleneck has been diagnosed for the proposed deployment because no
such hardware/workload deployment has been measured. Keep the main correctness
and native Mac acceptance gates intact; do not start a new OS or transport rewrite
from this reading agenda.


## Memory hardware, far memory and near-memory computation

Human direction, 2026-10-17: investigate research-backed combinations of faster
memory expansion, heterogeneous execution and affordable lab devices before
purchasing hardware or building another runtime. This is a reading/experiment
agenda only. It does not authorize procurement, testbed allocation, OS/BIOS/kernel
changes or product implementation.

### Separate capacity, bandwidth, access latency and execution location

Extra memory is useful only with its access path made explicit. CXL expansion,
RDMA-accessed remote RAM, another GPU's VRAM, and an SSD are different tiers;
there is no generic adapter that turns them into one equally fast GPU-memory
pool. CXL Type-3 expansion requires a compatible host CPU/root complex, firmware,
OS and device. CPU-visible CXL memory is not automatically ordinary GPU-local
VRAM. Pooling across hosts adds fabric/control/platform requirements beyond a
single expander. More GPU/HBM capacity likewise requires supported accelerator
interconnects and software placement, not ordinary DIMM-style VRAM expansion.

Remote memory retrieves bytes for execution elsewhere; remote expert execution
sends activations to compute near resident weights. Processing-in-memory (PIM)
puts programmable computation in or near the memory itself. Their useful regimes
can differ even with identical model semantics. Adding capacity can introduce a
new bandwidth bottleneck; concentrating a hot set in faster memory can help only
if its load/migration/eviction cost is repaid. Quantization/compression can reduce
bytes too, but representation and model-quality changes need separate baselines.

| Direction | Possible benefit | What to measure / verify |
| --- | --- | --- |
| Larger/more-channel local DRAM, correct NUMA placement | Capacity and local memory throughput without a remote protocol | Actual usable bytes, channels/topology, bandwidth under expert kernels and CPU service, not DIMM headline speed |
| CPU-attached CXL DRAM tier | More addressable capacity with memory load/store access on a compatible platform | Latency/bandwidth under concurrency, NUMA/tiering behavior, page placement and GPU staging paths; no assumed VRAM equivalence |
| Remote DRAM over TCP/RDMA | Pool otherwise unused RAM across hosts | Effective transport, remote bytes, page/object locality, cache misses and tails; RDMA saves some software/remote-CPU work but not all wire cost |
| Remote CPU/GPU expert execution | Move smaller activation payloads instead of repeatedly fetching expert weights | Expert service versus activation transfer and queue wait; batching, residency and synchronization |
| Programmable PIM / FPGA near memory | Reduce data movement through custom kernels near stored bytes | Kernel mapping, precision, local memory limits, host exchange, control overhead and end-to-end correctness; no drop-in PyTorch assumption |
| Cold NVMe backing plus demand-aware hot memory | Make an oversized model runnable with a bounded faster working set | Cold/warm and phase-switch behavior, actual storage reads, migration traffic and latency; capacity alone is not interactive usefulness |

### Research artifacts and papers worth prioritizing

Nine primary READMEs and three small LIA allocation/configuration sources were
inspected at pinned revisions. Their hashes are in `memory-hardware-sources.json`.
These are artifact/code observations and verified repository citations, **not
full-paper reviews or reproduced performance results**. A publisher-hosted Leap
PDF request returned HTTP403; a guessed Pond author-repository PDF path returned
404. Neither failed lookup establishes that the papers are unavailable elsewhere.
No alternate route bypassed the environment proxy.

| Reading / primary artifact | What it can teach us | What its accessible artifact establishes |
| --- | --- | --- |
| **Pond: CXL-Based Memory Pooling Systems for Cloud Platforms**, ASPLOS2023 per citation; [MoatLab/Pond](https://github.com/MoatLab/Pond/blob/5ac0e66b3624b9324cc9042abcd930127005d4bc/README.md) | Capacity pooling, tier-placement experiments and how to emulate a computeless memory tier | Authors explicitly describe this repo as emulation/evaluation scripts, not the full Pond system. They use a two-socket NUMA server with remote-socket cores disabled; this is not a real CXL fabric demonstration. |
| **LIA: A Single-GPU LLM Inference Acceleration with Cooperative AMX-Enabled CPU-GPU Computation and CXL Offloading**, [paper DOI](https://doi.org/10.1145/3695053.3731092); [ece-fast-lab/ISCA-2025-LIA](https://github.com/ece-fast-lab/ISCA-2025-LIA/blob/e6dd47d36fcfa45ffa411e70920681828d04301b/README.md) | Combine CPU matrix acceleration, GPU work and a larger memory tier | README lists fourth-generation-or-newer Intel Xeon and NVIDIA A100/H100. Selected CXL allocator uses NUMA nodes2/3 and a machine-specific library path. Actual physical CXL configuration and resulting tensor page residency remain unverified here. Large-batch example scripts are not interactive latency evidence. |
| **Infiniswap**, NSDI2017 per primary [paper link](https://www.usenix.org/conference/nsdi17/technical-sessions/presentation/gu); [SymbioticLab/Infiniswap](https://github.com/SymbioticLab/Infiniswap/blob/da7c14bf749ccadb4ef44953579d55143e8e7182/README.md) | Transparent remote-memory paging and decentralized slab placement | An RDMA paging design with historical kernel/NIC prerequisites, not ordinary remote expert execution or a validated current-kernel installation. |
| **Leap: Faster Data Path for Remote Memory**, USENIX ATC2020 per citation; [SymbioticLab/Leap](https://github.com/SymbioticLab/Leap/blob/13787f2bb5e4cf830e7ff05c189a81c295645022/README.md) | Predictive page prefetch and removing overhead from the remote-memory path | Kernel-integrated remote paging with documented Mellanox/InfiniBand prerequisites. No source benchmark result was reproduced. |
| **AIFM: High-Performance, Application-Integrated Far Memory**, [OSDI2020 paper](https://www.usenix.org/conference/osdi20/presentation/ruan); [AIFM-sys/AIFM](https://github.com/AIFM-sys/AIFM/blob/fa4f31ce827501ad52f5a5ca9249ef04ba92b467/README.md) | Application semantics, object-level caching and movement rather than anonymous paging alone | README exposes C++ far-memory pointers/containers over TCP and recommends a particular CloudLab profile. It is not a transparent PyTorch tensor allocator or verified drop-in on our hosts. |
| **PIM is All You Need: A CXL-Enabled GPU-Free System for LLM Inference (CENT)**, ASPLOS2025 per citation; [Yufeng98/CENT](https://github.com/Yufeng98/CENT/blob/4c2aac6ce6aa3ddfe1944fc9c5d656b90d3fc7d2/README.md) | Compute near memory, model dataflow and a CXL-connected PIM architecture | Accessible artifact is trace generation, AiM performance simulation, power/cost modeling and figure reproduction. Do not present it as a working retail GPU replacement or physical hardware test. |
| **Benchmarking a New Paradigm: An Experimental Analysis of a Real Processing-in-Memory Architecture**, [arXiv2105.03814](https://arxiv.org/abs/2105.03814), plus later versions in the primary bibliography; [CMU-SAFARI/prim-benchmarks](https://github.com/CMU-SAFARI/prim-benchmarks/blob/67179099730cdccc650d52d25f458cb2e4f8a675/README.md) | Characterize real UPMEM PIM and kernel suitability, including GEMV/MLP and transfer microbenchmarks | PrIM documents real-module execution and an SDK functional simulator. Simulator wall-clock speed is not hardware throughput. Current availability/support of modules and SDK requires confirmation. |
| [upmem/dpu_demo](https://github.com/upmem/dpu_demo/blob/938fbcdb74f0713567b93f24af841cf0ce4af30c/README.md) | A small vendor-provided starting point for host/DPU programming | Example checksum with CPU/Python host APIs; not an LLM benchmark. UPMEM DPUs are DRAM processing cores, not the same device class as networking SmartNIC DPUs. |
| **CXL-SpecKV**, [DOI listed by repository](https://doi.org/10.1145/3748173.3779188); [FastLM/CXL-SpecKV](https://github.com/FastLM/CXL-SpecKV/blob/0eb12ad0429c00c961fec1d4f4f16279efe61712/README.md) | FPGA-assisted KV-cache tiering/prefetch/compression, potentially relevant to long contexts or many agents | Lower-confidence follow-up: paper identity/physical board, bitstream, measured setup and headline numbers have not been independently validated. KV-cache capacity is different from expert-weight capacity. No performance/accuracy claim is adopted. |

Pond's NUMA approximation does not reproduce every aspect of CXL protocol,
switching, contention or device firmware; its cited latency is an emulation
target, not our measured hardware latency. Never run its core-disabling/memory
configuration scripts as a casual benchmark setup. LIA's selected allocator
shows how nodes are selected, not proof that a particular tensor remains on CXL
through framework storage construction/copies; a later experiment must verify
actual pages and account for temporary allocations. Those are validation tasks,
not findings of runtime failure.

The PrIM README reports the original SDK site as deprecated and points to a
CMU-SAFARI SDK archive. That is a dependency/support issue to investigate before
choosing a lab platform, not evidence that modules can currently be purchased.
CENT's complete simulation is documented as hours and substantial disk/memory;
inspect a bounded reproduction plan before running any simulation. This study
ran none of those commands.

### A lab ladder before any purchase

| Stage / possible device access | Small experiment to consider | Supported conclusion and limit |
| --- | --- | --- |
| Existing host with NUMA nodes, ideally a borrowed two-socket server | Compare local versus remote NUMA allocation at fixed thread placement, footprint and expert/GEMV workload; audit actual page placement | Sensitivity to a slower tier and locality, not a CXL performance claim |
| Two existing ordinary machines | Compare exact expert execution at the memory-owning host with fetching its weights to the compute host; account for initial loading and repeated reuse | Application-level compute-versus-data movement break-even on that actual link, not arbitrary RDMA/CXL behavior |
| Borrowed/testbed RDMA-capable hosts and compatible fabric | Measure remote read sizes, concurrency, latency/tails and CPU cost versus TCP and local RAM | Whether one-sided access helps that workload; neither transparent infinite RAM nor a proof of model correctness |
| Compatible CXL host plus Type-3 expander supplied by a lab/vendor | Enumerate real memory topology and compare local/CXL page placement, bandwidth, load time and capacity at fixed model/kernel settings | Real tier behavior for that exact CPU/firmware/device/software configuration; no assumed GPU-local bandwidth |
| UPMEM functional simulator, then a compatible real PIM server if accessible | Validate one GEMV/expert subkernel against a CPU oracle; charge all host/device transfers before testing a larger workload | Kernel feasibility first; performance requires hardware data or separately validated timing models |
| CXL/FPGA or CENT-like architecture simulation | Inspect the paper/model, reproduce one bounded point and sensitivity to assumptions before large runs | Research-model conclusions only, not a purchasing recommendation or physical speedup |

AIFM documents CloudLab xl170 as its tested target, so research testbeds are one
possible access route. Eligibility, current inventory (especially CXL/PIM), cost,
quotas and available reservations were not checked. No account, reservation,
purchase or vendor contact was made. Buying a generic PCIe card or GPU-memory
modification is not justified by these papers or by this study.

### A promising combined hypothesis, rather than a hardware shopping list

Keep frequently used experts in the fastest appropriate tier; keep other required
experts in larger local/CXL/remote memory. At execution time choose between moving
activation rows to resident compute, fetching a reusable weight shard to faster
compute, and retaining work locally. Use past-only demand and service/transfer
observations; adapt residency more slowly with hysteresis and a transfer budget.
Where PIM is involved, treat its kernels and numerical behavior as a separately
validated backend, not interchangeable native HF execution.

Compare equal logical work, chosen precision, usable capacity, cache preparation,
batch/context sizes and hardware cost assumptions. Record unique versus replicated
weight bytes, KV/workspace reservations, actual peak memory including staging,
bytes moved, useful/wasted prefetch, page faults, queue wait, service time and
end-to-end interactive latency. Distinguish observed data from modeled values;
report failures and workload changes. Do not sum overlapping phase timings to
claim a prediction without checking the critical path. No 'super-fast memory'
claim follows from nominal link speed or a paper's capacity headline.

The first research comparison worth designing is **compute near weights versus
move weights to compute**, with slower-tier sensitivity and warm/cold reuse.
It can use ordinary hardware first and tell us which specialized device, if any,
would address the measured bottleneck. No existing correctness source, native
Mac gate, #2 scope or hardware authorization is changed by this agenda.


## Software research atlas and Apple / heterogeneous execution paths

Human direction, 2026-10-17: broaden discovery before choosing a design; include
software papers, Apple Silicon, Thunderbolt/RDMA, colder experts on other hosts,
and combinations with the memory-hardware research above. This extends the same
issue #7 / PR #8 research stream. No new runtime, hardware experiment, model
execution or implementation issue is started.

### Evidence ledger and how to grow the collection

This pass inspected documentation from **21 primary project repositories**, plus
one explicitly secondary MoE bibliography, at pinned revisions. Eight selected
source/documentation files and one author-hosted 13-page technical report add
specific depth below. `software-mac-sources.json` records all 31 file hashes and
revisions; `software-paper-backlog.json` records paper citations, source level,
open questions and reading status. Some projects refresh earlier survey entries;
these are not all newly discovered projects. No primary project was installed,
imported, compiled or run. No project performance number becomes SPOJ evidence.

The Flash-MoE report was read in full after PDF text extraction; its peer-review
status is not established. Other paper links here were checked in the cited
project documentation or explicitly secondary bibliography, not read as full
papers. Do not confuse a verified citation with a verified method/result.
GitHub search is bounded discovery, not exhaustive literature coverage. Previous
arXiv/publisher access restrictions remain; no alternate route bypassed policy.

Use the collection in four stages: discovered citation; primary full text and
artifact inspected; method/assumptions extracted; independently reproduced or
rejected. Record negative findings, exact versions, hardware/workload, semantic
changes, initialization costs and author claims separately from observations.
Snowball references and citing papers around each mechanism; deduplicate by
paper identifier and canonical repository. Select the next full-text reads by
which uncertainty they resolve, rather than accumulated paper count.

### A mechanism map rather than one competing architecture

| Mechanism | Primary projects / papers | Question to resolve for SPOJ |
| --- | --- | --- |
| Mac execution and collective communication | MLX, MLX-LM, JACCL; exo | Which topology/backend is supported on our exact Macs, and what are actual payload-size latency/throughput and memory costs? |
| Resident CPU experts vs GPU staging | KTransformers, Fiddler, HybriMoE; previous source studies | When does sending activations beat fetching weights, including CPU service and queues? |
| Cache and predict future expert demand | Colibri, Mixtral offloading, SiDA; ProMoE / MoE-Lightning reading leads | Do demand-aware policies beat LRU/static residency after charging wrong prefetch and migration? |
| Identical-expert replication and placement | DeepSeek EPLB; HetRoute restricted replica interpretation | How much capacity is spent to reduce load/communication, and how does heterogeneous service change the policy? |
| Communication scheduling / overlap | DeepEP, FastMoE/FasterMoE, Tutel; Lina reading lead | Which dependency-safe overlap and batching ideas transfer beyond datacenter GPU fabrics? |
| Request/KV locality and prompt reuse | vLLM/PagedAttention, SGLang, LMCache, Mooncake | Does repeated agent context dominate cost enough that KV reuse matters more than expert placement? |
| Prefill/decode resource separation | DistServe, Dynamo, Mooncake | When do different phase optima repay KV handoff and extra resident resources? |
| Transport and memory-tier interfaces | JACCL; NIXL, Mooncake Transfer Engine; hardware section | Reuse interfaces and telemetry without assuming their platform support or kernels transfer to Macs. |
| Compression, changed routing, reduced expert count | HOBBIT / Pre-gated MoE / Flash-MoE and quantization reading paths | What computation/quality contract changes? Keep these comparisons separate from exact execution. |

The previously studied Prima.cpp, HexGen, distributed-llama, Petals, PowerInfer,
MoEInfinity, exo, Colibri and hardware-memory artifacts remain in this same index.
No claim that SPOJ uniquely supports distribution, heterogeneous scheduling,
expert caching or cost-aware placement survives this prior-art map.

### Apple Silicon: concrete support and important boundaries

Official MLX distributed documentation now describes three distinct paths:

1. **TCP/IP over Ethernet or Thunderbolt**, including MLX's ring backend. The
   ring documentation restricts arbitrary-rank send/recv; a coordinator/expert
   star cannot assume that collective backend exposes the exact point-to-point
   pattern it needs.
2. **JACCL RDMA over Thunderbolt 5**, documented from macOS26.2, with SDK26.2+
   requirements in the library README. Enabling it requires recovery-mode
   configuration; this is a host-access prerequisite, not something to promise
   a remote agent can silently enable. No host was configured here.
3. **NCCL for CUDA environments**, documented separately. Launching a Linux CUDA
   job from a Mac is not proof of one mixed Metal/CUDA collective or expert
   execution group. Cross-platform data types, numerical behavior, transport
   interoperability and failures need explicit tests.

There is a material documentation/version discrepancy: MLX's high-level guide
says JACCL only supports a fully connected mesh, and its launch auto-configuration
checks a mesh. The nested JACCL README also advertises a ring; selected
`jaccl.cpp` validates rings and constructs `RingGroup`, including a preference
flag. Thus **do not infer either universal mesh-only support or working arbitrary
rings from one document**. Freeze the library/wrapper/config-tool versions and
verify supported operations/topology together. A direct mesh needs n(n-1)/2
pair links before considering port/controller constraints; a ring has different
communication paths. This is topology arithmetic, not a benchmark.

The selected RDMA source loads verbs functions, registers memory and uses a TCP
side channel for connection metadata. RDMA data movement does not mean every
control path disappears, nor does it expose a transparent coherent memory pool
across Macs. JACCL collectives are not themselves an expert-placement algorithm.
The standalone library README says caller output buffers must already exist;
selected mesh implementation also allocates/registers internal communication
buffers, which later memory accounting must include.

exo's README adds model/OS/port/cable caveats and currently describes Linux
execution as CPU while Mac execution uses GPU. Its headline speedups were not
reproduced. SGLang's README lists Apple Metal/MLX and vLLM lists an Apple plugin;
these platform listings do not establish feature parity with their CUDA paths,
JACCL support, or arbitrary Mac/NVIDIA interoperability. NIXL explicitly lists
Linux-only support and no native macOS support in the inspected revision.

MLX-LM documents memory wiring on macOS15+ and prompt/KV caching. Wired-memory
limits do not create extra physical capacity. Unified CPU/GPU memory on one Mac
must be counted once. Its example sharded generation exposes pipeline and tensor
modes, not proof of the expert-granular heterogeneous scheduler proposed here.
An MLX/Metal backend would need its own declared numerical contract and oracle
checks; the existing native Mac acceptance gate is still outstanding.

### New software artifacts and precise lessons

| Artifact | What the inspected documentation/source says | Limits / next evidence |
| --- | --- | --- |
| [ml-explore/mlx](https://github.com/ml-explore/mlx/blob/b6642e604843776705b57b1eaecb6f57e519b793/README.md) | Distributed API, ring TCP, JACCL and NCCL; selected official docs and three JACCL C++ files inspected. | Test exact topology/backend and operations, actual transfers, singleton fallback, synchronization and memory overhead on native hosts. |
| [ml-explore/mlx-lm](https://github.com/ml-explore/mlx-lm/blob/93e6d4a6447b3080861985947f0820e76fcb957d/README.md) | Distributed inference, prompt cache and memory wiring; selected sharded example inspected. | Example accepts pipeline/tensor modes; model-specific sharding and expert placement still require source audit. |
| [ml-explore/mlx-examples](https://github.com/ml-explore/mlx-examples/blob/796f5b53cab69a3d48a44233ce21aae889e94a08/README.md) | Standalone learning examples including Mixtral. | Educational starting point; no distributed expert result established. |
| [exo-explore/exo](https://github.com/exo-explore/exo/blob/bc412e2230f395e652c23426a5eb88dfa515769b/README.md) | Mac model partitioning and Thunderbolt RDMA configuration documented. | Existing baseline to study before building; present README limits Linux acceleration and lists topology/port/version caveats. |
| [deepseek-ai/EPLB](https://github.com/deepseek-ai/EPLB/blob/d52c72d5b2f2fb4c41afbf8eb21366820239913d/README.md) | Estimated-load input, redundant experts and hierarchical/global packing; eplb.py read. | Equal-size replica slots and equal item counts per pack; no arbitrary memory budgets, measured device rates, link/queue costs or migration protocol supplied. |
| [dvmazur/mixtral-offloading](https://github.com/dvmazur/mixtral-offloading/blob/ce545188b804238f0b23a59fc45e6a8f8b390c40/README.md) | Mixed HQQ quantization, individually offloaded experts and LRU residency. | README explicitly calls speculative expert prefetch upcoming; do not treat the paper and repo as identical feature sets. |
| [timlee0212/SiDA-MoE](https://github.com/timlee0212/SiDA-MoE/blob/752882890c788551f071970c051548b2fb757567/README.md) | Short README documents activation collection and sharded checkpoints. | Disk offload and above-main-memory shard handling are TODOs there; the complete paper design is not established by this README. |
| [ranggihwang/Pregated_MoE](https://github.com/ranggihwang/Pregated_MoE/blob/6b0a6660ea792a7a9e128c592fa4641d11228dc8/README.md) | ISCA24 proof-of-concept artifact with GPU/container/build/evaluation directions. | Algorithm-system co-design is a separate semantic review; do not assume pretrained HF gate equivalence from its title. |
| [laekov/fastmoe](https://github.com/laekov/fastmoe/blob/55af4f98eee087cf5b3aac34318abf80c3bcbafd/README.md) | Distributed experts and data/expert parallel distinction in a PyTorch/CUDA/NCCL training system. | Training throughput/gradient communication differs from batch-one inference; backend/version requirements apply. |
| [thu-pacman/FasterMoE](https://github.com/thu-pacman/FasterMoE/blob/de4d5ac7547978bad56fed716d1a78203e9b64d7/README.md) | Training prototype documents dynamic shadowing, schedule fusion and topology-aware gate; cleaner integration is referenced in FastMoE. | Extract mechanisms; a topology-aware learned gate can change logical expert selection and is not an exact scheduler drop-in. |
| [microsoft/Tutel](https://github.com/microsoft/Tutel/blob/175ad8075acf7783e42d8de4473aa120dcc9e4d0/README.md) | Adaptive MoE implementation with distributed examples and inference documentation; primary Tutel paper citation present. | Current README mixes paper-era design with new serving/model claims; pin version and audit precision, workload and capacity before comparing. |
| [deepseek-ai/DeepEP](https://github.com/deepseek-ai/DeepEP/blob/b5a33eefda39485f438dc764695b71ba7b9249b6/README.md) | Expert dispatch/combine communication primitives and platform-specific paths. | Separate kernel/transport cost from expert math; do not assume Metal or commodity TCP compatibility. |
| [vllm-project/vllm](https://github.com/vllm-project/vllm/blob/7879f3687b5b6a4be4754242e70b9c21cf7b4183/README.md) | PagedAttention, batching, prefix caching, distributed modes and several backend/plugin paths. | Use as an engine/baseline where supported; README platform list does not prove uniform feature combinations. |
| [sgl-project/sglang](https://github.com/sgl-project/sglang/blob/05ce0e980f00aa80864190d6f1cd5d9b685802f1/README.md) | Serving framework with agentic workload focus and multiple hardware paths, including Apple. | Inspect actual Apple platform guide/backend before choosing features or claiming mixed-device support. |
| [LMCache/LMCache](https://github.com/LMCache/LMCache/blob/f24bfe9840599f796c844ac7bdfb6be791be8122/README.md) | Tiered KV reuse/offload, engine integrations, transport backends and observability. | Expert weights are a different object; non-prefix CacheBlend/recompression/token dropping need separate numerical/quality validation. |
| [kvcache-ai/Mooncake](https://github.com/kvcache-ai/Mooncake/blob/19e0ab28f125346f7348e8ac9d043537d7202771/README.md) | Transfer Engine, multi-tier Store and EP/process-group functionality described; paper/traces linked. | Paper-era KV system and current broader repo must be separated. Routing around failed ranks is not exact recovery of an unavailable required expert without a valid replica or explicit failure. |
| [LLMServe/DistServe](https://github.com/LLMServe/DistServe/blob/82831f1604cc6b10bebd360f6c437a07790dde9f/README.md) | Separates prefill/decode, with KV communication, Ray workers and a CUDA-oriented backend. | README requires at least two GPUs for its example; extra resources and KV movement may lose for a small interactive setup. |
| [ai-dynamo/dynamo](https://github.com/ai-dynamo/dynamo/blob/a29a9fde28df161df3c3e19f9170274789f698b1/README.md) | Orchestration above engines: KV-aware routing, phase separation, caching, planning and telemetry. | Reuse policy questions, not the entire datacenter stack. Request routing differs from token-to-expert routing. |
| [ai-dynamo/nixl](https://github.com/ai-dynamo/nixl/blob/0fe526d1aa2fd10091b7ae7fb7b735c0b1103bc0/README.md) | Plugin abstraction for CPU/GPU/storage point-to-point movement, benchmark and telemetry hooks. | Explicit Linux-only support; no native Mac claim. Data movement is not scheduling or numerical correctness. |
| [deepseek-ai/FlashMLA](https://github.com/deepseek-ai/FlashMLA/blob/0f11e178da1f67becb087a324b400854931ec3e3/README.md) | Model/hardware-specific attention kernels. | Current README records a breaking change removing Hopper/earlier-model support and changing KV formats; old benchmark assumptions cannot be carried to HEAD. |
| [danveloper/flash-moe](https://github.com/danveloper/flash-moe/blob/3601d41882a346d85041f7955c66429d248e8cd9/README.md) | C/Metal expert streaming, OS-cache experiments and an author technical report. | Interesting negative-result source; semantic changes and internal report/README discrepancies prevent treating its throughput as exact-model evidence. |

#### EPLB: a useful small algorithm, not yet our optimizer

The selected source replicates the expert maximizing estimated load divided by
its current replica count, then greedily packs sorted loads into equal-count
bins; the hierarchical path first packs expert groups to nodes. This is a
concrete simple baseline worth understanding. The source leaves load prediction
out of scope. It does not normalize by heterogeneous service rates or model
network contention, migration, replica initialization and unequal expert byte
sizes. These are reasons to compare/extend a baseline later, not a proven defect.
Identical replicas preserve logical expert identity only when payloads, weights,
precision and dispatch/reconstruction are validated; replication consumes memory.

#### Flash-MoE: read the raw report before adopting the headline

The 13-page author-hosted report and current README are not a controlled parity
comparison. Report sections3.2/4.5 reduce routing from top10 to top4, section3.4
requantizes experts to two bits, and section5.5 describes skipping expert forward
computation for nonfinal prefill tokens. These alter the computation contract;
we cannot count resulting throughput as unchanged-model distributed correctness.
Coherent answers on a few prompts and small weight RMSE are not full-model parity
or tool-use acceptance evidence.

There are useful unresolved source discrepancies to investigate before using
this project as a baseline:

- PDF abstract/section4.4 describe two-bit output as production-quality or
  indistinguishable in their examples; current README says two-bit breaks JSON
  tool calling and recommends four-bit. Record exact revision/config/task.
- PDF section4.3 says 43–57% of512 experts appear per layer across30 tokens. If
  that statistic uses its top4 configuration, only120 selections are possible,
  at most23.4375% distinct experts. Resolve the run/configuration/count definition
  before fitting a cache model; do not invent a runtime explanation.
- PDF section5.5's prefill omission needs a dependency-level audit and numerical
  oracle test. Earlier-token hidden states can affect later layers' attention
  state; overwriting a buffer is not proof its computation was unnecessary.
- PDF discussion claims a cross-Thunderbolt extension of unified memory; no
  transparent coherent shared-memory implementation was established here.
  Current README's universal 'hardware-optimal' no-overlap wording also needs
  measurements under varied kernels, cache states and workloads.

Its reports that explicit caches/prefetch can lose are valuable hypotheses:
compare OS-managed paging with explicit bounded caching at equal total memory,
record physical reads versus page-cache hits and compressor activity, and audit
CPU/GPU/I/O contention. Do not copy author speedups, SSD bandwidth, lack-of-OOM
claims or qualitative quality labels into SPOJ conclusions. No engine or model
was run in this study.

### Paper reading queue and candidate combinations

`software-paper-backlog.json` is the deduplicated queue for this extension. It
includes primary-artifact citations for Mixtral offloading, Pre-gated MoE,
FastMoE/FasterMoE, Tutel, PagedAttention, DistServe, Mooncake, LMCache,
CacheGen/CacheBlend, TENT and partial-rank failure work. Secondary discovery
leads include ProMoE, MoE-Lightning, HOBBIT and Lina. LLM in a Flash is a
reference found in the Flash-MoE report; its primary full text remains unread.
SiDA's paper citation is a discovery lead alongside its thin primary artifact.
Do not confuse the diffusion-routing repository named ProMoE with the
proactive-caching inference paper. Links are not performance endorsements.

| Candidate combination, all explanatory proposals | Why it might help | Falsifier / required evidence |
| --- | --- | --- |
| Two supported Macs over TB5/JACCL plus an ordinary TCP/Ethernet expert host | Low-latency fast tier plus cheaper colder-expert capacity | Native exact-backend parity and topology first; a required cold expert can still dominate every token that selects it. Measure p95/p99 and decode barriers, not frequency alone. |
| Mac hot expert replicas plus CPU/RAM canonical owners | Reduce common-path latency without storing every expert on every Mac | Count replicas, reserves, staging and initialization; compare with static single owners and include cold misses, phase changes and migration payback. |
| Local CPU execution vs remote expert execution vs weight staging | Adapt compute location to reuse, payload and device service | Exact same logical experts; paired traces, cold/warm loads, realistic queueing and bytes. Reject policies that gain by omitting work or future knowledge. |
| Expert residency policy plus KV/prompt reuse | Optimize both weight capacity and repeated agent context | Joint memory budget; identical prompt/task/quality baseline, end-to-end turn time and cache-preparation costs. A KV optimization may leave expert time unchanged. |
| Slow placement adaptation plus fast replica dispatch | Avoid costly migration while reacting to load fluctuations | Migration budget/hysteresis; compare to static, LRU/frequency and simple estimated-finish-time policies; measure stale/incorrect observations. |
| OS paging vs explicit cache and speculative prefetch | Test whether simpler caching wins on unified memory | Equal total footprint, cache state and workload; useful/wasted reads, compressor pressure, thermals and variance. No universal preference from one project's results. |
| Separate prefill/decode resources with KV transfer | Match compute-heavy prompt work and latency-sensitive decode | Count handoff bytes, duplicate/shared weights, idle resources, TTFT and full-turn tails; may lose at low load or on slow links. |

The first two combinations do not imply JACCL directly interoperates with a Linux
worker. A mixed-tier application protocol/backend bridge is a research question,
not supplied code. No multi-machine correctness or performance was established.
Keep exact-semantic execution and approximation/quality studies in separate
comparisons, even if both ultimately contribute to affordable local AI.

Before advancing a candidate, extract the full paper's objective, assumptions,
pseudocode, workload, precision, baselines, distributions and exclusions; map
those to pinned artifact code. Then propose one distinguishing experiment with a
numerical oracle, resource/traffic conservation, paired workloads, uncertainty
and retained negative results. Pick the smallest comparison that could reverse
our choice. Broad discovery is authorized; blindly combining all mechanisms or
starting new hardware/runtime work is not implied.


## Wedge decision: affordable capacity, with a hard usefulness gate

Date2026-10-18. Human objective: find a defensible open-source advantage for
SPOJ around affordable local inference or long-running bots; run useful research
experiments if needed. This permits this bounded source/policy study under issue
#7. It does not start a replacement runtime, new hardware deployment, issue #2,
checkpoint download, full-model generation, or merge. The earlier local TCP
correctness and outstanding native Mac acceptance remain unchanged.

**Decision: investigate one narrow candidate, not another general inference
server. No independently demonstrated SPOJ application advantage exists yet.**
The proposed user is someone with an existing inference-capable machine and a
spare RAM-rich host who cannot fit the desired model locally at the required
context/precision. The proposed job is: **borrow capacity from that host while
keeping the actual bot task within its latency and reliability budget**. This is
an assumption based on the human's stated motivation, not a completed user study.
An asynchronous question requests actual devices and a blocked/slow bot task.

### What would be the deliverable, if the experiment earns it?

Start with **one existing engine and model family**, not a new inference engine:
a small measured placement/admission component and donor-host expert-execution
integration, plus a replayable capacity/latency report. Use exact selected experts
and explicitly supported precision. Colibri's existing expert-worker path is the
first integration comparator to audit because it already moves activations to
resident CPU experts. An existing engine adapter may be the entire contribution;
an upstream patch is a better outcome than a separate framework without a reason
to exist. Mac/Metal interoperability is a separate backend prerequisite, not
already supplied by this recommendation.

Potential advantage to test: with the **same owned devices**, improve a feasible
placement's end-to-end task service, or enable a useful configuration that the
single primary machine cannot hold. Capacity success has no speedup ratio against
an OOM baseline. Compare absolute service and alternatives, including a smaller
local model that meets the task target. A larger model is worthwhile only if its
measured task quality/utility justifies its extra cost. No novelty or superiority
claim follows from remote experts or cost-aware scheduling alone.

### Candidates we should deprioritize

| Candidate | Competitive evidence | Decision |
| --- | --- | --- |
| Another local bot server / menu-bar app | oMLX, vllm-mlx and Osaurus already describe serving, caching or local-agent features | No standalone wedge established; reuse rather than recreate |
| Generic model swapping / idle eviction | llama-swap and oMLX already document it | Do not build a new project for this feature |
| Persistent/tiered KV cache | oMLX, LMCache, vLLM/MLX ecosystem already cover substantial ground | Only pursue a demonstrated missing invariant or target workload; not generic novelty |
| Distributed MoE / remote experts | Colibri already has expert workers; exo and others distribute models | Necessary mechanisms, not differentiation |
| Generic heterogeneous bandwidth-aware placement | exo#957 and the paper survey already discuss it | Compare as a baseline/upstream opportunity, not an invented research novelty |
| Capacity donor with measured usefulness/admission for one supported mixed setup | User questions and source limits make this plausible, but current projects and beta work may already solve enough | Highest-priority falsifiable candidate; kill it if an existing engine solves the task equally well |
| MoE backend conformance/fault harness | Current SPOJ evidence validates a bounded block/TCP boundary, and upstream reports mention cache identity failures | Useful developer contribution/fallback, not yet a proven consumer product or absence of upstream tests |

Newly inspected primary documentation:
- [jundot/omlx](https://github.com/jundot/omlx/blob/165be1ff5933a020f2f5a7544e1e95a2797f777f/README.md).
- [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap/blob/a2796fb0306215c6883454a8707dfb22d25c3068/README.md).
- [waybarrios/vllm-mlx](https://github.com/waybarrios/vllm-mlx/blob/ab74aa6606a1ac7647f4981320e863edee70823a/README.md).
- [osaurus-ai/osaurus](https://github.com/osaurus-ai/osaurus/blob/1e5bfab23ecf630546a1f82cc882aa3c76473d8d/README.md).
- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/blob/547208dca250ceb3e4c8615598d043f2b602a527/README.md).
- [JustVugg/colibri](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/README.md).

oMLX documents unequal-memory Mac pipeline serving, byte-aware shard planning,
**measured compute/link rebalancing**, and headroom-aware tuning as well as tiered
KV cache, model LRU/TTL and memory enforcement. Thus measured placement alone,
even across unequal-memory Macs, is not an unoccupied wedge. A local
bot-serving layer is also occupied ground. These are README claims, not our
verified compatibility, throughput or reliability results. Osaurus's broad
security/reliability marketing is not adopted as evidence here.

### Concrete need signals, and evidence against our favorite story

Six selected GitHub issue bodies and selected comments were inspected; all
available comments were fetched for context. Source metadata is in
`wedge-sources.json`; user numbers/hardware descriptions were not independently
verified. These show interest or reported pain, **not market size, willingness to
adopt, unresolved feature absence, or proven benchmark results**.

- [exo#1102](https://github.com/exo-explore/exo/issues/1102) asks for Mac/Spark and
  mixed-device use. Importantly, a comment points to **public beta#1776**; later
  comments discuss progress and stability. We must not pitch Mac+NVIDIA as a
  capability nobody has. Validate current beta/version behavior before any claim.
- [exo#957](https://github.com/exo-explore/exo/issues/957) already proposes using
  bandwidth/latency rather than RAM-proportional placement. A discussion models
  stage bottlenecks with CPU STREAM data. That is not GPU inference or measured
  single-request latency; pipeline sum and concurrent-stage maximum are different
  objectives. This is prior work to compare, not novelty to claim.
- [exo#2373](https://github.com/exo-explore/exo/issues/2373) reports daily mixed-Mac
  operation and manual management workarounds. Treat it as one anecdote about
  operational friction; do not repeat its speed/hardware figures as verified facts.
- [MLX-LM#1438](https://github.com/ml-explore/mlx-lm/issues/1438) requests
  expert streaming above RAM capacity. Discussion already explores LRU, locality,
  file-handle reuse, packed reads and failed heat-pinning/prefetch hypotheses.
  Initial I/O-level predictions must be separated from later claimed in-engine
  results and negative results; none were reproduced here. Later discussion also
  reports cache-size peaks (more hits but slower decode), coalescing nulls on an
  already-packed/concurrent engine, and existing streaming PR#1588. These weaken
  generic pinning/prefetch/repacking pitches; inspect current artifacts first.
- [MLX-LM#1194](https://github.com/ml-explore/mlx-lm/issues/1194) reports in-process
  prefix-cache API friction for persistent applications. Existing cache helpers
  and server caches are part of the discussion; a documentation/helper patch may
  solve it more directly than a new cache platform.
- [Colibri#2109](https://github.com/JustVugg/colibri/issues/2109) reports slow cache
  warmup. **Comments already identify prewarming work#2111 on dev** and a separate
  Windows warm-start fix#2131. Open issue status does not establish missing
  implementation. Do not use prewarming as our defensible differentiator.

This source triangulation is stronger than collecting more project names, but
it still does not replace observing the human's real task on their actual setup.

### Executed probe: why an existing homogeneous policy is insufficient evidence

`wedge_probe.py` executes the previously inspected, SHA256-pinned upstream
DeepSeek EPLB function on CPU. It compares four constructed cases against all
feasible assignments of four experts to two devices. Loads are `[100,90,10,1]`;
expert sizes are equal abstract slots; service rates and capacities are **assumed**.
No expert math, model, link, queue, migration, arrival trace or hardware latency
is measured. This is a scope/assumption test, not a new placement algorithm.

The actual upstream output is physical expert order `[0,3,1,2]`, yielding logical
owners `[0,1,1,0]`. With one replica per expert:

| Constructed case | Upstream score | Finite assignment oracle | What this establishes |
| --- | --- | --- | --- |
| Equal rates1/1, two slots each |101 |101 | Policy matches the minimum maximum assigned service for this tiny homogeneous case |
| Rates10/1, two slots each |100 |19 | Load count alone can make a poor assignment under an assumed rate asymmetry |
| Rates1/10, two slots each |101 |19 | Merely swapping assumed rates changes cost but not that load-only mapping |
| Rates10/1, capacities3/1 slots | Mapping violates one-slot bound |19.1 | Equal-count packing cannot express this constructed asymmetric capacity; this is outside upstream's equal-slot contract, not an upstream bug |

Scores are synthetic service-work units; the oracle's objective is maximum
assigned service under this finite independent-work model, not MoE token latency
or global optimality of the paper/system. Six assignments are feasible in each
2/2 case, four in the3/1 case. No quoted ratio is a measured speedup. Current
SPOJ has not implemented or benchmarked a heterogeneous replacement policy.

A source-hash corruption check rejects an unrelated Python file with expected
exit2 **before importing it**. It does not test numerical model faults. Parent
probe exit0 and independent reviewer exit0 outputs match completely; retained
raw JSON and logs are in `related-projects-evidence/wedge-*`.

A second analytical sanity check challenges 'cold experts are harmless': assume
64 experts per layer, uniform top2 selection without replacement, one cold expert
per layer, and32 independent layers. Only1/64=1.5625% of placements are cold, yet

`P(token needs cold tier) = 1 - (C(63,2)/C(64,2))^32 = 0.6379447107`.

That is **63.79% under these assumptions**, not an observed routing statistic.
Real layer/token correlations, learned routing, owner placement and overlap can
change it. Frequency alone cannot prove cold-tier latency is negligible; trace
actual required expert completion barriers and quantify tails before buying RAM
or writing an adaptive router.

### The smallest decision experiment, proposed but not started

Use one real task and one exact model representation on a primary host plus one
existing RAM donor. Do not begin with multiple donors, CXL, RDMA, a new OS or
full agent framework. Transport can remain ordinary TCP for the first comparison.
One supported existing engine is the execution baseline; the present tiny HF/TCP
experiment remains its own correctness evidence, not a deployable model server.

1. **Establish task adequacy and the capacity problem.** Freeze task success,
   model/precision/context, hardware, memory reserves and user latency budget.
   Compare a smaller fully local model that actually completes the task. Inventory
   owned resources; no hardware price/savings claim without costs and power data.
2. **Measure simple alternatives before a new policy.** Same model/workload where
   feasible: local resident; local offload/streaming; existing remote expert engine
   with static ownership; a simple measured placement; only then proposed adaptive
   placement/replica dispatch. Equal initialization, cache state and memory budget.
   'Local resident' may be infeasible; report that rather than invent a ratio.
3. **Check the complete resource path.** No hidden full-model copy on coordinator;
   direct shard loading, per-tier peak including initialization/staging/replicas,
   non-expert/KV/workspace/OS reserves, bytes transferred and cold-expert requests.
   Mac unified memory counts once. Use actual selected expert IDs and independently
   check contributions/output at the applicable precision/backend contract.
4. **Replay a persistent-bot-shaped workload.** Include cold start, extending turns,
   repeated tool prefixes, changed/forked prefixes, pauses/resume, context growth,
   bounded concurrent requests and donor disconnect. Measure full-turn completion,
   TTFT/inter-token tails, task/tool-call success, queueing, CPU/GPU/IO service,
   useful/wasted transfers and recoverable failure. HTTP health is not generation
   health. A prompt cache is not the bot's durable application/tool state.
5. **Predeclare the pass and kill criteria.** Proposed engineering gate, subject
   to workload qualification before execution: either useful new capacity within
   the user's SLO, or at least20% lower p95 full-turn time versus the strongest
   feasible same-hardware baseline, with a paired-run confidence interval excluding
   no improvement, no task-quality regression and a declared throughput/energy
   budget. Choose enough independent sessions and repeated cold/warm runs to
   estimate tails; never report a reliable p95 from a handful of requests. Record
   costs, failures and negative results. This threshold is a proposed decision
   rule, not an achieved result or the human's already-approved SLO.

**Kill/pivot:** if current Colibri/exo/oMLX already meets the real task equally
well, use or improve it upstream. If the donor causes unacceptable tails, do not
force distribution; compare a smaller local model or local streaming. If gains
exist only under oracle future demand, uncharged staging/replication, different
precision, dropped experts or a weak baseline, reject the apparent advantage.
If a small upstream patch solves the pain, ship that patch rather than a new
SPOJ runtime. A no-win result is a successful decision experiment.

### Reproduce this bounded probe and current stopping point

From the repository root at this research revision, frozen project environment:

```sh
uv sync --frozen --project spoi
gh api -H 'Accept: application/vnd.github.raw+json' 'repos/deepseek-ai/EPLB/contents/eplb.py?ref=d52c72d5b2f2fb4c41afbf8eb21366820239913d' > /tmp/spoj-eplb.py
spoi/.venv/bin/python research/heterorouter/wedge_probe.py --eplb-source /tmp/spoj-eplb.py > /tmp/spoj-wedge-results.json
```

Compare parsed JSON to `related-projects-evidence/wedge-probe-results.json`;
environment versions may differ on another platform, but source output, cases,
arithmetic and limits should match. This run used Python3.12.14 and
PyTorch2.14.1+cu130 on Linux CPU policy tensors. Torch's base version matches
`spoi/uv.lock`; no dependency, numerical tolerance or compatibility guard changed.
The existing environment was reused; `uv sync` above is a reproduction instruction,
not a newly executed setup check. Product tests were not rerun for this isolated
research probe. No native Mac or multi-machine outcome is implied.

**Physical/application validation is blocked on a specified real workload,
available target devices and model artifact access under the existing
no-checkpoint-download constraint.** No such advantage can be established from
this worker's source inspection or synthetic probe. What is complete here is a
ranked, falsifiable candidate and an evidence-backed rejection of several broad
pitches; what remains unproven is a real deployment win or reason to maintain a
standalone SPOJ product. Keep that distinction in the goal handoff.


## Limits ledger: learned control and KV-resident attention

Date2026-10-18. Human direction: explore mechanisms beyond spare-RAM donation,
including TypeSafe's Jev/System One models, online/reinforcement learning, cheap
hardware and sharing/offloading KV. These are research paths, not chosen product
requirements. The user clarified Jev with
https://typesafe.ai/blog/introducing-system-one-models-and-jev; it is **not JEPA**.

There is no evidence that these ingredients or all their combinations have never
been tried. Most have substantial prior art. The opportunity would be a specific
measured improvement or useful supported configuration, not an unverified claim
of a new category. Earlier capacity-donor qualification remains conditional.

### Jev-style decisions and online learning solve different problems

The supplied blog returned HTTP403 (curl exit22). Official TypeSafe GitHub SDK,
adapter and documentation were inspected instead; `limits-sources.json` records
pins/hashes. Their System One interface accepts application state and typed
questions: Choice, Noul and Score return structured judgments/probabilities.
The documentation describes Jev as a focused typed-judgment model. We did not
validate its latency, calibration, local weights, hardware needs or model
licensing. Open-source SDK/adapter code is not evidence of open local Jev weights.
No TypeSafe service, key or hosted-model call was used.

A plausible role is **semantic outer-loop control**: distinguish an interactive
tool turn from background indexing, infer which task phase has begun, prioritize
sessions, or suggest which already-feasible execution mode to consider. Known
bytes, measured service, hard deadlines and memory arithmetic belong in code.
A typed answer is not proof of a correct performance prediction. The adapter can
compare other LLM APIs and documents probability normalization; summing to one
is not empirical calibration. Measure error, calibration and actual controller
cost on the target workload rather than borrowing vendor claims.

This is different from **learning from outcomes**. A fixed decision model does
not automatically update its policy when a transfer or expert call is slow.
Online regression/system identification, contextual bandits, model-predictive
control and RL offer different adaptation mechanisms:

| Controller | Useful role | Main evidence/failure question |
| --- | --- | --- |
| Rules + measured cost/queue estimates | Transparent baseline and conservative fallback | Does a more complex policy beat it after paying its own overhead? |
| Online regression + constrained short-horizon planning | Update service/transfer predictions and plan staging/placement | Validate uncertainty, nonstationarity, overlap and prediction error against actual completion time. |
| Contextual bandit | Learn among a few feasible execution modes when feedback is sufficiently immediate | Exploration costs real user latency; delayed effects and unchosen-action outcomes require care. |
| RL with resource/cache state | Plan actions whose residency/queue effects have delayed rewards | Requires representative transition/reward data; simulator exploitation, drift and migration cost can erase gains. |
| Jev-style semantic features plus any controller above | Add task meaning that numeric telemetry misses | Ablate semantic features, include model memory/API/latency cost, and test whether they add value over measured telemetry alone. |

Possible actions: select an identical replica, execute at a resident owner, stage
weights to faster compute, adjust bounded batching, or change a slower residency
plan. The learned MoE gate still chooses logical expert IDs. Invalid memory,
backend/precision, ownership, dependency or deadline actions must be filtered by
code; a policy cannot silently replace experts or omit required calls. Low
confidence or stale measurements need a defined baseline fallback.

Train/replay with past-only observations; do not fit/evaluate on future demand.
A trace from one policy may not identify the outcomes of actions it never took,
especially with queue/cache interference. Compare actual action outcomes or a
separately calibrated model; label counterfactual assumptions. Start with a
small action set and measured baselines before a neural RL agent. A controller
wins only if saved critical-path work exceeds its inference, profiling,
exploration, memory and data-movement costs. This is a proposal, not deployed
learning code or proof that RL beats simple heuristics.

### Three different meanings of remote/shared KV

1. **Reuse an identical prefix across requests or bots.** A local/shared cache
   can avoid recomputing that prefix. Identical model/weights/adapters, actual
   token prefix, positions/positional encoding, mask/state, precision and cache
   representation matter; similar meaning is not cache identity. Diverging
   branches need independent suffix state/copy-on-write. Hybrid recurrent models
   can need state beyond K/V. These are cache compatibility constraints, not
   permission to share arbitrary prompts or models.
2. **Store inactive or precomputed state remotely, then restore it.** Transfer
   occurs on cache restoration or prefill/decode handoff, not necessarily every
   generated token. A very fast link is not always required: savings must exceed
   transfer/rebuild cost, and idle time or repeated reuse may help amortize it.
3. **Keep live KV on another host during every decode step.** Fetching all dense
   KV back for each token can be prohibitive. Another design computes attention
   beside KV and returns sufficient partial results. That saves wire bytes but
   leaves attention work/memory reads at those owners and adds layer dependencies.

Ordinary remote memory, RDMA and CXL do not automatically provide correct cache
identity, cache coherence, model semantics or inexpensive attention computation.
A memory donor may also need to be an attention executor; otherwise its link can
become the decode bandwidth bottleneck.

Explanatory design only; no sockets or remote process were exercised below:

```text
coordinator / current layer queries
          |                    |
          v                    v
   KV-context shard A    KV-context shard B
   compute m,z,u         compute m,z,u
          |                    |
          +---- stable merge --+
                    |
            attention output
                    |
          next layer dependency
```

Append the new token's K/V at the correct context owner; query fan-out, versions,
mask/position identity and bounded completion/failure are additional protocol
obligations. The diagram omits those implementation details and proves no
cross-machine correctness.

### Executed tensor check: compact attention reduction

`attention_limits_probe.py` generates CPU float32 Q/K/V tensors and compares a
partitioned calculation with **direct PyTorch scaled_dot_product_attention**.
For each shard i, it computes row maximum m_i, exponential sum z_i, and
unnormalized value numerator u_i. With M=max_i(m_i):

`attention = sum_i(exp(m_i-M)*u_i) / sum_i(exp(m_i-M)*z_i)`.

All-masked/empty shards contribute zero; an all-masked query returns zero under
the tested PyTorch convention. Averaging separately normalized shard outputs is
incorrect. KV-position coverage, query/key-head mapping and masks are part of
the computation contract. This is standard softmax-reduction algebra; it is not
a claimed new method or a reproduction of a named distributed paper.

Observed: **13 positive cases**, max absolute error **4.76837158203125e-7**,
rtol1e-5/atol1e-6. Cases include four seeded grouped-query tensors (2KV/4query
heads), causal masks, all-masked rows, contiguous/interleaved/unequal/empty shards
and extreme logits. Both injected faults were rejected: naive shard-output
averaging (maxerror0.5) and ignoring a required mask (maxerror1.0). Parent and
independent reviewer runs exit0 with identical full JSON. A bounded actual tensor
trace records one query, allowed positions, shards, local statistics and direct/
merged outputs; JSON null for a shard maximum means minus infinity/no allowed
keys, explicitly labeled. This is **local numerical evidence only**; no codec,
transfer, remote state, backend interoperability or performance is tested.

### Byte and latency bounds: a declared thought experiment

Assume32 attention layers,8KV heads,32query heads, head dimension128,32768 cached
tokens, FP16K/V and queries, and two context shards returning FP32partial
numerators and max/sum statistics. One query token, no KV replication, dense
attention and ordinary per-layer dependencies:

| Derived quantity | Value / condition |
| --- | --- |
| Full KV footprint `2*L*Hkv*D*T*2bytes` |4,294,967,296bytes =4GiB |
| Pull full KV at assumed effective1GB/s each decode step |4.294967296seconds for bytes alone; headers/compute/contention excluded |
| Broadcast query bytes to two shards |524,288bytes per decode step across all layers |
| Return FP32partial numerator bytes |1,048,576bytes |
| Return FP32max/sum statistics |16,384bytes |
| Append one token's FP16K/V to owners |131,072bytes |
| Total modeled wire bytes |1,720,320bytes ≈1.64MiB per decode step; no framing, replication, retries or auxiliary metadata |
|32sequential layer RPCs at assumed0.5ms RTT |16ms propagation/round-trip component alone if both shard calls per layer run in parallel |

The tensor experiment was float32; it **does not validate these hypothetical
FP16wire/cache formats**. These are arithmetic bounds, not measured traffic,
latency or speedup. Attention owners still scan/process their portions of dense
KV; memory bandwidth, CPU/GPU kernels, dtype conversion, queues, synchronization
and repeated layers may dominate. Parallel shard calls cost the required
completion barrier, not the sum of unrelated peer RTTs. More devices cannot
remove serial model dependencies. Combining remote attention and remote MoE
experts may introduce two sequential remote boundaries per layer; the32RPC
example covers attention only, not complete model execution. Exact dense
attention need not send its entire
KV across the network, but its work and data access still have to occur somewhere.

### Other paths worth discriminating, with their actual trade-offs

| Path to investigate | Why it could help | What can defeat it / first discriminating evidence |
| --- | --- | --- |
| Cheap RAM+compute host owns long-context KV; fast device owns other compute | Replace repeated bulk KV movement with query/partial exchanges | Owner memory/compute service and layer RTT; compare actual complete attention with local/offloaded baseline at the same numerical contract. |
| Shared-prefix directory and inactive-session KV tier | Many long-running bots reuse system/tool prefixes or pause | Identity/invalidation, changed templates, recurrent state and restore cost; measure task-shaped prefix hits and resume tails, not only stored bytes. |
| Joint expert+KV residency planning | Separate optimizers can steal each other's RAM/page-cache budget | Stage/replica peaks, correlated demand, transfer contention; compare one joint budget against strong simple separate policies. |
| Task-aware mixture of small local models and a larger streamed/distributed model | Avoid paying the largest model cost for every routine bot decision | Changes model/task-quality semantics; test routing errors, tool success, escalation and quality against a single-model baseline. |
| Draft locally, verify blocks on a larger model | Potentially amortize target execution and links across accepted tokens | Correct speculative verification can preserve the target sampling distribution, not identical RNG outputs; low acceptance, extra expert I/O and KV synchronization may lose. |
| Select architectures with GQA/MLA or recurrent/hybrid state | Reduce KV or per-token state demand at the model-design level | Different model/quality/training contract; compare task utility and support rather than claim same-model execution speedup. |
| APU/unified memory, more memory channels, striped NVMe or PIM near memory | Change the real memory hierarchy instead of tuning one scheduler | Shared bandwidth, actual kernels, IO concurrency, power and cost; use hardware only after profiling predicts a discriminating win. No purchase/availability claim. |
| Typed task-phase judgment + bounded online controller | Adapt to foreground/background phases, load and observations | Semantic feature may add nothing; benchmark controller overhead and use held-out changing workloads, safe action set and simple baselines. |
| Use tool-wait/idle intervals for bounded state or weight movement | Persistent bots often wait between model calls, allowing preparation away from an active decode path | Only known state and past-only predictions; unknown tool results cannot be prefetched as facts. Charge wrong transfers, cache interference, cancellation and contention with active sessions. |

### Primary reading leads added in this pass

Eleven primary READMEs plus the official TypeSafe API-documentation file were
inspected and hashed; **full research papers were not read in this extension**.
No listed project was installed or run. Author claims remain source claims.
- [typesafe-ai/typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python/blob/f36e68549ceca3191e5791e5f99ea1baa1a258b5/README.md): Official typed-choice API example; no local model/performance proof.
- [typesafe-ai/system-one-adapter-python](https://github.com/typesafe-ai/system-one-adapter-python/blob/e1d4cc938204b22fc5a3c3aca7044072fe3f712d/README.md): Comparison adapter for LLM APIs; native-looking interface/probability normalization does not give JEV architecture, speed or calibration.
- [typesafe-ai/skills](https://github.com/typesafe-ai/skills/blob/65a39f393687675ce170e6094757de20370365b9/README.md): Author description of System One/Jev, Choice/Noul/Score and confidence semantics; read as research documentation, not installed/invoked.
- [typesafe-ai/typesafe-public-examples](https://github.com/typesafe-ai/typesafe-public-examples/blob/25e9d373f4853b3e7e300e55a194f50e54838f68/README.md): Official examples repository identity; its short root README establishes no performance result.
- [hongzimao/decima-sim](https://github.com/hongzimao/decima-sim/blob/c010dd74ff4b7566bd0ac989c90a32cfbc630d84/README.md): Decima SIGCOMM19 simulator: reinforcement-learned cluster scheduling; not LLM inference, local hardware validation or ready-trained SPOJ controller.
- [Thesys-lab/Helix-ASPLOS25](https://github.com/Thesys-lab/Helix-ASPLOS25/blob/8639497a4aaf1eb3b7594614cb0bbd376c1342b3/readme.md): Helix paper arXiv2406.01566: heterogeneous GPU/network placement and max-flow scheduling, simulator plus prototype; solver/runtime assumptions do not prove local Mac applicability.
- [alibaba/llm-scheduling-artifact](https://github.com/alibaba/llm-scheduling-artifact/blob/a90824307249573f9c7548645c22994c65f83a08/README.md): Llumnix OSDI24: serving scheduling/migration artifact; example cluster4x4A10, not an affordable-local result.
- [Selimonder/ring-attention](https://github.com/Selimonder/ring-attention/blob/b83631d5a33552d745bfa04e4b05055d4a43e34f/README.md): Ring Attention arXiv2310.01889 and BPT2305.19370: blockwise/distributed context mechanisms; long-context training overlap claims are not batch-one remote-decode results.
- [snu-comparch/InfiniGen](https://github.com/snu-comparch/InfiniGen/blob/3754f52d131c30ab7a310e3c4cf356e8e3326ac3/README.md): InfiniGen OSDI24/arXiv2406.19707: predicts selected KV fetches; selective attention/state handling requires model-quality/semantic evaluation.
- [mit-han-lab/duo-attention](https://github.com/mit-han-lab/duo-attention/blob/fe93c314ae87306ef6629dc16713250b4718ffe7/README.md): DuoAttention ICLR25/arXiv2410.10819: retrieval versus streaming heads and reduced cache; approximate/model-adapted lane, not strict full-attention parity.
- [ByteDance-Seed/ShadowKV](https://github.com/ByteDance-Seed/ShadowKV/blob/e51904cdeab7d4d34013370f09f2cf5fcd655e15/README.md): ShadowKV ICML25/arXiv2410.21465: KV-management research artifact with CUDA/A100-oriented setup; no Metal or exact full-attention guarantee inferred from README.

Mooncake, LMCache, DistServe, EPLB, Colibri, oMLX and earlier hardware sources
remain relevant; do not reopen the false premise that KV pooling, learned
scheduling or measured placement is unoccupied ground.

The physical limit ledger is: capacity by tier and initialization peak; bytes
that must move on each path; memory traffic and compute where executed; model
critical-path dependencies; and task-quality/error budgets. Plot a Pareto frontier
of task success, p95turn time, usable context/model capacity, watts and cost.
A faster OS, language, controller or link helps only the part of that critical
path it actually changes. No universal absolute maximum follows from one model,
one cache trace, peak bandwidth or this algebra probe.

**Recommended research comparison:** retain the capacity-donor candidate, but
add KV-owner attention as a distinct testable path; compare simple measured
control with an online controller, then ablate whether semantic/Jev-style task
features help. Require actual device/runtime profiles before physical claims.
These are candidates for a new approved experiment, not changes to the main
three-worker TCP milestone or issue#2. No checks, tolerances, guards or native
Mac acceptance were bypassed; no checkpoints, machines, paid APIs, RL training,
full-model generation or infrastructure purchase occurred.

Reproduce the local algebra probe using the existing frozen environment from
repository root:

```sh
uv sync --frozen --project spoi
spoi/.venv/bin/python research/heterorouter/attention_limits_probe.py > /tmp/spoj-attention-limits.json
```

Only the second command ran in this study; the environment was already present.
It used Python3.12.14/PyTorch2.14.1+cu130 on CPU. Compare parsed JSON with
`related-projects-evidence/attention-limits-results.json`; environment fields
may differ elsewhere. Retained evidence explicitly separates observed tensors,
negative tests, derived bytes and untested physical/backend boundaries.
