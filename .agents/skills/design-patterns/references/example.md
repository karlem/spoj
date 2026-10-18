# Original example: compatible document bundles

A reporting tool supports compact and accessible rendering. Each family supplies
a renderer and a style configuration. Mixing an accessible renderer with a compact
style is invalid. One family selection should produce the whole bundle.

```python
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Bundle:
    family: str
    render: Callable[[str], str]
    line_spacing: int


def create_bundle(family: str) -> Bundle:
    if family == "compact":
        return Bundle("compact", lambda s: f"<small>{s}</small>", 1)
    if family == "accessible":
        return Bundle("accessible", lambda s: f"<p>{s}</p>", 2)
    raise ValueError(f"unsupported family: {family}")
```

This is intentionally a small family constructor, not a class-heavy implementation
of the full GoF collaboration. It demonstrates the compatibility boundary with the
least machinery. In a larger system, separate provider objects can implement a
shared factory contract. Keep creation at the composition root, inject the bundle
into callers, and avoid a global factory that can change while a request runs.

The example assumes trusted text and is not an HTML-sanitization library. A real
renderer must implement the target format's escaping and accessibility requirements.
No claim is made that one `<p>` tag makes a document accessible.

## Tests that earn their cost

- Selecting each family produces its corresponding rendering and style together.
- Unknown families fail before a partly constructed bundle escapes.
- Callers use the bundle contract without inspecting concrete provider types.
- A new family satisfies the same behavioral tests.
- If products have resources, partial construction closes already-created resources.

A factory interface can permit invalid mixing if products are later passed around
independently. Keep family identity in a bundle, enforce it through types where
practical, or validate at assembly boundaries. Naming a function “factory” does not
provide this guarantee.

## Review exercise

A refactor introduces five interfaces, a global registry, and reflection to replace
two constructors. The only supported variation is selecting one renderer function.
Ask which caller change becomes easier and which invariant is newly protected.
Keep the function-based solution if the additional framework has no demonstrated
benefit. Revisit when plug-in discovery or coordinated product families become
real requirements.
