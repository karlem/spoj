# Build a latency and throughput budget

## Delay components

Propagation depends mainly on path distance/media. Transmission time for a payload
of `L` bits over rate `R` bits/s is `L/R`, before protocol overhead and contention.
Queueing depends on competing traffic and scheduling; it can dominate under load.
Processing includes hosts and intermediaries. Internet routes can change, and
ICMP traceroute responses are not a faithful measurement of application delay
at every hop. A hop that de-prioritizes diagnostic traffic may forward normally.

## Original latency example

Assume a persistent connection, negligible payload transfer, no additional TLS
setup, and five sequential service calls that each require a full 30 ms network
round trip. Their communication component is about 150 ms before server work and
queueing. Batching into one remote operation can remove four round trips under
these assumptions. Parallel calls help only if independent; transactions and data
dependencies can require serial order.

For cold requests, DNS, transport handshake, and cryptographic setup may add
additional round trips. Actual TLS versions, connection resumption, preconnect,
proxy topology, and protocol choices change this budget. Measure rather than
blindly attaching a fixed number of RTTs to every request.

## Bandwidth-delay product

A path of 100 Mbit/s and RTT 80 ms has BDP
`100,000,000 bit/s * 0.080 s = 8,000,000 bits = 1,000,000 bytes`.
Roughly that much data must be in flight to fill the path in an idealized single
flow. Throughput can be limited by the congestion window, receive window,
application production/consumption, pacing, packet loss, or other bottlenecks.
A larger application buffer does not automatically increase the congestion window.

A 64 KiB effective in-flight limit over 80 ms gives an idealized bound near
`65,536 / 0.080 = 819,200 bytes/s`, below path capacity. This is a diagnostic model,
not a prediction that ignores ACK behavior, overhead, competing flows, and loss.

## Measurement matrix

| Observation | Plausible cause | Discriminating follow-up |
| --- | --- | --- |
| Cold much slower than warm | DNS/setup/TLS or cold server state | Separate phase timings and connection reuse |
| RTT stable, app latency grows | Server/pool/proxy queues | Compare spans and queue measurements |
| Throughput plateaus below link rate | In-flight limit, loss, app bottleneck | Transport counters plus CPU and receiver progress |
| Many tiny serial calls | Chatty application protocol | Trace critical path; test batching |
| Retransmissions increase | Congestion/loss/reordering conditions | Correlate path, queue, NIC, and capture evidence |

## Engineering exercise

A report recommends doubling NIC speed for a request that sends 2 KiB but performs
six serial RPCs across regions. Estimate transmission cost versus measured RTTs,
then test batching or data locality before changing hardware. Include the
consistency/ownership cost of relocating data; a latency win may alter failure
and staleness behavior.
