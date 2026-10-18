# Sources and coverage

Book orientation: *Software Architecture: The Hard Parts*, 1st edition (2021); Neal Ford, Mark Richards, Pramod Sadalage, Zhamak Dehghani.

**Coverage: partial. No full-book conversion.**

No authorized full edition available; used official Thoughtworks-hosted Chapter 7 and primary architecture/outbox articles. Migration procedures are original supplemental guidance, not claimed book content.

## Evidence map

| Source | Supports / locator |
| --- | --- |
| [Software Architecture: The Hard Parts — author companion site](https://architecturethehardparts.com/) | Bibliographic identity and scenario-oriented approach |
| [Software Architecture: The Hard Parts — official free Chapter 7](https://www.thoughtworks.com/content/dam/thoughtworks/documents/books/bk_software_architecture_hard_parts_ch7_en.pdf) | Service Granularity: separation/integration forces, transactions, workflows, shared code/data |
| [Microservices — James Lewis and Martin Fowler](https://martinfowler.com/articles/microservices.html) | Deployment boundaries, data ownership, operational costs and distributed trade-offs |
| [Transactional outbox — Chris Richardson](https://microservices.io/patterns/data/transactional-outbox.html) | Atomic business-state/event intent; relay duplication and consumer idempotency |

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

- Other book chapters, book case studies, full data architecture and saga taxonomy
