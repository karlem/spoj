---
name: concurrent-programming
description: "Diagnose shared-memory races, deadlocks, unsafe publication, and contention. Use when reviewing locks, atomics, concurrent queues, compare-and-swap loops, or claims of lock-free and wait-free progress."
---

# Concurrent object correctness

## State the model first

Identify language memory model, shared objects, operations, invariants, and allowed
histories. “Thread-safe” must name an operation and property. Race freedom,
linearizability, deadlock freedom, and bounded progress are different questions.

## Procedure

1. Write a sequential specification: valid inputs, state transitions, and results.
   Then mark each read/write of shared state and its synchronization mechanism.
2. Construct the smallest harmful interleaving. Look for compound check/update
   operations, publication before initialization, escaped references, and callbacks
   while holding locks. Use [correctness](references/correctness.md).
3. For each operation, identify a linearization point or a justified interval-based
   argument. Successful atomic instructions do not prove the entire object is
   linearizable.
4. Establish a happens-before path for publication and later mutation. In Java,
   a volatile flag can publish earlier writes when read accordingly; it does not
   make later increments or a compound protocol atomic.
5. Check lock ordering, wait predicates in loops, cancellation, and exception paths.
   Draw a wait-for cycle for suspected deadlock.
6. For lock-free code, review memory reclamation, ABA, retry loops, and actual
   progress guarantees. Read [progress](references/progress.md).
7. Validate bounded histories against the sequential specification, use available
   race detectors/stress tools, and measure scaling under contention. Passing a
   stress run is evidence for exercised schedules, not a proof.

## Prefer the smallest justified mechanism

A mutex around a short invariant is often easier to verify than a custom atomic
protocol. Read/write locks, sharding, immutability, or ownership transfer may fit
specific workloads. Choose based on measured contention, latency, and correctness,
not the prestige of “lock-free.”

## Output

Give invariant → failing schedule → memory-order reasoning → minimal fix → progress
limits → validation. Separate theoretical algorithm progress from runtime allocation,
scheduler, garbage collection, and blocking library calls.

## Scope and references

Partial coverage aligned with *The Art of Multiprocessor Programming*, 2nd ed.
(Herlihy, Shavit, Luchangco, Spear). Technical grounding uses the author/coauthor
linearizability and wait-free synchronization papers and the Java specification; the full book was
unavailable. See [sources](references/sources.md). Do not translate Java volatile
rules directly to C/C++, whose atomics and data-race rules differ.
