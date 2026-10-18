# Deadline and retry budget

## Original scenario: the charged-but-timed-out request

An API accepts an operation key, calls a payment provider, then loses the response.
The caller times out after the provider has committed. Retrying under a new key can
charge again. A retry is safe only if the provider durably recognizes the same
operation within its documented retention/parameter rules, or the application can
reconcile the outcome before repeating the effect. An HTTP method name alone is
not evidence that an arbitrary business action is replay-safe.

| Outcome | Retry consideration |
| --- | --- |
| Validation/auth failure | Fix the request/credentials; repeated identical calls rarely help |
| Explicit transient failure | Retry only within policy, load budget, and remaining deadline |
| Timeout/connection lost after send | Outcome may be unknown; preserve operation identity |
| Overload/throttle | Honor documented hints, limit attempts, spread traffic, reduce admission |
| Deadline exhausted | Stop new attempts and cancel work where supported |

## Amplification

If five layers each make up to three total attempts, one logical request can cause
`3^5 = 243` leaf attempts in the worst case. Distinguish “three retries” (four
attempts) from “three attempts.” Backoff changes timing, not the maximum count.
Avoid retrying in multiple layers unless their combined budget is deliberate.

Use a budget relative to original admitted work and a cap on concurrent attempts.
Retries must not starve first attempts. Hedged requests also multiply resource use
and are inappropriate for non-idempotent effects without a safe contract.

## Backoff and deadline sketch

For retry index `i`, a full-jitter delay can be sampled uniformly from
`[0, min(cap, base * 2^i)]`. This is a policy example, not a universal optimum.
Clamp arithmetic to avoid overflow, bound attempts, and do not sleep if delay plus
a useful attempt cannot fit the remaining deadline. Use a monotonic elapsed-time
source for local deadlines. A propagated deadline needs a defined cross-host
representation and clock-skew handling.

Connection setup, TLS, DNS, pool acquisition, and body consumption may have
separate timers. Check what the client actually includes in “request timeout.”
A peer that sends occasional bytes may evade a per-read timeout indefinitely
without a total deadline.

## Test protocol

- Return a transient error twice, then succeed; verify total attempts and key reuse.
- Commit the side effect but drop its response; verify reconciliation/no duplicate.
- Return persistent overload; verify bounded attempts and actual reduced traffic.
- Delay pool acquisition; verify total request deadline includes the wait.
- Cancel during backoff; verify no later attempt starts.
- Recover many clients simultaneously; measure jitter, probe rate, and pool occupancy.

Record admitted logical requests separately from physical attempts and successful
business effects. Otherwise a retry storm can masquerade as increased throughput.
