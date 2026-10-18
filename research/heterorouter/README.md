# Separate SPOJ algorithm exploration — initial source and simulation notes

Date: 2026-10-17. Research-only; no changes to the correctness implementation and no main-correctness acceptance claim. Published separately under `research/heterorouter/`. Tracking issue: https://github.com/karlem/spoj/issues/7.

## Capacity goal and Colibri comparison

Start with the [wedge decision and executed assumption probe](related-projects-and-papers.md#wedge-decision-affordable-capacity-with-a-hard-usefulness-gate): one capacity-donor candidate, direct competitor/user-need evidence, explicit kill criteria, and no claimed deployment advantage. Physical validation needs a real task and target devices.

The consolidated [software and Mac research atlas](related-projects-and-papers.md#software-research-atlas-and-apple--heterogeneous-execution-paths) maps MLX/JACCL/TB5, expert replication, offloading, KV reuse, phase scheduling and mixed-tier hypotheses. See its evidence levels and [paper reading queue](software-paper-backlog.json); no new runtime or hardware experiment was started.

The consolidated [hardware-memory research section](related-projects-and-papers.md#memory-hardware-far-memory-and-near-memory-computation) adds CXL, RDMA far memory and PIM papers/artifacts, distinguishes physical hardware from simulation, and proposes a no-purchase lab ladder. No hardware, model or benchmark was run.

The same [project/paper survey](related-projects-and-papers.md#affordable-local-ai-as-a-foundation-for-an-ai-os) now includes Prima.cpp, PowerInfer/PowerInfer-2, FlexGen, AIOS and IX, and a proposed method to distinguish network, memory and OS/control overhead for an affordable local-assistant goal. These are source-grounded reading leads and hypotheses, not measured platform results.

For additional systems and verified paper citations, read the [ranked primary-source project/paper survey](related-projects-and-papers.md). It separates CPU/GPU expert execution, cross-device layer/tensor partitioning, caching and transport. Nine pinned repositories were inspected; no project was installed/run and full paper texts were not read in that survey.

The human clarified that capacity comes first: combine heterogeneous device memory to host a model that cannot fit one device, then improve service through measured scheduling and placement adaptation. Read [the primary-code Colibri study and capacity accounting](capacity-and-colibri.md). This is research direction only; it changes no approved product scope or implementation. Colibri was inspected, not executed.

## Current source pointer: arXiv:2608.00577

The user supplied the primary PDF for https://arxiv.org/abs/2608.00577; it has now been read. Start with [primary-source analysis, algorithms and explicit ambiguities](primary-analysis.md). Its title is **HetRoute: Heterogeneous and Cost-aware Collaborative Routing Framework for Distributed Edge MoE Inference**. A separate bounded online sketch explores joint routing with assumed perceived bandwidth; it is not a complete reproduction. The generic simulation below remains a separate pre-paper baseline. [Earlier blocked-access notes](source-update-2608.00577.md) are retained as history.

## Read and reproduce the current sketch

- [Primary source, algorithms, equations and ambiguities](primary-analysis.md).
- [Observed synthetic decision and annotated code map](online-walkthrough.md).
- [Inputs and bounded output trace](online-results.json); [narrow-beam counterexample](beam-counterexample.json).
- [Independent source review](independent-primary-review.md) and [independent executable review](evidence-34c4bad/independent-code-review.md).
- [Evaluated commit and commands](evidence-34c4bad/validation.json). Python 3.12 stdlib; no model/network required. Both implementer and independent reviewer ran all 12 tests and matched complete JSON.

The source below describes the earlier generic bootstrap. It is retained separately and has not become a HetRoute reproduction.

## Initial discovery before the user supplied the citation (audit trail)

**At the initial bootstrap, no verified HeteroRouter primary paper or implementation had been identified.** Do not label the attached generic scheduler as HeteroRouter, reproduce invented equations, or infer a paper's claims from the user's pronunciation. The user subsequently supplied arXiv:2608.00577; the later attachment now supports the primary-source analysis linked above.

Observed public searches on this date:

- GitHub repository search `HeteroRouter`: 0 results.
- GitHub repository search `"HeteroRouter" in:readme`: 0 results.
- `HeteroRoute` name/README searches: 0 results.
- `"hetero-router" in:readme`: 3 results, none identified as the requested MoE paper.
- arxiv.org, export.arxiv.org, api.openalex.org, api.semanticscholar.org and Google requests: proxy rejected with HTTP 403. This is a source-access limitation, not evidence the paper does not exist. Ordinary sandbox network access first returned Operation not permitted; public GitHub API worked with escalation.

Exact queries can be repeated through `https://api.github.com/search/repositories?q=HeteroRouter` and equivalent URL-encoded queries. Search results are discovery evidence, not exhaustive bibliographic evidence.

## Verified related leads, not substitutes

1. **HexGen: Generative Inference of Large Language Model over Heterogeneous Environment**, ICML 2024, as identified by its official README: https://github.com/Relaxed-System-Lab/HexGen ; paper linked there: https://arxiv.org/abs/2311.11514. README describes hybrid pipeline/tensor parallelism and asymmetric parallel groups. Relevant question: how heterogeneous compute and links enter placement/partition decisions. It is not established here as an MoE token-routing algorithm. Full paper text/equations have not been retrieved; do not claim their objective or specific algorithm from README alone.
2. **DeepEP**, official communication implementation: https://github.com/deepseek-ai/DeepEP. README exposes dispatch/combine interfaces using selected expert IDs/weights and separates communication from expert math. Useful systems comparator, not the requested HeteroRouter paper. Its current documented environment requires modern NVIDIA GPUs/NVLink/RDMA; no installation or execution attempted. README performance claims are not SPOJ evidence.

Original extraction plan (now addressed for the supplied PDF; no author code acquired): inspect its exact version and corresponding code revision; extract objective, constraints, observation model, pseudocode and equations with section/page references, plus claims actually supported by its evaluation. Determine whether its "router" changes logical expert selection or only placement/replica dispatch. That distinction determines whether it can preserve the frozen HF oracle at all.

## Generic simulation bootstrap — explicitly our proposal

Files: `simulate.py`, `simulation-results.json`. Reproduce with Python 3 stdlib: `python simulate.py`. Exit 0 runs deterministic sanity assertions and emits JSON. No sockets, workers, devices, model weights, benchmarks, or measured network samples are involved.

The model keeps a fixed sequence of 120 expert jobs, seed 731. Each job has a semantic expert ID and row count; the scheduler may choose only a device holding an **identical hypothetical replica** of that expert. Placement/replication is assumed, not implemented; its memory and initialization costs are excluded. With the actual correctness demonstration's disjoint single-owner shards there is no replica-dispatch choice: only batching, queuing or a separately authorized placement problem remains. Do not silently introduce replication into the implementation.

There are three heterogeneous virtual devices and a dedicated full-duplex link per device. All values are assumed:

| Device | True simulated bytes/s | True simulated RTT | Compute seconds/row | Perceived network |
| --- | ---: | ---: | ---: | --- |
| 0 | 12,500,000 | .002 | .001 | matches assumed truth |
| 1 | 1,250,000 | .030 | .0003 | stale: 12,500,000 bytes/s, .002 RTT |
| 2 | 6,250,000 | .010 | .002 | matches assumed truth |

Perceived compute matches simulated truth. "True" means simulator ground truth, **not a measurement**. Input and output bytes are each assumed `64 + rows * 64 * 4`: one header plus hidden=64 float32 rows. Real SPOJ frame metadata, indices, batching, tensor payloads and initialization costs must later be derived from its codec/trace instead.

Each device has FIFO outbound serialization, compute, and return serialization calendars. A packet occupies its link for `bytes / bandwidth`; propagation is RTT/2 each direction. Compute starts after complete receipt and device availability. Predicted earliest finish (EFT) uses separate calendars and perceived parameters; actual latency uses true simulated parameters. The algorithm greedily chooses the eligible device with lowest predicted completion time, breaking ties by device ID. This is a generic heuristic with no HeteroRouter attribution and no global-optimality guarantee.

Baselines: fixed first eligible replica, deterministic per-expert rotation among eligible replicas, perceived EFT, and greedy EFT supplied true parameters. The last is a parameter-knowledge comparator, **not an optimal scheduling oracle**. All get identical arrivals, expert IDs, payloads and replica eligibility. Every latency below is for an individual expert-batch job, not an end-to-end token or complete MoE request; the top-k completion barrier is not represented.

## Executed virtual result

`python simulate.py > simulation-results.json` exited 0; dimensional arithmetic, bandwidth monotonicity for one job, same-device queuing and repeatability assertions passed. Every policy completed all 120 jobs with eligible owners.

| Policy | Mean latency, ms | p95 latency, ms | Makespan, s |
| --- | ---: | ---: | ---: |
| First eligible | 105.266 | 258.748 | 1.210748 |
| Per-expert rotation among eligible | 55.633 | 162.642 | 1.163372 |
| Perceived EFT | 36.265 | 54.410 | .984941 |
| EFT with true parameters | 32.798 | 53.331 | .969456 |

These are outputs of one constructed scenario, not measured improvements or a general policy ranking. The stale estimator sent 78/120 jobs to device 1; true-parameter EFT sent 31. That is an observable consequence of perception error in this model. A more realistic simulator may reverse a ranking.

## Boundaries and next research steps

The bootstrap excludes shared-uplink contention, finite buffers, admission/backpressure, RTT jitter, loss/retransmission, batch-level top-k barriers, request deadlines, online measurement updates, migrations, failures, resource limits and initialization traffic. It is a deterministic queue/calendar model of fixed jobs, not a production simulator or a numerical parity proof.

After primary-text inspection: choose a paper-faithful minimal algorithm, document every adaptation separately, and implement one agreed comparison. Then model shared resources and bounded queues explicitly (admit/block/reject; no disappearing work), retain per-event conservation assertions, and use batch completion as the maximum required expert response. Compare identical realized workloads under paired seeds; sweep offered load, bandwidth/RTT asymmetry, estimation staleness/error, payload sizes and skew. Report uncertainty and failed/uncompleted/deadline-missed work alongside latency so dropping work cannot improve apparent scores.

For eventual perceived measurements, specify what the observer could know at each decision: timestamped bytes transferred and elapsed duration for throughput; transport/application round-trip samples; device service-time samples separate from queue wait; observation age and estimator update rule. Trace replay must use past observations only. Assume-vs-measured provenance belongs in the input schema, with units, source host/run, timestamp, uncertainty and calibration command. No new host or benchmark is authorized by these notes.

Independent correctness evidence would include hand-solvable event schedules, conservation/eligibility assertions, zero-choice equivalence, queue saturation/deadline tests, paired reproducible inputs and algorithm checks against paper pseudocode. None would establish physical throughput, speedup, cross-machine numerical parity, or native Mac acceptance.

## Independent bootstrap rerun

The parent agent separately executed `python3 simulate.py` and compared the complete JSON with the researcher output: exit 0, exact match, all four policies conserved 120 eligible jobs. This checks deterministic mechanics only; it does not validate a HeteroRouter algorithm or physical predictions.

This workstream is distinct from correctness PR #6. To continue it in a separate ChatGPT conversation, reference GitHub issue #7 and this research branch. The identifier and primary attachment are now supplied. Continue from primary-analysis.md and the bounded online sketch; the earlier access blocker is resolved by the attachment.
