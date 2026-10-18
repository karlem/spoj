# Independent expanded software/Mac atlas review

Status: APPROVED. Final appended Software research atlas and Apple / heterogeneous execution paths section and its two manifests independently reviewed. No unresolved blocking findings. Read-only repository role. No source project code, models, setup, builds or tests executed; no downloads/paper fetches and no repository edits.

## Confirmed primary distinctions

MLX distributed.rst195-245 documents macOS26.2+,Thunderbolt5 and recovery-mode RDMA activation, explicitly not remote-sudo activation. Highlevel docs say mesh-only. Bundledjaccl/lib/README advertises ring; jaccl.cpp125/157 and291-302 implements ring validation/preference and actualRingGroup selection. These are differing documentation/source scopes, not validated support on our existingMac.

EPLB README and eplb.py assume equal cardinality bins, numphysical divisible bynumGPUs and group/node divisibility for hierarchical packing. Replica demand is weight/logcnt; no device service rate, heterogeneous byte budget, link observation or migration cost is supplied. A useful exact-replica placement example, not a ready mixedCPU/GPU capacity optimizer.

Flash-MoE attached pinned author technical report is13pages. Pages1-2 explicitly distinguish native top10 from prunedtop4 and introduce2bit requantization. Page7section5.5 cancels deferred expertcompute andIO for N-1 prefill tokens. These change the original computation contract and cannot establish strict untouchedHFparity. The README currently calls4bit production and reports2bitJSON/toolcalling breakage; that qualifies/contradicts the PDFp1/p5production-quality/no-degradation framing. Neither source independently establishes quality.

Reportp5 says routing profiled over200tokens, then diversity43-57%of512experts perlayer across30tokens; it separately identifiesK4. If all those numbers describe the sameK4window, maximumdistinct selected experts is30*4=120 (23.4375%), below claimed220-292. This is an unresolved configuration/window/count discrepancy, not proof of an engine runtime bug; the surrounding200tokenstatement and possibly differingKmust be clarified. No author performance measurements reproduced.


## Final written-section and manifest review

Independently recomputed sizes/SHA256 for all31 saved source files:22repositoryREADMEs,8selectedsource/docs and1PDF; all match software-mac-sources.json. Evidence counts correspond to21primaryproject repos plus1explicitlysecondarybibliography. software-paper-backlog.json contains21citationentries, including2clearlyidentifiedMooncakeversions from the same research family; full-text and citation-evidence levels remain explicit. These checks verify local source/manifest consistency, not a new independent upstream fetch.

The final text accurately carries the MLX highlevelmesh/bundledring discrepancy, recovery/TB5 constraints, no implicitMetal/CUDA interoperability, and EPLBscope limits. It includes Flash reportsemantics changes, README2bittoolquality disagreement and conditional30*K4diversity bound without inventing a runtime explanation. Citationqueue versus extractedmethod/reproducedresults is consistently separated. Crosschecked newer caveats against pinnedREADMEtext:exoLinuxCPU-only,NIXLLinuxonly,FlashMLAbreakingHopper/earliermodel/KVformat changes,Mixtraloffloadingprefetch upcoming,SiDAoffload/mainmemoryTODOs. No measured speedups,hardwareavailability,universalcachepolicy or uniqueSPOJcapability are asserted.

The nativeMacgate and existingproductscope remain unchanged. Candidate combinations are explicitly explanatory proposals and acknowledge that aJACCLtier needs a separately validated protocol/backend bridge to ordinaryLinux/TCPworkers. No additional tests,imports,builds,models,networkfetches or repositoryedits performed by reviewer.
