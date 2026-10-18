# Choosing consistency and coordination

## Name the observable property

| Need | Candidate property | What it does not imply |
| --- | --- | --- |
| A completed update must precede any later read of that object | Linearizability | Atomic transactions across unrelated objects |
| Transactions behave like some serial execution | Serializability | Real-time order between transactions |
| Both serial behavior and real-time order | Strict serializability | Availability during every partition |
| A user sees their own acknowledged write | Read-your-writes | Everyone sees the same latest value |
| Preserve dependencies between events | Causal consistency | One total order of concurrent events |
| Replicas converge after updates stop | Eventual consistency, under the system's convergence assumptions | A bounded lag or safe arbitrary conflict resolution |

These are contract distinctions, not interchangeable database marketing terms.
Ask what the selected API and isolation level actually guarantee. Snapshot
isolation can allow write skew: two transactions read “one doctor is on call,”
then each removes a different doctor. No overlapping row write is required for
the invariant to fail. Use a mechanism that protects the predicate/invariant,
such as suitable serializable isolation or explicitly locking shared guard state.
Serializable transactions may abort; retries need to preserve business semantics.

## Reason about replicas

Assume fixed replicas and acknowledged writes stored durably by `W` of `N` nodes.
A read from `R` nodes intersects the write set if `R + W > N`. Intersection is
only a set property. Concurrent writes, version selection, incomplete writes,
sloppy quorums, membership changes, and read repair still matter. A timestamp
chosen from a drifting wall clock is not a proof of real-time order. An older
value can survive failover if an acknowledged write was not in the elected
replica's recoverable history.

For a single leader, specify how it is elected and how old leaders are fenced.
A paused leader may resume after its lease expires. A protected storage service
must reject operations carrying older fencing tokens for this protection to work;
merely generating tokens at the client does nothing.

During a network partition, a design that cannot coordinate may reject or delay
some operations to preserve a required invariant. Identify which operations
remain available and which business actions can tolerate reconciliation. Avoid
using CAP as a slogan for unrelated latency or deployment choices.

## Partitioning decision procedure

1. List operations that must commit atomically and the keys they touch.
2. Try a partition key that keeps those operations local.
3. Estimate skew: a celebrity tenant or single inventory item can dominate a shard.
4. Decide how routing changes during migration, including in-flight requests.
5. Test duplicate, reordered, and old-version events during rebalancing.

An inventory counter is not safely split by order ID if all orders compete for the
same finite stock. Options include one owner per inventory item, a transactional
store, or bounded rights allocated to partitions. Each changes contention,
availability, or complexity. Choose from measured demand and the business rule.

## Ordering versus time

A wall clock helps correlate incidents but can move backward. A monotonic clock
measures local elapsed time but does not compare times on different machines.
Logical clocks can represent some ordering relationships; they do not themselves
make a replicated operation atomic. When sequence matters, carry an explicit
version/sequence and define behavior for gaps, duplicates, and stale writers.
