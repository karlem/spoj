---
name: architecture-patterns
description: "Choose architecture styles from measurable quality requirements. Use when comparing a modular monolith, service-based design, microkernel, event-driven architecture, or microservices, and when turning decisions into fitness checks."
---

# Architecture selection and fitness checks

## Translate goals into observable behavior

Identify actors, critical workflows, data ownership, and constraints. Convert
“scalable,” “secure,” and “maintainable” into scenarios: stimulus → environment →
response → measure. Rank the few characteristics that materially determine the
design. Distinguish mandatory constraints from preferences.

## Procedure

1. Define quality scenarios and acceptance thresholds with stakeholders. State
   workload, failure, and team assumptions. Use [selection](references/selection.md).
2. Identify the scope at which each property must hold: component, deployment,
   workflow, or whole system. Different parts may justify different styles.
3. Compare a small set of feasible styles against those scenarios, including a
   modular single deployment. Explain the mechanism supporting each claimed benefit.
4. Examine coupling: source dependencies, runtime calls, shared data, and coordinated
   changes. Static module independence does not prove runtime failure isolation.
5. Choose the simplest viable style and record an ADR, consequences, and a trigger
   for reconsideration. Keep reversible implementation details separate from costly
   structural commitments.
6. Turn critical decisions into fitness checks: prohibited dependencies, contract
   compatibility, latency budgets, restore time, and tenant isolation. Use
   [fitness checks](references/fitness.md).
7. Re-evaluate under observed load and change patterns. A passing dependency rule
   is evidence for one property, not overall architecture quality.

## Review questions

- Does a plug-in boundary solve actual extensibility needs without granting
  every plug-in unrestricted access to the core?
- Do events need durable publication, schema compatibility, deduplication, and lag
  monitoring? Are these costs included in the event-driven proposal?
- Does separate deployment improve a measured bottleneck or release constraint?
- Can the proposed team operate the resulting deployment and failure complexity?
- Which invariant becomes harder when data ownership splits?

## Output

Return quality scenarios, candidate mechanisms/trade-offs, chosen structure,
ownership/dependency map, ADR, fitness checks, and unresolved assumptions.

## Scope and references

Partial coverage aligned with *Fundamentals of Software Architecture*, 2nd ed.
(Richards and Ford). Author material, a public author interview transcript,
publisher contents, and architecture-test documentation ground this original guide.
See [sources](references/sources.md). No style is a universal maturity stage.
