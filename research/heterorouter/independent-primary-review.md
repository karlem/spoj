# Independent primary-source review

Reviewed 2026-10-17. Read-only repository review of research/heterorouter/primary-analysis.md against user-attached PDF and its pdftotext -layout extraction. No repository edits. This review covers the primary analysis, not a yet-unreviewed executable sketch.

## Outcome

No blocking factual/source-attribution findings in the primary analysis.

Independently checked PDF SHA-256 2ee21d03af26bbeeecb64c4dc7c76eb082b3a40e0ad708fecdf48bf00a65c321, size 3077989 bytes, 15 pages, metadata CreationDate 2026-08-12. Title and five-author list match PDF page 1. The analysis correctly avoids asserting an arXiv revision based on metadata and distinguishes the older discovery mirror from this attachment.

Pages 4-5 support exact-first candidates, physical-replica selection versus logical gate selection, directional bandwidth, quantization/substitution surrogate, four-component assignment cost Eq9, phase-max layer objective Eq10, and SUM gather with optional zero lookahead Eq11. Page7/TableI support the residency probability-weighted offload score and net-benefit replication heuristic; the text properly labels this heuristic rather than a joint optimum. Pages8-10/TableII support normal admission guards, emergency full-precision quality-safe fallback, beam/exact search and finite strict-descent exchange refinement. Page11 supports all stated testbed ranges, requests/s, beam width8 and threshold64 assignments.

The cautions are substantiated: TableII fallback loop handles targets with empty individual sets despite triggering on no feasible complete assignment; individual admission can fail jointly. Eq10 leaves co-located expert sums underspecified while page8 says compute competes. TableII tests collaboration-domain size while Property3 invokes a candidate-product bound; these are different counts. Eq20 does not fully specify beam ordering/ties. Page11 complexity assumes O(1) incremental scoring and constant exchange sweeps; those assumptions do not prove convergence of a capped refinement.

The proposed per-server sum/queue-once objective, product-based search threshold, beam score/tie policy, joint admission, exact/full-precision subset and omitted mechanisms are explicitly marked as adaptation or exclusion. No physical inference, numerical parity, author experiment reproduction, multi-host correctness or performance conclusion is attributed to the sketch.

## Minor observation

The prose accurately limits its claims to the inspected attachment. No author source or immutable experimental artifacts were obtained, so reproducing author headline measurements remains unsupported. Code review and hand-solvable numerical fixtures are still required before accepting executable results.
