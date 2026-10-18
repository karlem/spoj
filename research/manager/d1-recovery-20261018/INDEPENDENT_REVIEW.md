# Independent review of frozen D1 correctness fixture

Reviewer: `/root/d1_recovery_validator` (different worker from manager/author).
Frozen commit: `22baca7305f24d27866b349f3d095f0c5d791847`.
Disposition: **ACCEPT, narrowly scoped**.

The reviewer fetched every file at the exact commit into a separate temporary
directory without edits. `sha256sum -c SHA256SUMS` exited 0 for all 11 listed
files. The frozen manifest is anchored by the Git commit; it intentionally does
not self-hash. Validation data totaled 21,761 bytes.

## Independent commands and results

Both Python commands used a 2 GiB address-space limit and a 300-second timeout.

```sh
(ulimit -v 2097152; /usr/bin/timeout 300s python -B -m unittest -v test_recovery_contract.py) > exact-unit.stdout 2> exact-unit.stderr
# exit 0; one test passed

(ulimit -v 2097152; /usr/bin/timeout 300s python -B run_fixture.py) > exact-fixture.json 2> exact-fixture.stderr
# exit 0

cmp -s fixture.json exact-fixture.json
# exit 0
```

The independent JSON SHA256 was
`204bfe3a1ad8ee10dd3fc8e36d174d105244a1e88796dab76ef2efbe153daf09`
and was byte-for-byte identical to the frozen output. The reproduced environment
was Python 3.12.14 on Linux 6.18.55 x86_64/glibc 2.39. Unit stderr differed only
because it contains elapsed time.

## What passed

The prescribed trace exercises generation-CAS reacquisition; stale expected
generation and stale-owner rejection; identity/checkpoint digest mismatch;
persisted token redelivery after a lost ACK; same-digest client deduplication;
monotonic ACK to index 3; and server/client digest conflict rejection. Final JSON
is deterministic. The retained first failed attempt hashes cleanly. Its traceback
reaches the final-state assertion; the tuple/list diagnosis is producer-reported
because the attempt-1 source/diff was not retained.

Accepted claim:

> A deterministic, single-process/single-SQLite reference simulation demonstrates
> generation-fenced state transitions, digest-conflict detection and one durable
> logical client acceptance for duplicate delivery in one prescribed lost-ACK trace.

## Scope corrections and findings

- Delivery of token 2 occurs twice. The result is idempotent logical acceptance,
  not exactly-once wire delivery.
- Server state, output log, ACK watermark and simulated client acceptance use one
  SQLite database. Independent failure/durability domains, disconnect, network
  ambiguity, crash/reopen, replica failover and power loss are untested.
- `ack()` is not coupled to proof of durable client receipt and can cumulatively
  ACK unseen output. `client_receive()` can accept unknown/noncontiguous output or
  a digest absent from the server log. The prescribed happy path does not falsify
  these cases.
- `Lease` is a fencing generation, not a timed lease or authenticated owner.
  SQLite `BEGIN IMMEDIATE` encodes CAS; distributed contenders are untested.
- Identity/checkpoint validation compares caller-supplied hashes. It does not derive
  a canonical manifest, restore payloads, update checkpoints, or preserve RNG,
  sampler or application/tool state.
- SQLite WAL is not evidence of power-loss durability.

Fixture execution/integrity is accepted. End-to-end recovery and performance remain
**BLOCKED**. Research decision remains **REJECT** standalone checkpoint novelty,
**UPSTREAM** this correctness reference, and **UNRESOLVED** measured SPOJ advantage.

## Next smallest falsifying fixture

Use separate server/client SQLite databases and processes. Crash/reopen the client
after durable token-2 acceptance but before ACK transmission, then retry through a
small drop/duplicate/reorder transport. Assert at-least-once delivery plus one logical
effect. Add negative cases for ACK before durable acceptance, skipped cumulative ACK,
unknown/noncontiguous client indexes, concurrent generation acquisition and mismatched
digests. This would remain a correctness simulation, not inference-performance evidence.
