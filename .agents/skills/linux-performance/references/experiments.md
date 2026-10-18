# Validate a performance change

## Define success before measuring

Original example: a checkout endpoint must sustain 800 offered requests/s with
p99 below 150 ms, error rate below 0.1%, and no growing queue over 20 minutes.
These are scenario targets, not universal defaults. Include CPU cost per useful
operation and downstream resource cost so a local speedup cannot hide a fleet
regression.

1. Fix dataset size, key skew, payloads, dependencies, build flags, CPU allocation,
   and cache state. Record the version and machine class.
2. Choose a load model. A closed-loop client waits for responses before issuing
   more work; as latency rises it can reduce offered load and understate tails.
   An open-loop schedule can reveal this but must record scheduling delay,
   dropped sends, and load-generator capacity.
3. Separate warm-up from measured intervals. Keep cold-start/cache-miss tests
   separate rather than discarding them when they matter to users.
4. Save a full latency distribution and timeout counts. Never average host p99s
   into a fleet p99; merge compatible histogram counts or raw observations.
5. Alternate comparable baseline and candidate runs where feasible. Repeat enough
   to distinguish the effect from observed run-to-run variability. State sample
   counts and uncertainty; a tiny p99 sample is unstable.
6. Restore the original configuration if the change misses its target. Record
   negative results so the same ineffective tuning is not repeated.

## Useful bounds

Little's law relates steady-state *means*: `L = λW`, using the same system
boundary. If arrival rate is 1,000 requests/s and mean time in that boundary is
0.08 s, mean work in flight is 80. It is not a p99 formula or a safe pool-size
prescription. During unbounded backlog growth the steady-state interpretation
does not apply. A pool of 80 is not necessarily sufficient at a tail latency of
500 ms or during bursts.

For a change that accelerates only a fraction `p` of runtime by factor `s`, the
idealized serial bound is `1 / ((1-p) + p/s)`. If 25% is CPU serialization and the
rest is database wait, making serialization twice as fast yields at most about
1.14× under this model. Queueing and concurrency can invalidate the simple
runtime decomposition; use the bound to challenge expectations, not predict p99.

## Review the benchmark itself

- Is the load generator CPU/network limited?
- Are queues growing while a short test appears healthy?
- Are retries counted as extra business throughput?
- Did the candidate skip validation, durability, encryption, or useful work?
- Are async operations measured until completion rather than enqueue time?
- Are cold pages, JIT warm-up, GC, and compaction represented intentionally?

Exercise: a client capped at 20 concurrent requests reports lower throughput
when response time doubles. Explain why a server capacity conclusion needs
independent offered-load evidence. Then design a burst-and-recovery run that
would expose queue accumulation and deadline expiry.
