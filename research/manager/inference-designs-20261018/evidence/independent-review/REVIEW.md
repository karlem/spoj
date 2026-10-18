# Independent review: inference-engine designs

**ACCEPT for scoped research design and arithmetic evidence.** No blocking
correction was found in evaluated commit
`f9730ed4c6e0ee15b063320d4359645acd904f34`. This is not acceptance of an implemented
engine, a concurrent/distributed protocol, a physical performance advantage, or
product/native-Mac behavior. Those remain unresolved or blocked as stated below.

Run: `inference-designs-20261018-1841`, issue `karlem/spoj#9`.
Reviewer: `/root/inference_design_validator`, independently delegated from the
manager and both source researchers; provider model ID unavailable. First recorded
reviewer clock: 2026-10-18 18:49:23 UTC. Reviewed detached worktree
`/workspace/spoj-inference-designs-review`; all generated artifacts are under
`/workspace/scratch/inference-validator`. No children, author edits, dependencies,
model downloads, hardware changes, or remote commands were used.

## Executed validation

`python3 -B /workspace/scratch/inference-validator/run_review.py` ran the frozen
author fixture once and the independent audit once. Both exited 0. Exact commands,
times, environment, and limits are in `execution.json`; stdout and stderr are
retained. Each child had a 300 s wall timeout, 2 GiB address-space limit, 60 s CPU
limit and 16 MiB output-file limit. Actual elapsed times were about 0.033 s and
0.065 s respectively. There were no failed reviewer execution attempts.

- The author's output was byte-identical to its original result: 432 comparisons,
  including 240 empty cases, with maximum absolute error `1.1102230246251565e-16`.
  Source SHA-256 is `24d8c671408333e7a2cff47d4a6273fc2b1cdfd024e4f2da5e2d0fb82a459ac2`.
- The audit independently checked all six byte-ledger rows and the branch,
  Little's-law, and RTT arithmetic. KV is 131,072 bytes per token across 32 layers;
  query plus summary is 794,624 bytes per remote owner per decode step; an appended
  KV row adds 131,072 bytes across layers when that position's owner is remote.
  The example is ideal payload accounting, with excluded costs explicitly named.
- Eight additional reviewer fixtures supplied 96 merge comparisons against a
  separate 90-digit Decimal softmax reference. They cover equal/near-equal scores,
  large common shifts, strongly separated scores, signed values, uneven and empty
  shards, and three merge orders. Maximum absolute error was
  `2.8065589257859405e-17`, below `1e-10`. These are exploratory reviewer examples,
  not additions to the author's preregistered 432 comparisons.
- An exploratory duplicate-coverage counterexample changes an equal-weight answer
  from `0.5` to `1/3`. The algebra helper does not reject duplicate ownership;
  validating complete disjoint coverage and accepting each response once belongs
  to the explicitly unimplemented owner protocol. This supports that requirement,
  rather than establishing protocol correctness.
- All 33 retained fundamentals-source bodies and 38 prior-art-source bodies match
  the published SHA-256 values and byte sizes. All seven fundamentals excerpt
  records and all nine prior-art excerpt records match their captured sources;
  prior-art line anchors match exactly. All five fundamentals publication-manifest
  entries and all 51 entries in the prior-art original-source manifest passed.

`git diff --check 72219b9b4ba769e8d1f88454953d191684355adc..HEAD` exited 0; the
reviewed worktree was clean. The manager's required product-check stderr confirms
exit 1 before collection: offline resolution lacks cached
`nvidia-nccl-cu13==2.30.7` through Torch. I inspected this failure rather than
repeating an unchanged dependency blocker. It is not a passing product check.

## Claims and design contracts

**H1: branch lifetime and admission.** README lines 86–122 distinguish logical
ownership, reservations, and in-flight kernel/DMA/migration pins. The proposed
single metadata owner serializes publication and cancellation, while physical
reclamation waits for actual use completion. The proposed harmful-history tests
cover cancellation before and after commit, partial tails, delayed completion,
allocation failure, and exhausted credits. These are specifications and future
tests; no scheduler or interleaving prototype ran in this packet. The distinction
between an application-visible in-memory commit, a durable recovery checkpoint,
and external tool effects is explicit. Token-state idempotency does not establish
exactly-once tool effects.

