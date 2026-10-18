---
name: systems-programming
description: "Review C and POSIX code for integer overflow, memory lifetime, partial I/O, process behavior, and cache locality. Use when debugging corrupt data, intermittent I/O failures, or low-level performance regressions."
---

# Systems programming and machine costs

## Review from contracts to machine behavior

State the language/version, target ABI, integer widths, ownership, threading,
and syscall contracts. Separate a C-language guarantee from a common Linux/x86-64
observation. Code that works at one optimization level may still be undefined.

## Procedure

1. Trace values across parsing, signed/unsigned conversions, arithmetic, allocation,
   indexing, and serialization. Check overflow *before* the operation. Use the
   [memory and representation guide](references/memory.md).
2. For each pointer, identify allocation, capacity, initialized extent, owner,
   aliases, and lifetime. Check error paths and ownership transfer.
3. For I/O, handle short transfers, interruption, EOF, and nonblocking readiness
   explicitly. A successful `read` or `write` need not transfer the requested
   length. Use [I/O contracts](references/io.md).
4. For processes and signals, check descriptor inheritance, child reaping, signal
   safety, and races between checking state and waiting. Signals are not a general
   replacement for a durable work queue.
5. For performance, measure locality and work before rewriting instructions.
   A stride across rows can miss caches even when algorithmic complexity is
   unchanged. Inspect generated code only after the program's semantics are sound.
6. Validate with warnings, sanitizers, boundary inputs, fault injection, and
   representative benchmarks. A sanitizer passing does not prove absence of bugs.

## Code review questions

- Can `count * element_size` wrap before allocation?
- Does a negative length become a huge `size_t`?
- Is a buffer used after free or after its stack frame ends?
- Does a file-descriptor number get reused while another component still owns it?
- Can a network request be split across reads or coalesced with another request?
- Does an optimization change aliasing, overflow, alignment, or data-race behavior?

## Output

Give the violated contract, smallest triggering input/interleaving, fix, test,
and assumptions about platform behavior. Preserve return/error semantics while
optimizing; avoid “faster” code that silently accepts truncated data.

## Scope and references

Partial coverage aligned with *Computer Systems: A Programmer's Perspective*,
3rd ed. (Bryant and O'Hallaron). Author companion resources orient the topics;
POSIX specifications verify I/O contracts. See [sources](references/sources.md).
Examples are original and target the declared subset; this is not coverage of
all processor, linker, or virtual-memory mechanisms in the book.
