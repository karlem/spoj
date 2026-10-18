# Durability is a protocol

## State the failure model

A process crash can leave kernel buffers intact. A machine/power failure can
lose unsynchronized buffers. A device may acknowledge flushes incorrectly or
fail completely. Distinguish these cases before accepting a durability claim.
Replication adds another failure domain only if copies and their acknowledgment
policy actually protect against the failures being considered.

## Write-ahead logging

The recovery information needed for a dirty page must reach durable storage before
that page can become durable. A successful transaction response may additionally
require its commit/log state to be synchronized, according to the engine's
configuration. Different engines use physical, logical, or mixed records and
different undo/redo strategies. Do not infer ARIES semantics from the word WAL.

SQLite WAL is a concrete example: readers select a consistent end mark, writers
append changes to the WAL, and checkpoints transfer changes back to the database.
Long-lived readers can prevent checkpoint progress beyond their snapshots and
allow WAL growth. SQLite's concurrency and durability behavior depends on journal
mode, synchronization setting, and storage semantics. WAL files are part of the
database's state; copying only the main database file during active WAL operation
can miss committed data. Use the supported backup API/process.

## Crash-review questions

1. What exact event precedes the client receiving success?
2. Which files/records must survive restart, and in what order?
3. How are incomplete transactions distinguished from committed transactions?
4. How are torn writes or corruption detected and handled?
5. Can replay be repeated without applying a logical effect twice?
6. How do checkpoints affect restart time and foreground I/O?
7. Does restore include logs, encryption keys, metadata, and a verified checkpoint?

A checksum detects some damage; it does not reconstruct correct contents by
itself. A replica can faithfully replicate a bad write. Backup usefulness is
established by restore and application-level reconciliation, not successful upload.

## Original incident: growing WAL

A report says “disk is filling, so increase checkpoint frequency.” First inspect
active read transactions and checkpoint progress. If an old reader pins a snapshot,
more frequent checkpoint attempts may not allow reclamation. Bound transaction
lifetimes where the application allows, inspect busy/checkpoint results, and
measure growth/recovery after the reader releases. Do not delete a live WAL file.

## Benchmark recovery too

Run controlled crash/restart tests against disposable data using the documented
fault model. Check committed keys/values and invariants, not just server startup.
Measure recovery duration at realistic log size. A clean shutdown benchmark cannot
prove crash durability, and a process kill cannot fully simulate power loss.
