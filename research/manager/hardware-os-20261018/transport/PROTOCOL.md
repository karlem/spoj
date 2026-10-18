# Preregistered local transport mechanism experiment

Task `hardware-os-20261018-1801/D7-transport`; issue #9; author worker
`/root/hardware_transport`; base 72219b9b4ba769e8d1f88454953d191684355adc.
The parent manager owns issue/queue records and integrated product checks.
Protocol frozen in git before compilation or any timed experiment.

Question: how much does selecting an existing local IPC transport change matched
request/echo/verification cost in this VM? TCP loopback with TCP_NODELAY is the
simple baseline; AF_UNIX SOCK_STREAM is the strongest feasible standard local
socket alternative for this controlled comparison. This is a measurement task,
with no predicted winner or inference performance threshold.

Two processes, one persistent connection per process session. The child echoes
exactly the request length; the parent verifies the entire response against a
preallocated deterministic byte pattern with a sequence tag. Only one request is
outstanding. Time CLOCK_MONOTONIC around complete send, complete receive and memcmp.
Exclude and separately report listener creation, fork and client connection setup.
Sequence tag generation occurs before timing; verification remains inside timing.
Allocate buffers before setup/timing. No external code or downloads.

Five pairs, order TCP/UNIX, UNIX/TCP, TCP/UNIX, UNIX/TCP, TCP/UNIX. Each process
session tests payloads in fixed order 128 B, 16 KiB, 1 MiB, with two warmups for each
and respectively 128, 16, 2 measured requests. Warmups retained and marked. All
buffers and pages are touched by filling before requests; no cache flush, host
changes, affinity change, or synthetic sleeping. Tiny counts for large payloads
are intentionally not used for tail percentiles. Pair-session median RTTs and
per-request raw times are descriptive; no statistical or physical-network claim.

Byte accounting per session, request direction:
128*(128+2) + 16384*(16+2) + 1048576*(2+2) = 4,505,856 B.
With echoes = 9,011,712 B/session. Ten sessions = 90,117,120 B
(85.9423828125 MiB). One negative test adds 128 B request + 128 B corrupt echo,
for total 90,117,376 B application payload, below 100 MiB. TCP framing/ACK/kernel
copies are not counted or measured; this is application traffic accounting, not
physical wire accounting. Logs and source are expected <1 MiB; no model data.

Negative control: a separate TCP process session sends one 128-byte request; the
server deliberately flips one response byte. The client must reject it with exit
42, and the child must exit 0. Retain raw log and exits. Positive acceptance:
1520 total successful requests (10*(130+18+4)), all whole-response comparisons
pass, 10 parent and child exits 0, exact payload accounting, raw paired measurements.
Failure invalidates timing evidence, with at most two failed attempts. No selection
of best runs or silent discarded failures. Negative corruption rejection is expected,
not a failed worker attempt.

Each harness child inherits RLIMIT_AS 256 MiB, RLIMIT_CPU 30 s, RLIMIT_FSIZE 16 MiB,
no core dumps; each socket gets 5 s send/receive timeout; each process session has
an outer Python 20 s timeout; entire driver has timeout 280 s (hard kill 5 s later).
Driver will kill the whole session process group after timeout to bound descendants.
The entire run has <300 s, <2 GiB, <100 MiB resource budget. These bounds govern this
experiment, not resource use by other agents sharing this host.

Record source hashes, gcc/kernel/Python/cgroup quota/CPU affinity, socket buffers,
parent/child rusage, timings and errors. Summaries use no tail percentile claims or
assumed conversion to end-to-end inference gain. A hypothetical 20% end-to-end OS
improvement target cannot be evaluated from a socket timing ratio. No physical NIC,
optical cable, GPU, inference model, or remote machine is exercised.
