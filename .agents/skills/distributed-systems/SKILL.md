---
name: distributed-systems
description: "Review replication, consistency, partitioning, transactions, and message processing. Use when writes can be retried, consumers can crash, replicas can lag, or a design claims exactly-once effects."
---

# Distributed data correctness

## Start with the contract

Write down the invariant, its scope, and the failures it must survive. “An order
is charged at most once” is useful; “strong consistency” is insufficient. Identify
the authoritative record, derived views, actors, and each commit/acknowledgment
boundary. Ask whether clients need read-your-writes, causal order, linearizable
operations, serializable transactions, or merely eventual convergence.

## Review procedure

1. Draw the write path, including database commit, broker acknowledgment, and
   external side effects. Record what each successful response guarantees after
   a process crash, machine loss, or replica failover. A timeout means unknown
   outcome, not necessarily failed execution.
2. Enumerate crash windows before and after every durable step. For each, replay
   the operation and check the invariant. Test concurrent attempts as well as
   sequential retries. Use the [failure ledger](references/failure-ledger.md).
3. Keep a business effect and its deduplication marker in one transaction when
   they share a database. For outgoing events, consider a transactional outbox.
   For remote effects, require a durable provider idempotency contract or a
   reconciliation state machine. Broker delivery guarantees stop at their
   documented transaction boundary.
4. Identify ordering scope: key, partition, stream, or global. Choose the narrowest
   scope that preserves the invariant. A partitioned log orders its partitions;
   it does not automatically order related events in different partitions.
5. For replication and failover, inspect election, fencing, acknowledgment policy,
   and recovery. `R + W > N` gives set intersection under fixed membership; it
   alone does not establish linearizability. See [consistency](references/consistency.md).
6. For sharding, verify transaction locality, hot keys, rebalancing, and uniqueness
   enforcement. Measure the busiest shard, not only aggregate throughput.
7. Produce the smallest counterexample to a doubtful guarantee and a test that
   exercises it. Separate required guarantees from acceptable staleness.

## Review output

Return: invariant → assumptions → failure timeline → violated guarantee →
minimal fix → costs → validation. Include a recovery path for already inconsistent
data. Name any behavior that depends on a database, broker, or provider version.

## Check before recommending

- Can a retried request reuse its stable operation ID with changed parameters?
- Does a lease holder need a monotonically increasing fencing token enforced by
  the resource? Lease expiration alone cannot stop a paused process.
- Can replicas serve stale values immediately after a successful write?
- Do tombstones or deduplication records expire before the replay horizon?
- Does a multi-record invariant require a transaction or explicit coordination?

## Scope and references

Partial coverage aligned with *Designing Data-Intensive Applications*, 2nd ed.
(Kleppmann and Riccomini). These original procedures use public author course
notes and additional primary documentation; the full book was unavailable.
Read [sources](references/sources.md) for exact attribution. This skill does not
supply a consensus implementation or assume Byzantine fault tolerance.
