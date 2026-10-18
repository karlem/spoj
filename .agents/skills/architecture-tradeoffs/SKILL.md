---
name: architecture-tradeoffs
description: "Evaluate service decomposition, shared databases, synchronous workflows, and distributed transactions. Use when deciding whether to split or merge services, extract a module, or accept eventual consistency."
---

# Service boundaries and architecture trade-offs

## Make the decision concrete

List the business invariant, deployment pain, workload, team ownership, and
measurable goal. Compare at least two feasible alternatives, including improving
boundaries inside the current deployment. Service count is not a quality metric.

## Procedure

1. Map changes, calls, transactions, and data ownership between proposed units.
   Mark synchronous dependencies and boundaries that must change together.
2. Identify forces favoring separation: independent change, different scaling,
   security isolation, failure containment, and distinct domain behavior. Require
   evidence for each rather than treating all as benefits by default.
3. Identify forces favoring co-location: atomic invariants, chatty workflows,
   shared mutable data, and tightly coupled release contracts. Use the
   [boundary worksheet](references/boundaries.md).
4. Estimate added network round trips, serialization, operational ownership,
   failure cases, and migration work. Async communication changes coupling; it
   does not erase it.
5. Test whether the proposed boundaries permit independent deployment and failure.
   A service with its own process but a mandatory coordinated release is still
   coupled in the dimension that matters.
6. Select the smallest change that satisfies the actual quality goals. Record an
   ADR with alternatives, evidence, risks, and a condition for revisiting it.
7. Plan an incremental migration with a single authoritative writer at each step,
   reconciliation, compatibility, and rollback. Read [migration](references/migration.md).

## Check before approving

- Who owns writes to each entity, and where are multi-entity rules enforced?
- Does a new shared library force simultaneous deployments?
- Are derived data staleness and event-schema changes explicit?
- Can the critical flow proceed when an optional dependency is down?
- Will separate teams have monitoring, on-call ownership, and deployment capability?

## Output

Give a boundary map, forces/evidence table, invariant placement, failure timeline,
latency/cost estimate, selected alternative, migration stages, and revisit trigger.
Treat scorecards as decision aids; do not add ordinal ratings into a fake
objective optimum. Hard constraints can eliminate an otherwise attractive option.

## Scope and references

Partial coverage of *Software Architecture: The Hard Parts* (Ford, Richards,
Sadalage, Dehghani), using official Chapter 7, “Service Granularity,” and primary
architecture material. See [sources](references/sources.md). The worksheets and
scenarios are original; they do not reproduce the book's case studies.
