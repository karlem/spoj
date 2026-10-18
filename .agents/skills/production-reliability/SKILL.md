---
name: production-reliability
description: "Review deadlines, retries, idempotency, circuit breakers, bulkheads, backpressure, and deployment recovery. Use when dependency failures cascade, queues grow, or a service must remain usable under partial failure."
---

# Production failure containment

## Trace one failure through the system

Record the user deadline, critical dependencies, retries at every layer, bounded
resources, and irreversible effects. Start from a concrete failure: slow response,
connection refusal, ambiguous timeout, overload, or partial deployment.

## Procedure

1. Allocate one end-to-end deadline across queueing, connection setup, calls, and
   recovery. Propagate remaining time; a socket read timeout is not automatically
   a total request deadline.
2. For every retry, identify why it is safe and useful. A timeout does not establish
   that a side effect failed. Require idempotency or reconciliation for ambiguous
   operations. Use the [retry worksheet](references/retries.md).
3. Bound attempts and retry traffic. Prefer one retry-owning layer per call path;
   use capped backoff with jitter and respect remaining deadline and server hints.
4. Bound concurrency, pool waits, queue length/age, and per-tenant usage. Backpressure
   needs an actual admission/rejection protocol, not just an async queue.
5. Isolate failure domains with bulkheads. Circuit breakers can stop repeated calls
   to a failing dependency; they do not provide a concurrency limit by themselves.
6. Define degradation that preserves the business invariant. Stale recommendations
   may be acceptable; silently accepting an unrecorded payment is not.
7. Inject slow, failed, and recovering dependencies in a disposable environment.
   Verify useful throughput, resource bounds, and time to recover. See
   [containment](references/containment.md).

## Review checklist

- Can the slowest dependency occupy every worker or connection?
- Can retries amplify load while the dependency is already overloaded?
- Can canceled requests keep doing expensive work?
- Do startup/readiness checks create a dependency on an optional service?
- Can a rollout mix incompatible schema and application versions?
- Is recovery behavior tested after failure, including backlog drain and probe storms?

## Output

Return a failure timeline, resource/retry budget, correctness conditions,
containment changes, observable failure signals, recovery test, and rollback rule.
Choose numbers from measured workloads and SLOs, not universal timeout constants.

## Scope and references

Partial coverage aligned with *Release It!*, 2nd ed. (Michael T. Nygard), using
publisher excerpts and primary operational guidance. See [sources](references/sources.md).
This skill does not promise availability under unbounded load or make remote
side effects atomic with a local database.
