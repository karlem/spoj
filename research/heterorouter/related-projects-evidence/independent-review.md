# Independent related-projects survey review

Read-only static review on2026-10-17 of related-projects-and-papers.md and related-projects-sources.json, against selected primary files under /workspace/scratch/related-projects. No project code imported or executed; no builds, tests, model downloads or inference. No repository edits.

## Outcome

APPROVED. The identified HybriMoE source-fidelity correction is now explicitly included in the written survey, with the rank/ID example and global-UID nonfinding. No unresolved blocking findings.

### HybriMoE score-order caveat

In experts.py679-692, torch.topk supplies scores in rank order, but assignment via current_priority_scores[mask] addresses selected experts in ascending expert-ID order. These orders can differ: IDs[2,0] with scores[.9,.8] would associate .9 with expert0 and.8 with expert2. The survey should identify the intended score-aware EMA mechanism while explicitly noting this inspected association mismatch, rather than implying a verified correct per-expert update. This is static source reasoning, not an executed upstream failure or a paper-level claim.

A tentative concern about get_expert_to_unload lacking a layer argument was investigated and withdrawn: callsite961 passes dictionary keys that are global expert_uid values, populated at989; prefetch1066 explicitly constructs expert_uid=expert_idx+layer*expert_num_per_layer. No unsupported offset bug should be reported.

## Source checks

Independently recomputed and matched all19 source file sizes/SHA256s across9 pinned repositories. This confirms local selected-source/manifest consistency; no new independent upstream fetch performed.

Fiddler constants7/70 and device-calibration TODO match constructor38-39. Prefill comment specifies max(CPUcostsum,GPUcostsum), while lines580-590 enumerate a single sum of selected per-expert costs; draft correctly calls it a source/comment mismatch without claiming a paper result or measured defect.

exo memory_once_loaded reserves not-yet-loaded shard bytes; placement filters cycle connectivity, memory, model/backend compatibility and applicable RDMA controls. Ranking uses downloaded-model fraction and availableRAM, after other cycle preferences. Draft avoids claiming general latency-optimal routing or arbitrary mixed-backend compatibility.

DistributedLlama README explicitly says tensor parallelism, root/worker memory split, power-of-two total nodes and KV-head/quantization restrictions. Draft correctly separates this from expert-parallel sharding and leaves root-loader peak memory unaudited.

MoE-Infinity README explicitly restricts current distributed operation to single-server multiGPU and notes public code differs from the paper version. DeepEP pinned README explicitly lists Linux,Hopper-or-newer,CUDA13.1+,intranodeNVLink/internodeRDMA; dispatch/combine completion waits and caller-provided replication/rerouting are described. HexGen group helper consumes supplied heterogeneous groups/partition rather than itself proving a placement optimizer. KTransformers tutorial is clearly described as documented capability, not audited inference code.

All seven listed paper title/ID or DOI/venue references match authors primary repository citations. The survey explicitly states full papers were not read and makes its questions a reading agenda, not extracted algorithms/theorems. Scope is a capacity-first shortlist, not model compatibility, a deployment result or comparative physical-speedup evidence.
