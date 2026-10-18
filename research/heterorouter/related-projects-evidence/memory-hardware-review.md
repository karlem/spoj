# Independent memory hardware/far-memory survey review

Read-only static review of Memory hardware, far memory and near-memory computation appended section and memory-hardware-sources.json. Examined pinned primary READMEs and three selected LIA sources under /workspace/scratch/memory-hardware. No repository edits, source project execution, tests, builds, papers fetched, kernel/OS changes or hardware/model experiments.

## Outcome

APPROVED. No blocking factual, source-attribution or scope findings.

Independently recomputed all12 selected file sizes/SHA256s across9 repositories; all match manifest. This verifies selected local sources against recorded manifest, not independent upstream retrieval.

Pond README explicitly identifies the artifact as CXL emulation/evaluation scripts rather than full Pond. It describes remote-socket NUMA memory and disabled remote CPU cores, with150ns as emulation target. Section appropriately avoids turning this into a real CXL fabric result or proposing unsafe script execution.

LIA README lists >=4th-generation Xeon and NVIDIAA100/H100, with suppliedOPT examples forSPR-A100. Selected numa_alloc.c sets interleave bits2/3; numa_alloc.py loads an absolute machine-specific shared-library path and wraps the allocation through framework buffer/storage/tensor construction. The section correctly treats physical CXL topology and final tensor page residency as unverified, rather than assuming node numbers prove CXL or declaring a runtime bug. Supplied batch900-and-larger scripts do not establish interactive latency.

CENT README describes trace generation,AiM performance simulation,power/cost modeling and figure reproduction; complete simulation hours/memory/disk costs match the draft. No physical GPU replacement is inferred. PrIM explicitly documents both realUPMEM modules and SDK functional simulation, deprecated officialSDKsite andCMU-SAFARI archive; the draft correctly separates functional validity from hardware timing and current procurement/support uncertainty. Vendor demo is a checksum example withC/Pythonhost interfaces, notLLMinference.

AIFM README states C++ far-memory pointers/containers and TCP remote-server memory, using Shenango runtime, and strongly recommends the CloudLabxl170 test environment. Draft correctly limits this to an application-integrated far-memory design rather than a transparentPyTorchallocator or verified ordinary-host deployment. Infiniswap/Leap distinctions remain remote paging/RDMA with historical prerequisites. CXL-SpecKV is expressly a lower-confidence source lead whose paper/hardware/headline claims were not validated.

General distinctions are sound:CPU-visibleCXL is not automaticallyGPU-localVRAM;remote byte fetch differs from remote expert execution;PIMkernels need explicit numerical/backend validation. Proposedlab ladder,past-only tier adaptation,capacity ledger,staging transients andcompute-near-weights comparison remain proposals. No unmeasured hardware bottleneck,speedup,retail availability or purchase recommendation is asserted. Fullpapers-read and hardware-executed flags remainfalse;maincorrectness/nativeMac scope unchanged.
