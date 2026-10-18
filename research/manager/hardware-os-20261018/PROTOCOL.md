# Hardware, transfer granularity and OS: frozen research protocol

Issue #9; run hardware-os-20261018-1801. Started 2026-10-18T18:01:51Z,
deadline 18:31:51Z. User requests hardware/software/optical-network/OS designs
and experiments, offering future hardware access. Actual inventory/model/task
not yet supplied. Hypotheses H1 placement versus link upgrades; H2 removable
OS/control cost. D1/D2 and D7 prior accepted packets are not rerun.

Manager /root authors arithmetic/design only. Source researcher
/root/hardware_sources; transport experimenter /root/hardware_transport;
independent validator assigned after frozen evidence. Model/provider run IDs
unavailable. At most 3 children, no grandchildren; each experiment <=300s,
2GiB address space,100MiB generated/downloaded artifacts. No purchase/model
download/new server/host OS change or product acceptance waiver.

## H1: moving computation can beat moving weights

Consider one autoregressive token, sequential 32-layer conditional MoE path,
hidden width4096, intermediate14336, top-k2, three matrices/expert at assumed
0.5 byte/weight (ideal packed4bit without scales). Full dense FP16 activation
vector4096*2 bytes. Per cold layer selected weights=176,160,768 bytes (168MiB),
request+result activation bytes=16,384. Exactly M entire selected-expert groups
are cold on the GPU, M in {0,1,4,16,32}; their weights already exist in donor RAM.
This is explicit arithmetic, not a model artifact, real router distribution,
measured kernel, physical benchmark or inference correctness result.

Non-expert dense/attention work remains on the GPU at an assumed0.1ms/layer.
GPU selected-expert service g in {0.05,0.2,1}ms; CPU donor selected-expert service
c in {0.5,2,10}ms. Services are assumptions inclusive of local memory/compute
cost, not vendor FLOPS estimates. GPU PCIe payload bandwidth is assumed24GB/s.
Link line rates {1,2.5,10,25,100,400} decimalGb/s at assumed80% payload efficiency,
divided equally among {1,4} active flows. Payload serialization uses bytes, not
bits; full-duplex request/response cannot overlap causally for one token. RTT
{0.02,0.2,1}ms includes propagation/NIC/stack but excludes explicit payload
serialization and compute. No compression, future-prefetch oracle, shared-link
overlap win, or uncharged initial model load. Warm GPU cache and donor residency
are common between expert alternatives. Link/compute rates are not measurements.

Matched expert alternatives, all preserve logical target experts/weights:

- Full GPU residency: lower reference L*(dense+g), **capacity unverified**, not
  always feasible when offload is needed. No offload may claim to beat this
  reference merely because its model fits whereas GPU-only does not.
- Weight staging: fetch all selected cold weights once per cold layer via one
  RPC, then execute on GPU. An optimistic chunk/pipeline lower bound per cold
  layer is RTT+max(g,W/network,W/PCIe); serial upper model is
  RTT+g+W/network+W/PCIe. Non-cold layers pay g. Scales, packing, host copies and
  controller overhead are excluded: this deliberately favors weight staging.
- Execute near weights: one fused request/result per cold layer at the same
  donor. Lower model RTT+max(c,A/network,A/PCIe); serialized model
  RTT+c+A/network+A/PCIe. CPU compute and return dependencies make the serialized
  model the conservative comparison; no k separate RPCs when fusion is possible.

Use intervals rather than silently assuming optimal overlap. Screening criterion:
one alternative's serial model <=80% of the other's optimistic lower bound.
This establishes a **robust conditional result within assumed costs**, not
superiority over deployed upstream systems. If intervals overlap, say unresolved.
Baseline strongest practical implementations remain existing engines (Colibri/
CPU-expert engines and their pipelined load paths); no engine is benchmarked here.

Coarse contiguous layer partition is a separately labeled design comparison:
M entire layers on donor, one contiguous middle block (two model boundaries),
extra CPU dense/attention service assumed0.5ms per remote layer and same c.
M=0 has no boundary; M=L models remotely resident whole model with one input/output
RPC. This sends smaller vectors fewer times, but moves extra compute, KV and
whole-layer weights to the donor. Capacity/placement feasibility and numerical
compatibility are **unverified**. It is not a matched expert-placement winner.
Network A bytes per boundary means two vectors per round trip; a contiguous
middle block has one outward vector and one return vector, modeled as one RTT
and A bytes overall (not two full round trips). Endpoint input and output remain
at the GPU host. Routing/cache/stage changes across tokens are not modeled.

Cost grid:5 miss counts*3GPU services*3CPU services*6line rates*2flow counts*
3RTTs=1,620 deterministic cases. Save all rows, exact inputs/hash, summary and
dominance checks. Controls: zero misses==GPU reference; zero traffic if no misses;
bits/bytes and MiB/GB conversion; faster link monotonic; larger RTT cannot help;
more contending flows cannot help; staging serial>=lower, near serial>=lower;
payload checks; invalid inputs reject. Cold-layer sequence/tail behavior unknown.

## H2: is a fresh OS worth investigating?

Do not treat all transfer/compute time as OS overhead. Amdahl screening considers
assumed truly removable critical-path fraction f in {0,.01,.05,.1,.2,.5} and
removal fraction r in {.5,.9,1}: new/old latency=1-f*r; speedup=1/(1-f*r).
At least20% latency reduction requires f*r>=.2. Perfect removal of5% yields
only5% lower latency, not20%. These fractions are scenarios, not profiling data.

A separate measured local experiment compares persistent TCP loopback with Unix
domain streams using identical C two-process verified echo, matched payloads,
AB/BA process-pair order and bounded traffic. The experimenter's separately
committed transport/PROTOCOL.md defines exact iterations before timed runs.
Success requires correct replies and rejected intentional corruption; there is
no prescribed performance winner. Localhost elapsed time contains scheduler,
syscalls, copies, verification and virtual CPU effects. It is **not** physical
NIC throughput, isolated kernel cost, or a GPU/RDMA/new-OS benchmark. Never plug
its RTT into the architecture grid as a measured physical link.

Fresh OS work remains a proposed design, not a selected implementation. Require
a real token/task critical-path trace to attribute >=20% removable time after
qualified batching/fusion/NUMA/preallocation/driver/I/O/runtime baselines. A new
kernel cannot remove required bytes, arithmetic or physical latency. Propose
small userspace/runtime intervention first; hardware/driver/isolation support
must survive any alternative OS. Agent-task latency, inference-token latency,
tool wait and multi-session throughput are distinct objective functions.

## Evidence and independent acceptance

Manager arithmetic uses Python3.12 stdlib only. Transport uses available C
compiler; inspect source before running, strict warnings, bounded IO/cleanup.
Record failures/raw timings/environment; do not remove slow observations or
infer reliable p99 from five sessions. Separate reviewer verifies hashes,
reruns arithmetic and at least smallest transport correctness/corruption test,
challenges baseline comparisons and independently recomputes a representative
cell. Real hardware/model correctness and useful performance stay UNRESOLVED.
Attempt required product check offline under bounded time; missing dependencies
remain a disclosed gate. No repeated accepted D1/D2 startup grids.
