# Select a style by a falsifiable goal

## Original quality scenarios

| Goal | Concrete scenario | Evidence |
| --- | --- | --- |
| Performance | At 1,500 admitted requests/s with stated payloads, p99 < 200 ms | Representative workload test with errors and queue growth |
| Recoverability | Restore a production-sized backup within 45 minutes, losing at most 5 minutes of accepted data | Timed restore and reconciliation drill |
| Modifiability | Add a payment provider without changing inventory rules | Change-impact review and contract tests |
| Isolation | One tenant's report cannot consume all checkout capacity | Adversarial load and resource/admission measurements |

These values are scenario parameters, not recommendations. A quality requirement
without an environment and measure cannot decide among architectures reliably.

## Candidate mechanisms

| Style | Useful when | Mechanism | Costs to test |
| --- | --- | --- | --- |
| Modular monolith | A team needs local transactions and simpler deployment | In-process interfaces plus enforced module/data ownership | Shared deployment and runtime failure domain |
| Layered design | Responsibilities fit a stable dependency direction | Separate policy/application/data concerns | Pass-through layers, cross-layer changes, bypasses |
| Microkernel | A stable core supports many optional extensions | Explicit plug-in contracts | Extension lifecycle, compatibility, trust/isolation |
| Coarse services | A few capabilities need separate operations | Explicit APIs and deployment/data owners | Network failures, contract migration, cross-service invariants |
| Event-driven integration | Producers and consumers can tolerate decoupled time | Durable event contracts and asynchronous processing | Lag, ordering, duplicate effects, observability |
| Microservices | Multiple capabilities have demonstrated independent evolution/scale needs | Autonomous ownership and deployment with bounded contracts | Operational overhead, distributed data correctness, team capacity |

The styles can combine. A service may contain layers and plug-ins, while publishing
events. A diagram of containers is not enough: describe the dependency direction,
transaction ownership, and runtime behavior that makes the selected style useful.

## Avoid metric theater

Static coupling and cohesion metrics can highlight candidates for investigation.
They do not measure business alignment automatically. High fan-in to a stable
interface can be appropriate; high fan-in to frequently changing details is riskier.
A dependency cycle may signal unclear boundaries, but eliminating it through a
meaningless interface can improve the graph without improving the design.

Interpret change coupling using repository history and workflow knowledge. Files
changed together because of a mechanical formatting commit do not necessarily
belong in the same domain module. Independent repositories do not prove low
coupling if releases still require coordination.

## Architecture review exercise

A six-person team with one on-call rotation proposes 18 microservices to “be
scalable.” The current bottleneck is one expensive SQL query. Ask for workload
measurements and release/change evidence. A better initial candidate may optimize
the query and enforce domain modules in the existing deployment. Revisit extraction
when a capability requires independent scale, isolation, or release ownership and
the team can operate it. This is a conditional choice, not a prohibition on services.
