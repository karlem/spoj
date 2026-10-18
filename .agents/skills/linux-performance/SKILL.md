---
name: linux-performance
description: "Investigate high p99 latency, throughput plateaus, resource saturation, and container throttling on Linux. Use to choose measurements, form bottleneck hypotheses, and validate changes under representative load."
---

# Linux performance investigation

## Establish the symptom

Record the affected operation, arrival rate, concurrency, payload distribution,
error rate, latency histogram, time window, and recent changes. Separate service
time from queueing and end-to-end response time. Compare a healthy interval with
the incident at similar load. A single host average cannot explain a fleet p99.

## Investigation procedure

1. Define the measurement boundary and SLO. Include failed and timed-out requests;
   a dashboard of only successful requests can hide collapse.
2. Apply USE (utilization, saturation, errors) to each plausible resource: CPUs,
   memory, storage, network, and bounded software pools. Saturation means waiting
   work; high utilization by itself does not prove a bottleneck.
3. Find where request time accumulates. Correlate application spans, run queues,
   pressure stalls, pool wait, and device latency over the same interval.
4. In containers, inspect the process's cgroup CPU quota, throttling deltas,
   memory limit/events, and pressure before interpreting host capacity. Spare
   host CPU does not imply that a throttled container can run.
5. Write competing hypotheses and the observation that would falsify each. Use
   [measurement choices](references/measurements.md); profile only after choosing
   the event and time basis.
6. Change one factor, rerun at matched load, and compare latency distributions,
   throughput, errors, and resource cost. Use the [experiment protocol](references/experiments.md).
7. Check sustained load, bursts, and recovery. Reject an improvement that moves
   work to an unmeasured queue or changes correctness.

## Decision rules

- CPU runnable delay rising with demand: inspect quota, per-CPU skew, and CPU
  stacks. Load average also includes some uninterruptible tasks; it is not CPU %.
- High latency with low on-CPU demand: inspect I/O, lock/pool waits, scheduler
  delay, and downstream spans. A CPU flame graph cannot account for all waiting.
- Memory pressure: distinguish allocation rate, resident working set, reclaim,
  swap, major faults, and OOM events. “Free memory” alone is not diagnostic.
- Device `%util` is not a universal capacity gauge for parallel storage. Use
  latency, queue depth, IOPS/bytes, workload shape, and device capabilities.

## Output

Return symptom → evidence with units/time window → competing hypotheses → next
measurement → proposed change → controlled validation → rollback criterion.
Mark missing permissions, unsupported counters, and ambiguous causality.

## Scope and references

Partial coverage of *Systems Performance*, 2nd ed. (Brendan Gregg), using the
publisher Operating Systems sample and the author's USE material. Kernel pressure documentation
supplements container diagnosis. See [sources](references/sources.md). Commands
are examples for Linux; availability and semantics vary by kernel/tool version.
