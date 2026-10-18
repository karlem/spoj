# Attempts

Attempt 1 at frozen source 6ef280b: compile failed before any timed harness execution.
GCC -Werror=stringop-overflow objected to `server[sizes[p]-1]` in the
negative-control branch, despite its one-payload loop. Raw compiler evidence is
in raw-attempt1/compile.json; driver exited 1.

Attempt 2 changes only that corruption index to explicit 127, which is the last
byte of the predeclared negative control's fixed 128-byte payload. This preserves
the protocol, limits, and correctness invariant. Frozen before retry.
