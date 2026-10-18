# What transport guarantees stop short of

## TCP

TCP provides reliable, in-order byte-stream delivery while the connection remains
viable. It does not preserve application messages. A send/write can complete
locally before the peer application has read, validated, or committed anything.
A transport acknowledgment is not a database commit acknowledgment. If the
connection fails after a request was sent, the application may not know whether
the effect happened.

Frame the application protocol: fixed length, delimiter with escaping, or a
length-prefixed format with strict bounds. Parse incrementally, enforce limits
before allocation, distinguish EOF from a complete message, and apply deadlines
and backpressure. A slow reader can fill buffers even when packet delivery works.

TCP loss recovery can hold later bytes behind missing bytes in the same stream.
Multiplexing several application streams over one TCP byte stream can therefore
couple their delivery during loss. Application protocols and connection pools
change how visible that coupling becomes.

## QUIC

QUIC provides multiple streams over a connection, with reliable ordered delivery
within each stream. Loss affecting one stream need not block delivery on another
stream for the same in-order byte-stream reason as TCP. Streams still share path
capacity and congestion-control effects; QUIC does not eliminate all head-of-line
blocking or latency coupling. Protocol choice must also account for deployment,
UDP reachability, server/client support, and processing costs.

Flow control limits what the receiver is prepared to accept; congestion control
adapts traffic to network conditions. Increasing one does not remove the other.
Connection reuse avoids repeated setup but long-lived connections still require
idle timeout, draining, failure, and resource policies.

## Layer responsibilities

| Layer | Example guarantee or mechanism | Application responsibility remaining |
| --- | --- | --- |
| Transport | Ordered bytes/streams, loss recovery | Framing, validation, operation identity |
| TLS/security integration | Peer authentication and encrypted channel under its configuration | Authorization, business validation, secret handling |
| Broker | Durable delivery under its own configured contract | Atomic effects, duplicate handling, replay policy |
| Database | Selected transaction/durability guarantees | Correct invariant boundaries and external effects |

## Validation exercise

A team says “TCP is reliable, so our payment POST needs no idempotency key.” Show
a timeline: server commits, response is lost, client reconnects and retries. TCP
reliability did not tell the new connection whether the prior business effect
committed. Define a stable operation identity and documented reconciliation
contract at the application layer.
