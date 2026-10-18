# Select a collaboration, then justify it

## Variation guide

| Demonstrated change pressure | Candidate | Simpler comparator | Cost to inspect |
| --- | --- | --- | --- |
| Swap one algorithm behind a stable operation | Strategy | Pass a function | More types/configuration; behavior still needs a contract |
| Construct compatible product families | Abstract Factory | One constructor for a complete family | Adding a new product kind changes every family provider |
| Translate one existing interface | Adapter | Local conversion function | Semantic/exception mismatch can remain hidden |
| Add behavior around an existing operation | Decorator | Explicit wrapper function | Ordering and state-sharing become harder to inspect |
| Treat a tree of parts uniformly | Composite | Direct tree traversal | Some operations may not make sense on both leaves and groups |
| Change behavior with lifecycle state | State | Explicit transition table | Transitions and shared data can scatter across objects |
| Notify dependents of changes | Observer | Explicit calls for a few fixed dependents | Lifetime, reentrancy, ordering, and error propagation |

Only Abstract Factory is directly grounded in the fetched book excerpt. The other
rows are narrow engineering orientation around the broader vocabulary, informed
by the author's public interface/composition discussion. Consult the full book or
additional primary documentation for complete pattern-specific treatment.

## Abstract Factory trade-off

Select a factory once for a family, then construct the related products through
that factory. The key value is compatibility of the family as well as hiding
concrete constructors. If every caller can choose each product's family separately,
the abstraction may fail to enforce its main invariant.

Adding a new family can be localized to a provider. Adding a new product kind to
the factory interface usually requires updating all existing providers. This
asymmetry matters: use the pattern when families vary more often than product
kinds, or when compatibility justifies the interface cost.

“Program to an interface” means use a stable behavioral contract. It does not
require inventing a language-level `interface` for every concrete class. A
function signature, protocol, or existing abstraction may already express the
contract. Avoid interfaces that simply duplicate implementation details.

## Composition review

Composition lets an object delegate selected behavior rather than inherit an
entire implementation/lifecycle. It can make changes more local, but wrappers can
still violate contracts. Check whether retries happen once or twice after adding
a decorator, whether exceptions remain meaningful, and whether wrapper order is
observable. A logging wrapper must not consume a stream needed by the caller.

## Refactoring exercise

A file exporter chooses CSV versus JSON with one small branch and has no shared
lifecycle. Compare a dictionary of format functions with an exporter hierarchy.
If later each format needs coordinated writer, schema, and validator objects,
consider a family constructor/factory. Explain what new requirement earns the
additional structure rather than choosing a pattern based on line count.
