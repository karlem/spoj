# SPOI tiny Qwen3 MoE correctness experiment

Issue #1 implements the CPU process-placement mechanism in the approved
[v0.1 specification](../docs/specs/spoi-v0.1.md) at revision
`e49f36f30312400a45c4d68d4a1db18328e64ef6`. It uses random initialized weights
in the actual Hugging Face `Qwen3MoeSparseMoeBlock`; no checkpoint, tokenizer,
attention, generation, or GPU is involved. Full benchmark/run bundles and memory
pressure monitoring belong to dependent issue #2. This correctness artifact does
not establish v0.1 completion, a speedup, or reduced total model memory.

From the repository root (Python 3.11+ and uv required):

```sh
uv sync --project spoi --frozen
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --project spoi --frozen python -m spoi smoke
./scripts/check.sh
uv run --project spoi --frozen pytest spoi/tests -q
```

The lock currently selects torch 2.14.1, transformers 5.20.1, pytest 9.1.1,
and psutil 7.2.2. The smoke prints actual versions, source fingerprint, eager
backend, config, finite CPU float32 shape, state hash, owned experts, persistent
worker PIDs, participation, local compute duration, parity errors, and exit codes.
It compares two requests to the direct HF block with `rtol=1e-5, atol=1e-6`.
Relative error uses `abs(actual-reference)/max(abs(reference), 1e-12)`;
`assert_close` determines pass/fail. The smoke is not a latency benchmark.

The runtime guard accepts only the inspected platform/build pairs: native
macOS `torch.__version__ == "2.14.1"` and Linux `"2.14.1+cu130"` from the
unchanged lock. It does not strip build suffixes or accept arbitrary 2.14.1
variants. Linux's locked wheel installs CUDA dependencies, but this experiment
still uses CPU tensors exclusively and requires no GPU. Transformers remains
exactly 5.20.1 and the Qwen source SHA-256, eager backend, and tensor schema
guards remain enforced. The installed Linux router/expert implementation was
reinspected: linear router, float32 softmax, top-k/optional normalization,
fused gate/up SiLU product, weighted down projection and indexed accumulation.
Linux smoke/test results supplement native Mac acceptance; they do not replace
the complete native Mac suite, fresh-environment smoke, or independent review.
Seeded weights may differ across platforms: compare paths against the same
local frozen snapshot, rather than requiring the Mac and Linux hashes to match.

Tiny dimensions and routing options are configurable, for example:

```sh
uv run --project spoi --frozen python -m spoi smoke --num-experts 5 --top-k 1 --no-norm-topk-prob --batch 8 --sequence 128 --seed 1
```

Options include `--hidden-size`, `--moe-intermediate-size`, `--hidden-act silu`,
and `--threads`. `ExperimentConfig` additionally controls two-worker placement
and startup/request/shutdown deadlines. Default ownership splits ordered expert
IDs into contiguous halves, with the extra expert on worker 0. One expert is
valid and leaves worker 1 empty. Every request explicitly visits both workers,
including empty assignments.

`qwen3_adapter.py` concentrates all HF internal imports and expert arithmetic.
It guards exact package versions, the installed Qwen source SHA-256, eager
backend, exact state keys, shapes, dtype, device, and finite values. Updating the
lock requires reinspection and validation; an unsupported implementation fails
before worker startup. Expert tensors are explicitly initialized in sorted
parameter-name order after seeding Python and Torch. Snapshot exports clone;
canonical SHA-256 covers sorted length-delimited name/dtype/shape metadata and
little-endian float32 bytes, with format tag `spoi-f32-state-v1`.

The coordinator owns the actual HF router and a frozen reference snapshot. Each
spawned child receives only compact cloned expert slices, global expert IDs,
state provenance, and a shard digest that the child verifies before readiness.
Workers use the real fused gate/up and down weights, SiLU gated products and
routing weights. Packing retains original token and top-k slot indices;
aggregation adds each selected contribution once into original token order.

