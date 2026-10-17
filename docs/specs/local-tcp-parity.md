# Local TCP MoE correctness demonstration

Approved direction: human conversation on 2026-10-17 explicitly requests the proposed three-worker local TCP milestone, stronger evidence and no expanded scope. This additive milestone authorizes local TCP implementation and an evidence/walkthrough issue. It does not replace original v0.1/native-Mac acceptance or authorize #2, multiple hosts, pretrained models, generation, speedup/capacity claims, purchases or merge.

## Computation contract, recorded before implementation

Source authority is the installed frozen lock: Torch linux 2.14.1+cu130 / darwin 2.14.1, Transformers 5.20.1, Qwen modeling source SHA256 58387f2cc22a706e7e4c7dabe6cf05cb1e9c9fe48c57e2f2a0fc5cbdb2132f4f. Existing exact version/source/backend/schema/finite CPU float32 guards and rtol=1e-5, atol=1e-6 remain mandatory. Inspect installed Qwen3MoeTopKRouter, Qwen3MoeExperts and Qwen3MoeSparseMoeBlock. Router is F.linear -> float32 softmax -> topk -> optional selected-score normalization -> dtype cast. Expert is fused gate/up projection -> SiLU(gate)*up -> down projection -> selected routing weight. Reference block restores original batch/sequence shape after indexed summation.

Invariants:

1. Initialize explicitly in sorted parameter-name order from a seed. Freeze cloned state and canonical hash. Direct HF reference and worker slices come from this one snapshot; workers never initialize expert weights or receive full expert banks.
2. Exactly one static owner per expert. Default five experts/three workers own [0,1], [2,3], [4]. Local worker count 1–4 is configurable; existing two-worker queue experiment remains supported unchanged.
3. Every selected (token, top-k slot) appears exactly once, retains expert ID, input row and routing weight, and is sent only to its owner. Zero-hit workers return explicit empty contributions. Top-k two does not imply all three workers process each token.
4. Validate every returned weighted contribution against the actual HF experts on the same assignment and snapshot. This independent oracle must not call the worker evaluator. Sum contributions in original token order and compare against direct block(x) using the unchanged float32 tolerances.
5. Initialization shards and request/result tensors cross actual loopback TCP as bounded framed bytes. No tensor queues, shared-memory handles, pickle or file-path shortcuts in the TCP path. Separate subprocess workers receive only endpoint/worker identity as launch arguments.
6. Versioned framing, bounded metadata/payload and tensor shapes, exact message schemas/identities, digests, readiness, monotonic deadlines, bounded send/receive/backpressure and deterministic socket/child cleanup. Fail the whole session on errors; no retry/failover.

## Acceptance and validation

Default tiny CPU dimensions hidden=64/intermediate=128; three persistent workers plus coordinator, one host. Bind loopback only. Frozen dependencies unchanged. Validate seeded parity across worker counts 1/2/3/4, seeds, top-k 1/2, norm on/off, odd expert counts and existing three shapes; deliberately force all-worker and zero-hit routing. Compare raw contribution vectors as well as outputs and assignment multiplicity.

Test fragmented/partial I/O, malformed/oversized/truncated frames, wrong versions/IDs/dtypes/shapes/digests, nonfinite values, corrupted weights/contributions, disconnects, stalls, send backpressure, request/startup deadlines, and bounded process/socket cleanup. Negative tests must fail for the intended reason; retain observed outcomes. Preserve legacy regression suite. Run the demo in a new frozen environment.

Emit a bounded raw trace of token vectors, router logits/selected IDs/weights, ownership, initialized shard metadata, actual TCP frame IDs/endpoints/bytes, per-assignment weighted results and independent oracle contributions, and reconstructed/direct outputs. Link to evaluated Git commit, dependency/source hashes, command, exit code, exact versions, PIDs and cleanup. Persist raw trace and checks on GitHub. Explain through diagrams, measured token examples and an annotated code map. Explanatory diagrams are distinct from measured traces. Reject oversized trace requests rather than silently truncating claimed evidence. No benchmark or #2 run bundle is implied.

Independent review covers source fidelity, transport, contribution evidence and faults. Success is a reproducible local correctness argument only. Original native Mac full/fresh checks remain outstanding. Once local milestone passes, document questions/evidence for later multi-host planning only, without implementation or provision.

## Approved execution sequence

One implementation issue for local TCP workers, invariant checks and protocol tests, then one dependent demo/evidence/walkthrough issue. The human's verbatim task authorizes this bounded sequence. The already available/reviewed Linux artifact on issue #1 is the starting dependency; original Mac acceptance remains separate, not waived or silently satisfied. Existing #2 is unchanged. Each issue records sole ownership, evaluated commit and evidence; human retains merge authority.
