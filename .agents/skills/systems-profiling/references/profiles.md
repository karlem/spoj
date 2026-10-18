# Interpreting profiles without inventing causality

## Original example: a disappearing hotspot

Baseline: 400 useful requests/s uses 2 CPU-seconds per second, with 40% of samples
in JSON encoding. Candidate: 400 requests/s uses 1.2 CPU-seconds per second, with
60% in JSON encoding. Encoding's approximate absolute CPU consumption changed
from 0.8 to 0.72 CPU-seconds/s, despite the larger percentage. Another path became
much cheaper. Percentages are compositional; every profile sums to 100% even
when total resource demand changes.

A differential flame graph is useful only when its normalization matches the
question. Equal sample counts emphasize distribution; equal wall intervals and
comparable sampling expose absolute changes, subject to sampling coverage.
Include throughput, total CPU, and profiling configuration alongside the graph.

## CPU versus waiting

Suppose an endpoint takes 200 ms, of which 8 ms runs on CPU and 180 ms waits on a
connection pool. Optimizing the widest CPU frame may save microseconds while
the user-facing tail remains. Measure pool acquisition, downstream time, and
queue depth. An off-CPU stack tells where a thread stopped running; it can include
sleep, I/O, and synchronization. It is not automatically the identity of the
resource owner causing the wait. Runnable scheduling delay is also different
from blocked time.

For asynchronous runtimes, one worker thread executes many logical requests. A
thread stack may stop at the event loop. Use runtime-aware task attribution or
application spans to connect suspension to the logical request. Avoid attributing
all event-loop idle time to every active request.

## Capture quality checklist

| Problem | Consequence | Follow-up |
| --- | --- | --- |
| Missing user symbols | Work appears as unknown addresses | Match symbols/build IDs to the deployed binary |
| Broken stack unwinding | False shallow hotspots | Check frame pointers or supported DWARF/runtime unwinding |
| Lost samples/events | Biased proportions or missing sequences | Inspect loss counters; reduce event rate/scope |
| Periodic sampling synchronized with work | Aliasing | Vary frequency or compare another event/source |
| Too short a capture | Rare expensive paths absent | Extend representative observation, within overhead budget |
| System scope instead of process scope | Neighbor work mixed in | Narrow PID/cgroup/namespace where supported |

Inlining can fold source functions into callers; source-line attribution depends
on debug data. Hardware event counts may be multiplexed or scaled. Raw IPC across
machines is not a portable ranking: instruction mix, vectorization, memory stalls,
and processor design differ.

## Reviewer exercise

A report says “the tallest stack is slowest; remove three layers.” Correct it:
height reflects depth; width reflects aggregate event weight. Identify whether
those layers do work or merely call a hot leaf. Require a profile-backed mechanism
and a benchmark at the relevant load before approving a rewrite.
