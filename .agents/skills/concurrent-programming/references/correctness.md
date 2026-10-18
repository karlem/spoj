# Histories, invariants, and visibility

## Original lost-update schedule

Two threads perform `count = count + 1`, starting at zero:

```text
A reads 0
B reads 0
A writes 1
B writes 1
```

The result is one rather than two. Making `count` Java `volatile` provides
visibility/ordering properties but still leaves the read-modify-write sequence
split. Use a suitable atomic increment or protect the whole invariant with a
lock. If the counter accompanies other state, one atomic counter may still leave
the multi-field invariant exposed.

## Linearizability review

A concurrent history is linearizable if completed operations (and an appropriate
completion of some pending operations) can be placed in a legal sequential order
that preserves real-time precedence of non-overlapping operations. Overlapping
operations may have either order if the sequential specification permits it.

Example: `enqueue(x)` completes before `dequeue()` starts. A FIFO queue's dequeue
cannot report empty if no earlier removal consumed `x`. This is a useful small
counterexample. For overlapping enqueue/dequeue, observing empty may be legal if
the dequeue linearizes first. A timestamped log needs reliable invocation/response
boundaries; source-line order alone does not define the concurrent history.

A successful CAS may be a linearization point for one algorithm. A failed CAS,
empty return, or helping operation needs its own reasoning. Local atomicity of
one pointer update is not proof of FIFO semantics, safe memory access, or progress.

## Java publication

If a producer initializes data and then writes a volatile `ready = true`, and a
consumer observes that write through a volatile read before using the data, the
happens-before chain can publish those prior writes. The protocol must prevent
unsynchronized later mutation and define reuse/reset. A flag recycled for multiple
messages without sequencing can conflate generations.

Lock release/acquire can provide another publication path. Use the same monitor
for the protected state, keep the predicate and its transition under that protocol,
and recheck condition-wait predicates in a loop because wakeups do not reserve
the state for the awakened thread.

## Deadlock and open calls

A waits for B's lock while B waits for A's lock. Adopt a global acquisition order
or redesign ownership; a timeout can limit waiting but does not repair a partially
executed invariant automatically. Calling untrusted callbacks or external I/O while
holding a lock adds hidden lock order and unbounded duration. Copy the necessary
state, release the lock, perform the open call, then revalidate state if needed.

## Validation ladder

1. Reason about a minimal bounded schedule with explicit operations.
2. Enumerate small histories and check the sequential specification.
3. Add platform-appropriate race detection and adversarial stress.
4. Measure scaling, tail latency, allocation, and fairness under real contention.

A test that observes no lost increment on one machine does not establish correct
memory ordering or safe publication. Different optimizations and scheduling can
expose a schedule the test never generated.
