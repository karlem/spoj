# Exact user citation supplied: arXiv:2608.00577

The human supplied https://arxiv.org/abs/2608.00577 for the separate research workstream. This resolves the intended identifier. It does **not** establish that we have read its primary text.

## Discovery and access evidence, 2026-10-17

- Primary arXiv abstract/HTML/PDF requests are blocked by the environment proxy (root agent independently checked all three). The earlier arXiv API request was also blocked. No proxy bypass attempted.
- Public GitHub code search for `"2608.00577"` returned secondary indexes. Public repository name/readme search for `HetRoute` returned 0. Repository search for the arXiv ID returned 0. These are limited discovery results, not proof that no author code exists.
- One discovery source is a Japanese secondary summary at https://github.com/uni042/llm-paper-summary/blob/50cbf70c14ab97d64fd411e5bf594a075fc74b55/papers/inference/12-moe-parallelism-communication/2026-2608.00577-hetroute-collaborative-routing.md . We read it **only for bibliographic/source discovery**, not as authority for algorithm reconstruction.
- That source identifies the title as **HetRoute: Heterogeneous and Cost-aware Collaborative Routing Framework for Distributed Edge MoE Inference**, and lists five authors. A second mirror, checked by root at https://github.com/CSQianDong/Awesome-arXiv-Daily-Reporter/blob/9b383750edcd578dabc0feb142ec655d662c2a23/4-Aug-2026/NLP/papers.jsonl , lists **Xin Yuan, Ning Li, Wenchao Xu, Athanasios V. Vasilakos, Song Guo, Haijun Zhang**. The omission of Athanasios V. Vasilakos in the secondary summary is a concrete reason to retain source provenance and check the actual paper. Identity is supported by mirrored metadata, pending direct primary retrieval. The secondary summary states official code was not confirmed as of its 2026-09-11 check.
- Hugging Face paper API and Crossref metadata requests were also denied HTTP403. GitHub code search for the arXiv identifier plus PDF extension returned 0; exact-name commit search returned 0. No official primary implementation was identified.

## Paper-reading extraction plan

Obtain the actual versioned PDF through permitted access or a user attachment. Record version/date/hash, distinguish paper content from its references and secondary explanations, and extract:

1. The exact mathematical objective, units/normalization, decision variables and constraints, with equation and section/page references. Is the target per-layer critical-path latency, full request latency, throughput, quality, or a weighted surrogate?
2. The offline/online split: expert placement, replication, memory residency and precision versus online route/aggregation choices. Identify which inputs are assumed known and which are observed/estimated.
3. Candidate eligibility and feasibility: identical expert copies versus different experts; precision changes; queue-stability constraints; fallback semantics; quality guarantees versus empirical estimates. **Strict HF contribution parity remains a separate contract.**
4. Exact algorithm pseudocode, thresholds/beam widths only if verified from the primary text, complexity, tie-breaking, search fallback and resource constraints. Read any released author implementation against these details.
5. Network cost model: directional throughput, RTT versus one-way latency, duplicated/deduplicated token payloads, shared-link contention, compute/communication overlap, aggregation destination, queue model and next-layer lookahead.
6. Evaluation lineage: physical measurements versus trace-driven simulation, workload, calibration data, arrival model, hardware, baselines, cost-accounting fairness, confidence intervals and failure/missing-work accounting.
7. Claims and limitations with exact evidence locations. Do not reproduce headline performance numbers before checking their definitions and conditions.

The secondary summary mentions approximate execution mechanisms. This is a **verification question**, not an adopted paper fact: does the primary algorithm permit different expert identities or lower-precision replicas under a quality-loss budget? If yes, keep any paper-faithful approximate simulation explicitly separate from a strict-parity adaptation; do not silently remove those features and call the result a reproduction.

## Existing simulation status

`simulate.py` remains the generic, synthetic exact-replica scheduling baseline from before this citation. It has no paper-derived equations, constants, algorithm attribution, primary-source validation or measured-network inputs. Its job-level metrics do not evaluate the paper's possibly coupled top-k layer routing. Do not rebrand it as HetRoute. Paper-faithful coding remains blocked on the primary text; the generic exploratory work is complete and independently reproducible.

## Mirrored abstract comparison map

Root retrieved the full abstract from the second metadata mirror above (local discovery copy `papers-metadata.jsonl`). Treat these as **abstract-level reported features**, not verified equation/pseudocode details:

| Mirrored abstract reports | Generic baseline currently does |
| --- | --- |
| Transmission, GPU–CPU offloading, GPU compute queues, quantization-quality cost | Simplified transmission plus one compute queue; no memory tiers or quality dimension |
| Offline routing-cost-coupled placement, residency and precision choices | Assumes fixed hypothetical identical-replica eligibility; no placement or precision optimizer |
| Whole-top-k-set routing with bottleneck objective | Schedules individual expert jobs; no token/layer completion barrier |
| Exact enumeration or beam-search online selection | Greedy per-job earliest-finish heuristic; neither search reproduced |

The next useful prerequisite is the actual PDF, attached by the user or accessed through a permitted source. No paper-derived simulation should be written from this abstract alone.
