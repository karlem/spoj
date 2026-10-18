---
name: network-engineering
description: "Analyze network latency, connection churn, throughput limits, stream framing, and unnecessary service hops. Use when debugging slow requests, comparing TCP and QUIC behavior, or reviewing application network paths."
---

# Network paths, latency, and transport

## Trace the application operation down the stack

Map DNS, connection setup, TLS, proxies/load balancers, application round trips,
transport delivery, and server queues. Record which connections are reused and
which steps are sequential. Distinguish propagation, transmission, queueing,
and processing delay. A hop count alone is not a latency model.

## Procedure

1. Define the endpoint, client location, payloads, rate, and warm/cold connection
   state. Measure end-to-end timing with matching request identifiers.
2. Split lookup/setup/handshake/request/body timing. Server spans alone omit client
   and network time; cross-host timestamp subtraction needs clock assumptions.
3. Inspect transport evidence: RTT, retransmissions, throughput, congestion/flow
   control, and connection churn. Use [path analysis](references/paths.md).
4. Estimate whether the path is RTT-bound, bandwidth-bound, loss/congestion-bound,
   or application-bound. Compute the bandwidth-delay product with consistent units.
5. Check stream framing and backpressure. TCP preserves an ordered byte stream,
   not message boundaries or durable application processing. Read
   [transport contracts](references/transports.md).
6. Compare pooling, batching, co-location, fewer serial calls, caching, or protocol
   changes against the actual constraint. Include failure and staleness costs.
7. For forwarding, LAN, wireless, or authentication symptoms, use the
   [layer checks](references/layers.md) to choose the responsible boundary.
8. Validate cold and reused connections, impaired paths, representative concurrency,
   errors, and tail latency. Do not call QUIC or a cache a universal latency fix.

## Review checklist

- Are serial remote calls on the critical path avoidable or batchable?
- Are pooled connections correctly reused and bounded?
- Can a proxy terminate/restart connections or buffer entire responses?
- Is the measured RTT representative of affected clients?
- Does packet capture include sensitive payloads, and is capture scope appropriate?
- Does an acknowledgment mean transport receipt or committed business effect?

## Output

Return path diagram, measured timing boundary, latency/throughput budget,
falsifiable hypotheses, smallest change, and validation under loss/load.

## Scope and references

Partial coverage aligned with *Computer Networking: A Top-Down Approach*, 9th ed.
(Kurose and Ross). Public author slides and current TCP/QUIC RFCs ground the
selected mechanisms. See [sources](references/sources.md). The layer checks are selective; full routing, wireless,
security, and link-layer coverage is not claimed.
