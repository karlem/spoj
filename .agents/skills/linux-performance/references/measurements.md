# Match observations to hypotheses

## Start with low-overhead evidence

Read counters over an interval rather than treating cumulative totals as rates.
Document tool version, namespace, CPU count, and cgroup scope.

```sh
uptime
vmstat 1 5
mpstat -P ALL 1 5
pidstat -p PID -u -r -d -w 1 5
iostat -xz 1 5
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io
```

Replace `PID` with the process ID. These are bounded observations, not a recipe
to run indiscriminately. `sysstat` tools may be absent. Ignore historical first
reports when the tool reports since-boot averages; verify its actual behavior.

| Suspected constraint | Useful measurement | Important ambiguity |
| --- | --- | --- |
| CPU availability | Per-CPU busy time, runnable delay, cgroup `cpu.stat` deltas | Host idle time does not override quota; one thread can saturate one CPU |
| Memory capacity | Working set, major faults, reclaim, memory PSI, cgroup events | Page cache is reclaimable; RSS is not allocation rate |
| Storage | Request latency, queue depth, bytes/s, IOPS, app I/O spans | Buffered writes can defer cost; cache hits never reach the device |
| Network | RTT, retransmissions, loss, connection churn, NIC errors | Retransmission may reflect congestion, not only a faulty link |
| Lock contention | Wait duration, owner stacks, queue length | Spinning appears on CPU; sleeping does not |
| Connection pool | Wait histogram, active/idle count, timeout rate | More connections can overload the database |

## Container example

A service sees 60% host idle CPU, rising p99, and occasional one-second bursts of
runnable work. Its CPU quota allows one CPU of aggregate execution per period,
although several threads can run briefly on multiple CPUs. Once the quota is
used, they can all be throttled until replenishment. Compare `nr_throttled` and
`throttled_usec` deltas with incident intervals, quota/period configuration, and
request traces. Throttled-time accounting can differ across kernels and scopes;
do not equate it directly with user request delay or host utilization.

Possible fixes depend on evidence: reduce unnecessary CPU work, increase the
quota if capacity/cost permits, tune concurrency, or shed bursts. A lock-heavy
workload may become worse when threads are added. Check post-change p99 and
throughput at the original offered rate.

## Pressure stalls

Linux PSI reports time tasks are stalled for CPU, memory, or I/O. `some` indicates
at least some tasks stalled; `full`, where supported and meaningful for that
resource/scope, indicates all non-idle tasks stalled together. `avg10`, `avg60`,
and `avg300` are rolling percentages; `total` is cumulative microseconds. Compute
interval deltas when correlating a short incident. A pressure event is a symptom;
follow it to the responsible allocation, I/O path, or scheduling constraint.

## Counterexamples worth keeping

- One hot request key saturates one worker while average CPU looks healthy.
- A downstream timeout holds all connections; CPU usage falls as latency rises.
- A benchmark gets faster because errors return immediately. Throughput counted
  as “requests completed” can improve while useful throughput collapses.
- System-wide counters mix a noisy neighbor with the target service. Narrow scope
  before attributing causality.