The 4.5 GiB copied-branch example versus 1.5 GiB shared-prefix example is correct.
The proposal and existing exact sharing both use 1.5 GiB: its asserted additional
sharing saving is correctly **zero**. A lifetime/admission advantage must therefore
survive comparison with existing SGLang cache/fork behavior and application-aware
policy. Parrot supplies relevant architecture and scheduling precedent; its
current patched, unmaintained source is not a qualified deployable dependency.
The future workload must distinguish known traces from unpredictable tool waits
and preserve offered load, quality, cache budgets and total resources.

**H2: KV-owning attention.** The stable reduction is valid for a partition of one
attention operation in real arithmetic. Current-step K/V is explicitly staged and
visible to that step alongside the committed prefix, and the complete step is
published only after required layers and sampling. The design names exact model,
mask/position, partition and generation identities; missing/stale responses are
errors, not empty shards. It requires response coverage checks, stale-owner
fencing, reserved append/reduction buffers, bounded credits and deterministic or
all-or-release credit acquisition. Cancellation fences publication before draining
uses. These address the relevant failure modes at design level; implementation,
deduplication retention, transport completion and device memory ordering remain
to be specified and tested against actual APIs.

The fixture's all-masked convention is `None`, meaning no result; it does not claim
that every model/backend returns that value. The code consumes precomputed Q/K
vectors and explicit visible positions. It does not implement RoPE, additive bias,
quantization, FP16/FP32 kernels, model layouts, RPC parsing or distributed epochs.
Its binary64 successes cannot establish their correctness or task-quality parity.

Query/summary traffic correctly scales with query heads, whereas stored KV and
append traffic scale with KV heads. The 8 GiB at 64K context and 4 GiB per balanced
owner are consistent. Raw-copy traffic is explicitly a weak baseline; vLLM/SGLang
DCP, same-capacity local attention, and independent-agent placement are named as
stronger comparisons. The 32 serial RTT floors and slowest-owner critical path
are conditional bounds, not latency predictions. Nothing claims that relocating
KV solves weight capacity or dense/MLP compute.

**Queued recurrent state.** Inspected Mamba/Mamba-2 cache allocations use bounded
convolution/SSM shapes independent of `max_seqlen`, and step paths mutate that
state. The proposed fork-copy requirement is therefore appropriate. Context
scaling changes do not preserve an arbitrary transformer's outputs; hybrids can
still contain attention KV, and past-input edits require replay/checkpoints.
Task quality, training/weight compatibility, and actual fork/restore cost remain
open. This is a queued third direction, not a third active experiment.

## Source depth and limitations

I inspected the frozen synthesis, protocol, analytical source, both researchers'
reports and provenance. Direct source spot checks included SGLang fork/cache
methods and DCP documentation, vLLM context-parallel documentation, Parrot semantic
variables and its current limitations, Flash-Decoding's three-step description,
Mamba cache/update methods, the requested library's concurrency/distributed-system
procedures and partial-book-coverage record, and relevant linearizability,
DMA-completion and Roofline passages. Other source families were checked through
the reports, hashes and bounded excerpts; this was not a full independent reread
of every paper or implementation. No external implementation was executed.

The `karlem/skills` pin and applied ownership, harmful-interleaving, admission,
measurement-boundary and bandwidth/causality procedures support the proposed
contracts. The library explicitly records partial book coverage; neither this
review nor the research run establishes whole-book reading. Captured-source
hashes establish consistency with retained bytes, not an independent fresh
retrieval from every origin. No worldwide novelty conclusion follows. The
retained failed retrievals and the excluded unrelated GASNet paper were not
promoted to evidence for the designs.

One nonblocking test-coverage limitation deserves explicit attention: the main
fixture chooses the GQA KV-head index once and uses it in both reference and
candidate paths. Its wrong-head negative control establishes that an asymmetric
example produces a different answer; it is not independent validation of all
head-routing code. The future protocol/kernel fixture should derive expected
head mapping independently and inject wrong mappings. The current mapping is
correct by inspection for its declared contiguous grouping, and the manuscript
does not claim full backend validation.

**Disposition:** pursue H1's bounded lifecycle model and existing-engine API audit;
retain H2 for protocol qualification and a physical capacity/SLO test; queue the
recurrent model comparison. No new OS or hardware advantage has been demonstrated.
Research design acceptance, unresolved implementation/performance questions, and
blocked product/native-Mac acceptance must remain separate in the final handoff.
