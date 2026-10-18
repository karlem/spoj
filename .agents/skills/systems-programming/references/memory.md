# Representation, lifetime, and locality

## Guard arithmetic before allocation

Original C example:

```c
#include <stddef.h>
#include <stdint.h>

int checked_bytes(size_t count, size_t width, size_t *out) {
    if (width != 0 && count > SIZE_MAX / width) return 0;
    *out = count * width;
    return 1;
}
```

The caller supplies a valid writable `out` pointer. This checks representability,
not whether memory is available or whether an application limit permits the
allocation. Validate a signed input as nonnegative before converting to `size_t`.
If zero-byte allocations are meaningful, define their semantics separately.
Checking `count * width > SIZE_MAX` after multiplication cannot detect unsigned
wraparound, since the computed result is already reduced modulo the type's range.
Signed overflow in ordinary C arithmetic is undefined, rather than guaranteed
wraparound. Compiler optimization can exploit that distinction.

## Ownership ledger

| Object | Owner | Valid lifetime | Who may mutate? | Release path |
| --- | --- | --- | --- | --- |
| Request buffer | Parser/request | Until callback completes | Parser before publication | Request cleanup |
| Borrowed slice | No independent owner | No longer than backing buffer | Per API contract | No independent free |
| Shared cache entry | Cache protocol | Until last protected reader releases | Under synchronization | Eviction/reclamation protocol |

A pointer's non-null value does not prove validity. A `realloc` failure leaves the
original allocation valid; assigning directly over the only pointer can leak it.
A successful `realloc` can invalidate old aliases. Returning a pointer to a local
array leaves a dangling pointer. Freeing memory under a mutex is not enough if a
reader retains an unprotected pointer after releasing that mutex.

## Locality example

For a C row-major matrix `a[rows][cols]`, iterating columns inside rows usually
visits adjacent elements. Reversing loop order can jump by an entire row on each
access. Both orders are `O(rows * cols)` but can have different cache/TLB behavior.
The benefit depends on dimensions, caches, prefetching, layout, vectorization,
and aliasing. Benchmark representative sizes, including a working set larger
than the relevant cache, and verify the result so work is not optimized away.

False sharing occurs when independent frequently written data share a coherence
unit. It is not a language data race if each thread owns its object, but cache
line bouncing can hurt scaling. Measure contention and layout before padding;
padding increases footprint and the relevant cache-line size is platform-specific.

## Debugging sequence

1. Compile with useful warnings and debug information.
2. Use AddressSanitizer/UndefinedBehaviorSanitizer where supported for targeted
   repros; use a separate ThreadSanitizer build for races where appropriate.
3. Minimize the failing input and preserve the failure under the relevant build.
4. Check arithmetic and ownership contracts before blaming the allocator/compiler.
5. Recheck correctness at optimized settings, then measure performance separately.

Exercise: a signed client length is `-1`, then cast to `size_t` for `memcpy`.
Explain why a non-null destination and an overflow-safe allocator do not make the
copy safe. Validate length, capacity, and initialized source extent together.
