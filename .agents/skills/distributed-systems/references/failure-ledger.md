# Crash windows and durable effects

## Original scenario: an invoice consumer

A worker reads `InvoiceRequested(id, account, amount)`, updates a ledger, then
acknowledges the message. Assume at-least-once delivery, a transactional database,
and a unique constraint on `(consumer, event_id)`.

| Failure point | Durable state | Replay behavior required |
| --- | --- | --- |
| Before transaction | Nothing | Execute normally |
| After marker insertion, before commit | Nothing after rollback | Execute normally |
| After effect and marker commit, before broker ack | Both present | Skip effect, then acknowledge |
| After broker ack | Both present | No replay required for correctness |

The transaction must cover the effect and marker together. Inserting the marker
in an earlier transaction loses effects after a crash; inserting it after the
effect permits duplicates. A check-then-insert outside a transaction races.

Illustrative PostgreSQL transaction (original example):

```sql
BEGIN;
INSERT INTO processed_events(consumer, event_id)
VALUES ('invoice-ledger-v1', :event_id)
ON CONFLICT DO NOTHING
RETURNING event_id;
-- Only when a row was returned, in this SAME transaction:
INSERT INTO ledger_entries(event_id, account_id, amount)
VALUES (:event_id, :account_id, :amount);
COMMIT;
-- Acknowledge the broker only after COMMIT succeeds.
```

Branch on the actual returned row count; the comment is not executable control
flow. Roll back if the effect fails. Use a consumer-specific marker so another
consumer can process the same event. If IDs can be reused with different payloads,
store and compare a canonical request fingerprint and reject mismatches.
Database isolation and uniqueness behavior must support this transaction; verify
against the selected engine. The SQL is illustrative, not portable middleware.

## Crossing a transaction boundary

An outbox row commits alongside business state. A relay may publish it twice if
it crashes between publish and marking the row sent. Therefore an outbox prevents
the database/publish dual-write gap but does not remove consumer deduplication.
Partition ordering may require a sequence and a relay that preserves it; “one
outbox table” does not prove order with parallel relays.

A provider charge is outside the local transaction. Persist the intended operation
ID, call the provider with that key, then record the known result. A timeout leaves
the state pending/unknown. Query the provider or retry under its documented
idempotency semantics before deciding to create a new operation. Inspect retention,
parameter-mismatch rules, and whether failure responses are cached. An in-memory
set is lost on restart and does not coordinate multiple workers.

If the provider offers neither idempotency nor a lookup/reconciliation mechanism,
a local transaction cannot guarantee both completion and no duplicate remote
effect under arbitrary crashes. State that limitation and choose an explicit
business policy rather than claiming exactly-once processing.

## Recovery checklist

- Test crashes at each row in the ledger with durable restart state.
- Simulate two workers executing the same event concurrently.
- Replay after the longest supported outage and after a consumer deployment.
- Define poison-message handling without silently acknowledging lost work.
- Measure outbox age, replay rate, dedup conflicts, and unresolved operations.
- Retain dedup state for the documented replay horizon, including restores.

Exercise: a database restore rolls back markers but an external provider retains
charges. Explain why replay can charge again unless operation IDs survive restore
or reconciliation checks the provider. The broker offset alone cannot repair this.
