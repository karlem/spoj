# Sources and coverage

Book orientation: *The Art of Multiprocessor Programming*, 2nd edition (2020); Maurice Herlihy, Nir Shavit, Victor Luchangco, Michael Spear.

**Coverage: partial. No full-book conversion.**

No authorized full edition available. Direct Elsevier title and ScienceDirect endpoints were denied; publisher catalogue and search metadata confirm edition. Used author-hosted Herlihy/Wing paper and official Java/reclamation documentation; this is original subject coverage.

## Evidence map

| Source | Supports / locator |
| --- | --- |
| [Elsevier software engineering catalogue — book listing](https://shop.elsevier.com/books/subjects/physical-sciences-and-engineering/computer-science/software/software-engineering) | Confirms The Art of Multiprocessor Programming 2nd ed., 2020; metadata only |
| [Linearizability: A Correctness Condition for Concurrent Objects — Herlihy and Wing, 1990](https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf) | Sections 1–3: legal sequential histories and real-time precedence |
| [Wait-Free Synchronization — Maurice Herlihy, 1991](https://cs.brown.edu/~mph/Herlihy91/p124-herlihy.pdf) | Introduction and model: per-operation finite-step progress independent of other process speeds |
| [Java Language Specification SE 25, Chapter 17](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html) | 17.4 memory model, 17.4.5 happens-before and synchronization; wait/notify rules |
| [Java SE 25 java.util.concurrent.atomic package](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/atomic/package-summary.html) | Atomic update operations and memory effects; algorithm-level progress requires separate reasoning |
| [crossbeam-epoch official crate documentation](https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/) | Deferred reclamation, pinned readers, retired objects and stalled participants |

## Attribution boundaries

These procedures, scenarios, code, and decision tables are original engineering
synthesis. They are not quotations, reproductions of book examples, or a substitute
for the cited books. A contents page verifies scope/identity only. Supplemental
implementation documentation supports the stated mechanisms, not claims about
unread book chapters. Context-dependent choices are recommendations, not guarantees.

Read the mechanisms reference relevant to the task; do not load all references
automatically. Source snapshots were accessed on 2026-10-18. Original URLs, observed
HTTP status, hashes, extraction methods, and acquisition failures are recorded in
the repository’s `sources/manifest.json`. No source license transfers to this library.

## Not covered

- Full second-edition text, complete algorithms/proofs, transactional memory and language-specific lock-free implementations
