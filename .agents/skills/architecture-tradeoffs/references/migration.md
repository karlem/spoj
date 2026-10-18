# Migrate a boundary without losing the source of truth

1. Isolate a capability behind a stable internal interface before relocating it.
   Instrument current behavior and record invariants for migration comparison.
2. Choose the authoritative writer for each stage. A copy of the data is not a
   second authority unless conflict resolution is explicitly designed.
3. Expand contracts first: old and new readers can tolerate the new shape. Backfill
   data using a checkpointed, restartable process and reconcile counts/values by
   stable key. Counts alone do not prove equal contents.
4. Shadow only safe operations. Duplicate reads can compare results; shadowing a
   charge or notification creates real side effects unless the target is isolated.
5. Shift traffic gradually with monitoring of correctness, latency, errors, event
   lag, and cost. Keep a clear rollback boundary.
6. Contract old schemas/APIs only after consumers have migrated and the rollback
   window has closed. A destructive data migration can make code rollback unsafe.

## Dual-write failure

Writing a local row and then calling a remote service leaves a crash window after
the first write. Reversing the order only moves the window. Use an atomic outbox
when business state and event intent share a transaction; consumers still need
replay-safe handling. A saga records progress and business compensation, but
compensation is not identical to database rollback. A sent email cannot be unsent;
a refund is a new financial event and can also fail.

## Shared database trade-off

A shared database can support local ACID transactions and simple queries, making
it a reasonable early choice. Multiple owners directly changing each other's
schema and rows reduce independent evolution and make security isolation harder.
Introduce ownership and APIs around writes before assuming that separate databases
will fix coupling. A reporting replica/derived view can serve cross-domain queries
without becoming another authority for transactional writes.

## Migration acceptance

- Old and new clients work during the compatibility interval.
- Backfill can restart without duplicating business effects.
- Events arriving during backfill cannot overwrite newer state with old state.
- Ownership is unambiguous during cutover and rollback.
- Reconciliation finds value mismatches, missed updates, and orphaned records.
- Operators know how to detect and repair partially completed workflows.

Exercise: an extracted service stores a copied balance and starts accepting writes
before CDC has caught up. Describe the lost-update and conflicting-authority risk,
then specify a cutover barrier or protocol that makes the transition auditable.
