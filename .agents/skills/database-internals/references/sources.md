# Sources and coverage

Book orientation: *Database Internals*, 1st edition (2019); Alex Petrov.

**Coverage: partial. No full-book conversion.**

Commercial publisher edition not available; author landing page and publisher contents do not provide full text. Technical coverage comes from SQLite and RocksDB primary documentation, clearly labeled as implementations rather than a book conversion.

## Evidence map

| Source | Supports / locator |
| --- | --- |
| [Database Internals — author book site](https://www.databaseinternals.com/) | Bibliographic discovery only; retrieved page had little substantive material |
| [Database Internals — publisher contents](https://www.oreilly.com/library/view/database-internals/9781492040330/) | Bibliographic identity and topic map only |
| [SQLite database file format](https://www.sqlite.org/fileformat.html) | B-tree page structures and record/index storage |
| [RocksDB leveled compaction](https://github.com/facebook/rocksdb/wiki/Leveled-Compaction) | Sorted runs, level overlap, compaction and amplification trade-offs |
| [SQLite write-ahead logging](https://www.sqlite.org/wal.html) | Reader end marks, checkpointing, concurrency, durability configuration and WAL files |
| [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) | Failure model, write ordering, synchronization and recovery assumptions |
| [RocksDB Bloom Filter](https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter) | Negative lookup filtering, false positives, memory and lifecycle considerations |

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

- Full book, engine implementation, complete distributed algorithms and recovery algorithms
