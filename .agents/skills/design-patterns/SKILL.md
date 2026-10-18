---
name: design-patterns
description: "Select and review object design patterns from a concrete change pressure. Use when refactoring conditionals, creating related object families, adapting interfaces, composing behavior, or diagnosing overengineered abstractions."
---

# Design patterns through variation and contracts

## Find the variation before naming a pattern

Describe the current behavior, the change that is difficult, and the contract that
must remain stable. Trace a concrete caller. A named pattern is useful only when
its collaboration removes that difficulty at an acceptable cost.

## Procedure

1. Identify what varies: algorithm, object construction, interface, added behavior,
   lifecycle state, or notification. Keep a direct implementation as a comparator.
2. Choose the smallest collaboration that isolates the demonstrated variation.
   A function parameter may be enough; an interface need not require a class hierarchy.
3. For a family of related products that must remain compatible, consider Abstract
   Factory. Centralize family selection and prevent callers mixing products.
   Read [pattern selection](references/selection.md).
4. Specify ownership, errors, ordering, reentrancy, and lifecycle in interfaces.
   Substitutability includes behavior, not just matching method signatures.
5. Refactor in small steps under behavior tests. Add tests for alternate implementations,
   invalid combinations, and error paths. Use [original example](references/example.md).
6. Reassess indirection: if variation never materializes and navigation becomes
   harder, simplify. Do not introduce speculative extension points without a user.

## Review smells

- A global mutable Singleton hides dependencies and can couple tests and threads.
- A factory creates individually valid products that form an invalid family.
- A wrapper silently changes exception or transaction semantics.
- Observer callbacks run while the subject holds an internal lock or fail without
  a defined notification policy.
- A pattern name substitutes for an explanation of why the design is easier to change.

## Output

State change pressure → preserved contract → proposed collaboration → original
before/after example → costs → tests. Use pattern names as precise vocabulary,
not as an instruction to maximize classes or inheritance.

## Scope and references

Partial coverage aligned with *Design Patterns: Elements of Reusable Object-Oriented
Software*, 1st ed. (Gamma, Helm, Johnson, Vlissides). Directly checked material is
the official Abstract Factory excerpt and an interview with Gamma on interfaces
and composition. Other pattern choices are limited orientation, not a complete
conversion of all 23 patterns. See [sources](references/sources.md).
