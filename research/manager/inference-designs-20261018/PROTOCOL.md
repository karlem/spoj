# Inference designs: source and analytical protocol

Run `inference-designs-20261018-1841`, issue #9. Started 2026-10-18 18:41 UTC,
expires 19:11 UTC. Research proposals; not approved product requirements.
Manager authors synthesis, two source researchers, one independent validator;
no grandchildren. Existing PR #12/#13/#14 conclusions remain in force.

H1: an explicit branch-lifetime/admission contract can improve completed-task
outcomes under memory pressure over a strong prefix-sharing engine. Source stage:
map existing SGLang/Parrot behavior and specify an experiment that can reject the
extension. Do not claim generic DAGs, forks or shared KV as novel. No H1 engine
implementation or performance trial this run.

H2: KV-resident attention workers can trade bulk KV movement for query/summary
messages. This is a proposed topology/execution contract around known distributed
attention, not a new attention formula. Verify stable softmax merge in real
arithmetic and a bounded floating-point fixture; physical advantage remains
unresolved. It does not solve model-weight capacity or alter token dependencies.

The third, recurrent-state/model co-design direction is queued, not an active
experiment. Describe quality/training tradeoffs without claiming equivalence to
an unchanged transformer.

Analytical fixture declared before execution:
- Stdlib Python only, no weights, external code execution or dependencies.
- Compare monolithic stable softmax attention against shard summaries and stable
  merge under distinct query-to-KV head mapping (GQA), empty shards, one token,
  uneven partitions, all-masked rows, and extreme finite scores.
- Fixed seed 20261018, binary64 arithmetic; explicit all-masked convention returns
  no attention result, so no division by zero or silent invented value.
- Use independent direct reference versus distributed formula; compare max
  absolute error <=1e-10 and finite outputs for nonempty finite inputs.
- Deliberately wrong GQA head mapping must differ on an asymmetric fixture.
- Report exact fixture counts and all failed attempts. Passing binary64 tests
  establishes only these examples, not GPU kernel correctness or FP16 accuracy.
- Conditional byte ledger: 32 layers, Hq=32, Hkv=8, d=128; FP16 Q/K/V,
  FP32 summary; contexts 8192/65536; remote workers 1/3/7. Separate Q broadcast,
  summary return, new K/V append, local memory reads and framing/precision limits.
- H1 capacity example: four branches, 8192-token prefix, 1024-token suffix each.
  Compare copying with both existing prefix sharing and proposed sharing; charge
  in-flight references and all other engine memory separately.
- No timing claim. Each process <=300 s wall, 2 GiB address space, 60 s CPU,
  16 MiB output file; total artifacts/downloads <=100 MiB.

Future performance gates are proposed experiment choices, not agreed product SLOs:
20% lower p95 complete-task latency at fixed arrivals/model/quality/resources,
or useful added capacity meeting a declared SLO, against strongest available
baseline. Freeze trace/arrival/deadline/quality policies and measurement windows
before a future hardware run. Report tails only with adequate independent trials.
