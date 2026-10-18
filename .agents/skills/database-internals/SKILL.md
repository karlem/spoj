---
name: database-internals
description: "Compare B-tree and LSM storage, indexes, compaction, WAL, and crash recovery. Use when selecting a database for a workload, explaining write stalls or read amplification, or reviewing durability assumptions."
---

# Storage engine decisions and recovery

## Characterize the workload

Record key/value sizes, key ordering/skew, read/write mix, point/range queries,
working set, ingest bursts, retention, durability requirements, and storage budget.
Distinguish foreground latency from steady-state maintenance costs. “Write-heavy”
is not enough to choose an engine.

## Decision procedure

1. Identify access paths and the atomic unit: page, record, transaction, or batch.
   Confirm how indexes and the base data remain consistent after a crash.
2. Compare tree and log-structured designs using the [storage worksheet](references/storage.md).
   Include read, write, and space amplification plus maintenance headroom.
3. Inspect memory structures, cache behavior, flush, compaction/checkpoint policy,
   and behavior when background work falls behind. A short in-memory benchmark
   does not exercise steady-state storage.
4. Specify the durability boundary: log append, OS page cache, synchronized log,
   replication acknowledgment, and client response. Distinguish process crash
   from power loss. See [recovery](references/recovery.md).
5. Verify the selected implementation's contracts. WAL layout and checkpoint
   behavior are engine-specific; “uses WAL” alone proves neither isolation nor
   durability under every storage failure.
6. Benchmark with realistic data, secondary indexes, cache state, skew, updates,
   deletes, and sustained load. Record p99, stall time, bytes written, disk use,
   and recovery time as well as operations/s.

## Review rules

- A Bloom filter can avoid many negative point lookups; it does not accelerate
  every range scan or eliminate reading versions in other runs.
- Tombstones cannot be discarded merely because they are old. Older versions or
  replicas may still require them to prevent deleted data reappearing.
- Page splits, cache misses, fsync latency, and compaction can dominate tails even
  when asymptotic search cost looks good.
- A secondary index trades read speed for extra writes, storage, and maintenance.
  Check whether its column order matches real predicates and sorting.

## Output

Return workload assumptions, candidate access paths, amplification/maintenance
trade-offs, recovery contract, discriminating benchmark, and a conditional choice.
Avoid claiming a universal winner between B-trees and LSM trees.

## Scope and references

Partial subject coverage aligned with *Database Internals* (Alex Petrov, 2019).
The full book was unavailable; technical mechanisms here are checked against
SQLite and RocksDB primary documentation. See [sources](references/sources.md).
This is a selection/debugging skill, not an implementation of a storage engine.
