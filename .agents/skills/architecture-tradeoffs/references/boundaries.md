# Boundary worksheet

## Original scenario: checkout and recommendations

Checkout's stock reservation and order acceptance must obey a stock invariant.
Recommendations can be stale and unavailable. A proposal splits validation,
reservation, order creation, and recommendations into four synchronous services.

| Force | Evidence to gather | Boundary implication |
| --- | --- | --- |
| Independent change | Commits and releases that change only one capability | Supports separate ownership when contracts remain stable |
| Uneven scaling | CPU/I/O demand and peak rate per capability | Separate deployment may reduce cost; measure shared bottlenecks |
| Security | Actual privilege/data boundary | Separate credentials and policy can justify process isolation |
| Atomic business rule | Data and predicates changed together | Keep transaction local or design an explicit coordinated protocol |
| Chatty workflow | Traces showing calls, payloads, and round trips | Coarser API or co-location may reduce latency and failure surface |
| Shared state | Multiple services updating the same tables | Independent deployability is questionable until ownership is resolved |

Do not infer that stock and order *must* always be one service. They may use a
reservation protocol with expiry and reconciliation. That is a change in business
semantics and operational complexity, not just moving functions over HTTP.
Recommendations have a plausible separate failure boundary because checkout can
use an explicit empty/default result without breaking order correctness.

## Quantify latency and availability carefully

For sequential remote calls, added communication latency is approximately the
sum of critical-path round trips and serialization, under the stated reuse and
queueing assumptions. Parallel calls replace a sum with a maximum only for the
parallel portion; fan-out tail behavior and shared dependencies still matter.
Do not sum independent component p99s and call the result an end-to-end p99.

Multiplying dependency availabilities is a rough model only when failures are
independent and every dependency is mandatory. Shared networks, databases, and
regions create correlated failures. Use real failure domains and critical paths
rather than quoting a precise reliability number from an unsupported model.

## Review anti-patterns

- **Distributed monolith:** deployment units remain lockstep because contracts,
  shared writes, and synchronous assumptions are unchanged.
- **Table-per-service thinking:** a schema entity is not automatically a business
  capability; the invariant may span several tables.
- **Async as a cure:** asynchronous work needs event contracts, retry policy,
  observability, deduplication, and lag handling.
- **Pure scorecard selection:** a weighted score cannot compensate for violating
  a mandatory regulatory or correctness requirement.

## ADR skeleton

```text
Decision and scope:
Required invariant and quality targets:
Current measured problem:
Alternatives (including improving the current system):
Evidence and assumptions:
Selected boundary and data owner:
Failure and recovery behavior:
Costs, reversibility, migration stages:
Revisit when (observable condition):
```

Exercise: if all four proposed services must deploy together to change the
checkout schema, identify which coupling remains and propose a contract migration
that permits staggered deployments. A new repository per service is insufficient.
