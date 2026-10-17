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
