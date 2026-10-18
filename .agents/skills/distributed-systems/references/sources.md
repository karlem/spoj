# Sources and coverage

Book orientation: *Designing Data-Intensive Applications*, 2nd edition (2026); Martin Kleppmann, Chris Riccomini.

**Coverage: partial. No full-book conversion.**

Publisher offers commercial/full-access reading; no authorized full ebook was available in the environment or found for unrestricted processing. Used publisher contents for identity and public author course notes plus listed primary supplements for mechanisms.

## Evidence map

| Source | Supports / locator |
| --- | --- |
| [Designing Data-Intensive Applications, 2nd Edition — publisher contents](https://www.oreilly.com/library/view/designing-data-intensive-applications/9781098119058/) | Bibliographic identity and second-edition topic map only |
| [Martin Kleppmann — author site](https://martin.kleppmann.com/) | Second edition coauthored with Chris Riccomini, published in 2026 |
| [Distributed Systems — Martin Kleppmann, Cambridge 2021/22](https://www.cl.cam.ac.uk/teaching/2122/ConcDisSys/dist-sys-notes.pdf) | Sections 1.3, 3, 4, 5, 6 and 7: RPC outcomes, clocks, ordering, replication, consensus, consistency |
| [How to do distributed locking — Martin Kleppmann](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html) | Lease expiry, paused clients, fencing tokens and enforcement |
| [PostgreSQL INSERT reference](https://www.postgresql.org/docs/current/sql-insert.html) | ON CONFLICT, unique constraints and RETURNING |
| [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) | Serializable behavior, snapshot anomalies and retries |
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

- Full second-edition chapter text, analytics, encoding/schema evolution, stream processing and complete consensus algorithms

The Cambridge notes identify a Creative Commons BY-SA license without specifying
a version in the retrieved text. No note text, diagrams, or close adaptations are
distributed here; the license notice is recorded for future acquisition/reuse review.