`ExpertSession` is a context manager with one request in flight. It starts two
long-lived processes using `torch.multiprocessing.get_context("spawn")`, one
bounded request queue per worker (capacity 1) and a bounded response queue
(capacity 4). CPU tensor transport uses PyTorch's `file_system` sharing strategy,
available on native macOS. First sending a tensor may copy its storage into
shared memory; queue send duration is enqueue cost, not worker receipt. This is
local shared memory transport, not network execution. Thread counts are set
before numerical work in each process. Use a guarded `if __name__ == "__main__"`
entry point when calling the session from a script.

Ready messages verify worker PID, ownership, digest and storage sizes. Requests
carry unique run/request identities. One monotonic deadline bounds sends and
receives; worker exits, tracebacks, stale/duplicate/malformed replies and invalid
assignment coverage fail the session. Any forward failure closes it permanently.
Shutdown drains responses, joins children and terminates/kills only surviving
session children within bounded grace periods. Queues close without unbounded
feeder joins. The test suite exercises normal and abnormal shutdown and checks
known named shard resources after sharing-manager grace without unlinking them.

Tests include 48 process parity scenarios (two seeds, top-k 1/2, normalization
on/off, four/five experts, three required shapes), controlled zero-hit cases on
each side, exact routing/slot coverage, altered-weight detection, protocol and
process failures, bounded backpressure, and subprocess resource cleanup. No
test downloads pretrained weights. The coordinator retains timing spans and
worker-local compute durations for issue #2; clocks from different processes
are never subtracted.

For a fresh frozen environment, choose an absent path and use it consistently:

```sh
UV_PROJECT_ENVIRONMENT="$PWD/target/spoi/fresh-issue1" uv sync --project spoi --frozen
UV_PROJECT_ENVIRONMENT="$PWD/target/spoi/fresh-issue1" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --project spoi --frozen python -m spoi smoke
```

Keep caches/results under ignored paths. Native shared-memory process tests
need permission to create semaphores/shared memory and inspect owned process
lifetimes; a sandbox-denied run is failed validation until rerun with permission.

## Three-worker local TCP correctness demonstration

The additive [local TCP specification](../docs/specs/local-tcp-parity.md) keeps
this milestone separate from original native-Mac acceptance and issue #2.
From the repository root, use a new output directory:

```sh
uv sync --project spoi --frozen --python 3.12
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --project spoi --frozen python -m spoi tcp-demo --output target/tcp/my-demo
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --project spoi --frozen python -m spoi.verify_tcp_trace target/tcp/my-demo/trace.json
./scripts/check.sh
```

`my-demo` must be absent. The demo starts three standalone subprocesses on
loopback TCP, transfers compact expert shards as raw tensor bytes, reuses the
same worker PIDs across three requests, and checks every returned contribution
with the actual unchanged HF expert path before comparing the reconstructed
output to direct `block(x)`. It forces all-worker and zero-hit routing. Workers
are trusted local processes; this protocol is not exposed to remote peers.

The output contains `trace.json` (bounded full tensor records and base64 raw
TCP frames), `verification.json`, and a generated `README.md` with measured
routing tables, frame sequence diagram and source walkthrough. The offline
verifier decodes the frames, checks receipt hashes, reconstructs seeded shard
provenance and re-executes HF contribution and direct-output oracles without
starting workers. It rejects altered bytes, even if a result frame's hash is
recomputed, when the altered contribution disagrees with the HF oracle. Hashes
link evidence; they are not signatures or independent proof of the recorded
process execution. Source/model arithmetic shares PyTorch with the oracle;
no independent audit of compiled kernels is claimed.

`TCPSession(block, frozen, workers=1..4)` provides the bounded local worker
count independently from the legacy two-worker `ExpertSession`. The default
TCP demo uses five experts split [0,1]/[2,3]/[4], CPU float32, tiny dimensions
and unchanged locked packages. TCP frames cap metadata at 64 KiB and tensor
payload at 8 MiB. Trace mode caps requests at four, tokens at 16, hidden size
at 64, frames at 128 and aggregate raw frame bytes at 4 MiB; excess fails
explicitly. Do not use this correctness demonstrator to infer speedup, reduced
total memory, full-model generation, or multi-host/native-Mac acceptance.
