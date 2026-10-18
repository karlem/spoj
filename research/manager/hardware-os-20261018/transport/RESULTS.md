# Local transport mechanism result — REVIEW

Task `hardware-os-20261018-1801/D7-transport`, issue #9. Author
`/root/hardware_transport`, branch `research/hardware-transport-20261018`.
Measured on 2026-10-18 18:06:54 UTC. Protocol commit `7d0e113`; successful timed
source revision `2a02ae97421521848f333c5550fbac74f3b209bf`. Compiler failure at the
previous source revision is retained; second attempt passed. No further attempts.
Independent validation is pending; this report does not self-approve the evidence.

**The existing transport choice changes localhost request cost, but this small
shared-VM test does not establish a stable winner or an inference bottleneck.**
All 1,520 positive whole-response comparisons passed, with all ten positive client
and server processes exiting 0. Deliberate corruption was rejected with client
exit 42 and server exit 0. The aggregate application echo payload was exactly
90,117,376 bytes (85.942626953125 MiB), including warmups and the negative control.
No external network, GPU, physical NIC, optics, or model inference was exercised.

## Paired raw summary

Each entry is TCP / AF_UNIX median request+echo+whole-response-verification time
in microseconds within one process session. Each 128 B cell has 128 measured
requests, each 16 KiB cell has 16, each 1 MiB cell only 2. Two warmups precede each
payload and are retained in the raw JSONL files but excluded from these medians.

| Pair | Execution order | 128 B, us | 16 KiB, us | 1 MiB, us |
|---|---|---:|---:|---:|
| 1 | TCP then UNIX | 19.0385 / 15.3880 | 20.5610 / 16.6800 | 211.9680 / 223.8460 |
| 2 | UNIX then TCP | 14.1110 / 15.2780 | 15.8685 / 16.8550 | 154.4715 / 259.0680 |
| 3 | TCP then UNIX | 21.3920 / 11.0465 | 24.3815 / 11.9080 | 214.1610 / 95.5480 |
| 4 | UNIX then TCP | 14.0460 / 15.2730 | 15.7385 / 16.8150 | 258.0825 / 196.2690 |
| 5 | TCP then UNIX | 21.4075 / 11.0215 | 24.6020 / 11.6470 | 323.9960 / 114.9175 |

For 128 B and 16 KiB, the apparent winner changes with execution order: UNIX has
the lower median in all three TCP-first pairs; TCP has the lower median in both
UNIX-first pairs. This is evidence against interpreting the pooled ratio as a
transport improvement. CPU placement, scheduler state, warming, and shared-host
contention are plausible confounders, not established explanations. The 1 MiB
sample is too small for tail claims and varies markedly. No significance or
speedup claim is made.

Setup (listener/fork/connect; before warmups) ranged 351.297–625.368 us for positive
TCP sessions and 69.975–112.949 us for UNIX. These are separately reported costs,
not part of persistent-connection RTT; server accept completion is not explicitly
barrier-synchronized with setup timing. Initial scheduling is absorbed by warmup.
TCP_NODELAY is enabled at both TCP endpoints. Default socket buffers differ;
client buffer values are retained per session rather than tuned or equated.
The workload measures this standard configuration choice, not an isolated count
of TCP instructions. Kernel buffering, copies, process scheduling, user-space
verification, and timer overhead all contribute to RTT. No component fraction
has been causally attributed.

## Environment and enforcement

Linux 6.18.55 x86-64, GCC 14.2.0, Python 3.12.14. Exposed model string AMD EPYC
9V45 96-Core Processor; process affinity CPUs 0–4; cgroup CPU quota 400000/100000,
i.e. four CPU-equivalents. This is a shared virtualized environment, not five
dedicated physical cores. The harness uses two processes and preallocates three
1 MiB buffers before setup. Child writes can still incur copy-on-write minor
faults after fork; two warmups touch each active region before measured requests.
Rusage is retained for parent and child separately.

Each harness process has 256 MiB address-space and 30 s CPU limits, with 5 s socket
timeouts. Driver imposes a 20 s session timeout and process-group kill; child also
uses parent-death SIGKILL. Whole driver outer timeout is 280 s with 5 s kill grace.
Only the bounded two-process harness is given address-space/CPU limits; GCC and
the stdlib driver are not independently RLIMIT_AS-constrained. Their input and
logs are fixed and small; successful compilation and all sessions completed in
under one second as observed by the execution wrapper. This is disclosed rather
than asserting a kernel-enforced global memory cap. Source/log files are under
1 MiB; payload accounting counts each request and echo once, not TCP headers,
ACKs, retransmissions, or internal memory copies. No physical wire-byte claim.

## Decision and next experiment

Recommendation: **UNRESOLVED** for any inference-performance or custom-OS claim;
retain this as a correctness-checked mechanism baseline pending independent review.
It supports testing ordinary local IPC configurations before writing a new OS,
but it does not establish that socket work consumes a useful fraction of an agent
workload. An assumed 20% end-to-end target cannot be evaluated from these ratios.

Next smallest assignment: on an available inference host, trace one fixed real
agent tool-wait workload with model/prompt/output policy held constant. Account
separately for prefill, decode, tool waits, IPC, KV copies, and accelerator idle time.
Only if IPC is a material measured fraction should a same-workload existing IPC
intervention be tested; require matched outputs and a predeclared end-to-end
latency or throughput threshold. Physical NIC/cable or distributed-GPU comparisons
need actual devices and topology-specific traffic, not this loopback result.
