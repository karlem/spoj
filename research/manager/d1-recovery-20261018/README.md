# D1 recovery correctness fixture

This bounded fixture tests a residual control-plane contract found by the D1
source review: generation-fenced ownership, compatibility/checkpoint identity,
durable output indexes, and idempotent client acceptance across a lost ACK.

It intentionally does **not** implement or measure inference, KV restoration,
sampler/application state, process/power failure, storage durability, network
traffic, recovery latency, or throughput. Passing it cannot establish a SPOJ
performance advantage. GhostServe/LUMEN-like checkpointing remains the recovery
mechanism; this envelope supplies only the tested correctness semantics.

Run:

```sh
python -B -m unittest -v test_recovery_contract.py
python -B run_fixture.py
```

Acceptance was frozen in issue #9 before execution. The independent validator
must rerun the frozen revision and challenge scope/semantics.
