---
name: systems-profiling
description: "Choose and interpret CPU samples, allocation profiles, off-CPU stacks, and flame graphs. Use when locating expensive code, lock waits, or benchmark regressions after a performance symptom is established."
---

# CPU and waiting-time profiling

## Choose what time means

Start with the event: on-CPU samples, wall time, allocations, lock waiting, or I/O
latency. State the target process/thread, interval, sample rate, and expected
coverage. A CPU profile answers where sampled CPU execution occurred. It cannot
by itself explain a request that mostly waited.

## Procedure

1. Reproduce representative work and record end-to-end latency and useful
   throughput. Preserve a baseline profile from the same load/configuration.
2. Select the lowest-cost observation that distinguishes hypotheses. Start with
   counters; use sampling for stack distributions and tracing for event sequence.
3. Capture a bounded profile. For a Linux process, an example is
   `perf record -F 99 -g -p PID -- sleep 20`. Permissions, stack-unwinding support,
   and rate limits vary; record the actual event and lost-sample warnings.
4. Inspect symbols and stack completeness before interpreting results. Missing
   frame pointers, JIT symbols, inlining, and broken unwind chains can hide work.
5. Interpret flame graph width as aggregate weight for the chosen event. Horizontal
   position is not chronological order; stack height is call depth, not duration.
6. Identify a mechanism: repeated allocation, redundant parse, excessive syscall,
   contended critical section, or cache-unfriendly access. Compare absolute sample
   rates or CPU time as well as percentages.
7. Change one mechanism, repeat at matched load, and verify response-time and
   correctness outcomes. Read [profile interpretation](references/profiles.md).

## Decision rules

- Wide CPU frame with many descendants: distinguish inclusive from self cost.
- Low CPU with poor latency: collect request spans or waiting-time evidence.
- More CPU after a latency fix: useful throughput may have increased; normalize
  per completed business operation before calling it a regression.
- Allocator hot: inspect object lifetime and allocation frequency before replacing
  the allocator. Retained memory and allocation rate answer different questions.
- High spin cost: examine lock ownership and critical-section work. Replacing
  spinning with blocking changes scheduling and throughput trade-offs.

## Output

Report event, scope, sample quality, dominant stack/mechanism, competing
explanations, proposed change, measured before/after, and remaining uncertainty.

## Scope and references

Partial companion skill for *Systems Performance*, 2nd ed. (Gregg), grounded in
the official Operating Systems sample and author flame-graph documentation. See
[sources](references/sources.md). This is not a guarantee that `perf` or eBPF is
available. Kernel tracing can add overhead; choose permissions and duration
appropriate to the environment.
