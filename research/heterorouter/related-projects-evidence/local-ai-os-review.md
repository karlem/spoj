# Independent local-AI/OS survey extension review

Read-only static review of appended Affordable local AI as a foundation for an AI OS section and local-ai-os-sources.json, against five pinned primary READMEs. No implementation inspection, setup, builds, tests, model downloads, inference or benchmarks. No repository edits.

## Outcome

APPROVED. No blocking factual or scope findings.

Independently recomputed all five README byte counts and SHA256 hashes; all match the manifest. This is local source/manifest consistency verification, not a new independent upstream network fetch.

Prima primary README supports device profiling, heterogeneous layer and GPU-offload assignment, dropping weak devices, piped-ring/prefetch and mmap/page-cache behavior. Its AppleMetal benchmark-table entry conflicts with the CUDA-only FAQ; the section accurately highlights the inconsistency rather than assuming mixed GPU support. It avoids presenting low memory pressure or mmap as all-RAM capacity guarantees. Title and ICLR2026 paper link match the primary citation.

PowerInfer README describes hot/cold neurons, sparse activation, CPU/GPU co-computation, adaptive predictors and special PowerInferGGUF carrying model/predictor weights. It links PowerInfer2/2406.06282 and describes smartphone/TurboSparse results. Section correctly avoids generic arbitrary Qwen/MoE compatibility or borrowing author measurements. No full-paper mechanisms are claimed extracted.

FlexLLMGen README explicitly targets high-throughput large batches with IO-efficient offload, and warns of poorer small-batch behavior. AIOS README explicitly describes an abstraction above the host OS kernel for agent resource/tool/model management, not a replacement accelerating low-level inference. IX README specifies protected dataplane OS research, IntelDPDK and supported Intel82599/X520/X540 NICs; section appropriately marks historical hardware-specific scope rather than a modern inference recommendation.

Illustrative arithmetic is correct and properly conditional:32serial dependent2ms request/response crossings contribute64ms; eliminating a hypothetical5%critical-path fraction has ideal Amdahl speedup1/.95=1.05263. Neither is claimed as a measured SPOJ overhead, universal communication bound or established network bottleneck. Memory/compute/transport/control mechanisms are separated and later comparisons explicitly remain proposals. Main implementation/nativeMac gates unchanged.
