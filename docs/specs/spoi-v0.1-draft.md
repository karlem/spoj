# SPOI v0.1 — Qwen3 MoE process-boundary experiment

Status: superseded by [the canonical local experiment specification](spoi-v0.1.md). This file preserves the reviewed draft.

Source: the human-supplied `SPOI_V0_1_EXPERIMENT_AGENT.md` (2026-10-16).
The human confirmed native macOS on the existing Mac and requested starting the
experiment. The following changes adapt the supplied execution environment:

- Execute natively on the existing Apple Silicon Mac using CPU float32.
- Use this existing repository; keep the Python project in `spoi/`.
- Default results to `target/spoi/results/<UTC-run-id>/` and logs to
  `target/spoi/logs/`, relative to the repository root; allow explicit path overrides.
- Keep the original small-workload memory budget, and measure actual process memory.
  On macOS, distinguish existing swap occupancy from swap activity during a run.
  Abort when a run encounters memory pressure with active swapping.
- Use the current terminal session for the first run. Scheduling, phone pairing,
  SSH configuration, VMs, and a separate generic job runner are outside this experiment.
- Report native macOS/ARM results with their actual hardware and software context.

The numerical semantics, required tests, measurement protocol, and evidence
requirements below are preserved from the supplied brief.

## Project objective and the role of v0.1

The human clarified that the lab's purpose is to run larger models using the
combined memory and compute of heterogeneous devices available at home. Model
parts should reside on assigned devices, with intermediate inputs and outputs
exchanged to execute inference. Capacity, correctness, and usable execution are
the first questions; performance measurements guide subsequent choices.

The eventual capacity demonstration should execute a chosen model whose working
set exceeds what any one participating device can accommodate under the stated
memory budget. It must account for weights, runtime buffers, shared model
components, and generation state on each device. The model, budgets, device
inventory, and acceptable responsiveness remain open decisions for that later
experiment; v0.1 does not define or claim that demonstration.

The local two-worker experiment is the first mechanism test: establish expert
ownership, route inputs to the owning worker, reconstruct the correct output,
and handle worker failures. Its latency measurements describe the cost of this
implementation. A slower worker path can still satisfy v0.1's correctness and
measurement requirements.

For validation, v0.1 retains a full reference block and frozen state in the
coordinator. Consequently it does not establish reduced total memory use or
loading a model too large for this Mac. A later capacity experiment needs shard
loading that avoids materializing the full model on one device, plus explicit
placement of attention, embeddings, routers, and other non-expert components.

### Experiment order and rental budget

Start with the tiny locally fitting Qwen MoE block to test the execution
assumptions. Review the implementation and its correctness evidence before
scaling. Preserve the required v0.1 diagnostics; rental decisions follow observed
memory and execution requirements rather than a predetermined machine size.

For a later network test, choose a workload that fits the cheapest suitable
workers. A small remote experiment can establish network behavior before renting
enough aggregate memory for the full 30B model. Compare total hourly rental cost,
usable memory after system/runtime overhead, CPU capability, network locality,
taxes, IP charges, and actual availability. The previously discussed two 16 GB
machines are an estimate for a particular full-model scenario, not a requirement
or an approved purchase. Exact rental resources and spend require human authority.

The original v0.1 scope uses a random-weight MoE block and synthetic input vectors.
Whether "review the code" means an independent review of this implementation or
a separate pretrained model performing code review remains to be clarified. The
latter would need a distinct experiment covering full-model generation.

Before a multi-device experiment is specified, resolve:

- Available devices, usable RAM/VRAM, operating systems, supported numerical
  backends, and network connections.
- Which model parts each device stores and executes, including uneven placement
  for devices with different capacities and compute speeds.
- Network request/response representation, timeouts, and failure behavior;
  local shared-memory queues alone do not establish remote execution.
- The model and weight format, per-device memory limits, and the correctness
  reference or validation procedure feasible at that scale.

## Goal

Implement a **Python-first, CPU-only expert-placement and correctness experiment** in the SPOI lab, with timing and memory diagnostics. Compare one-process execution of an actual Hugging Face/PyTorch Qwen3 MoE block with a coordinator plus two long-lived worker processes that own disjoint expert IDs. Use a small, configurable random-weight MoE block first. This v0.1 proves numerical parity across worker boundaries and records the implementation's execution cost as groundwork for later multi-device model capacity experiments. It does **not** benchmark full-model inference or claim a speedup. Keep the default configuration small enough for a 4–8 GB experiment RAM budget on the host; abort a run if memory pressure causes swapping, and record peak RSS.

The single-process oracle must instantiate the real `Qwen3MoeSparseMoeBlock` from `transformers.models.qwen3_moe.modeling_qwen3_moe`, configured through `Qwen3MoeConfig`, rather than replacing it with a toy MoE. The current implementation exposes `Qwen3MoeTopKRouter` and `Qwen3MoeExperts`; inspect the **installed, locked version** before writing the adapter because internal classes and weight layouts may change. Record exact `transformers` and `torch` versions. See the [Hugging Face model documentation](https://huggingface.co/docs/transformers/main/model_doc/qwen3_moe) and [implementation source](https://github.com/huggingface/transformers/blob/main/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py).

## v0.1 scope and fixed semantics

- Inference only: `eval()`, `torch.inference_mode()`, CPU, `float32`, one MoE block, no tokenizer, attention, training, network transport, or distributed GPU framework.
- Start with `hidden_size=64`, `moe_intermediate_size=128`, `num_experts=4`, `num_experts_per_tok=2`, `hidden_act="silu"`, and `norm_topk_prob=True`. Make these CLI/config options; validate `1 <= top_k <= num_experts`, positive dimensions, and exactly two worker partitions. Use input shapes such as `[1, 16, 64]`, `[1, 128, 64]`, and `[8, 128, 64]` plus empty-hit cases.
- Seed Python and PyTorch, initialize one real block once, and freeze a CPU `state_dict` snapshot. The baseline and worker path consume **the same** inputs, router weights, and expert weights. Do not independently initialize worker weights. Hash a canonical serialized state snapshot and record that hash.
- **Static expert placement** means a fixed mapping `expert_id → worker_id` for an entire run, e.g. IDs 0–1 on worker 0 and 2–3 on worker 1. The Qwen3 router still selects top-k experts **per token**. No adaptive placement or rerouting is in scope.
- Use the installed implementation's exact router behavior: linear router logits, float32 softmax, top-k selection, optional top-k renormalization, and cast of selected scores as implemented. Preserve each token's original index and each selected expert's top-k slot. Handle duplicate token assignments to different experts correctly; aggregate with `index_add_` or equivalent. The v0.1 adapter may calculate only the expert feedforward computation in workers, but it must use the actual Qwen3 expert weights, SiLU gated product, down projection, routing weights, and output dtype/order. Do not silently substitute generic `nn.Linear` expert modules with independently copied values.
- Treat `Qwen3MoeSparseMoeBlock` as the reference output. Version-specific internal adapter code belongs in one module, with an explicit compatibility check on parameter names/shapes and a fail-fast error if the locked implementation differs. Document the adaptation; no monkey-patching of Transformers internals.

## Suggested repository layout

```text
spoi/
  pyproject.toml                # Python 3.11+; torch, transformers, pytest; lock with uv
  uv.lock
  src/spoi/
    config.py                   # validated experiment config and seed
    qwen3_adapter.py            # real HF block/router/expert weight access; version guard
    partition.py                # fixed expert ownership; dispatch/aggregation indices
    baseline.py                 # direct HF block oracle
    worker.py                   # long-lived worker loop, local expert slices only
    coordinator.py              # spawn, dispatch, gather, teardown, failures/timeouts
    bench.py                    # scenarios, warmup, timing, records
    records.py                  # JSON schema and atomic result writing
  tests/
    test_parity.py
    test_partition.py
    test_failures.py
  README.md
```

Create the Python project in `spoi/` within this existing repository. Use the existing Git repository; no VM or additional repository is required. Use `uv` to create and lock the environment. Pin exact compatible versions in `uv.lock`; record them in every run. Avoid downloading any pretrained checkpoint for v0.1. Keep datasets, model caches, and results out of Git unless intentionally curated.

## Implementation sequence

1. **Prove the real oracle works.** Instantiate `Qwen3MoeConfig` with the small values and `Qwen3MoeSparseMoeBlock(config).eval()`. Set the expert backend to the installed version's plain/eager PyTorch path if it provides a backend selector; assert which backend is active. Initialize parameters deterministically (the internal block may contain uninitialized expert tensors, so explicitly initialize or use the library's supported initialization). Run a seeded float32 input and record shape, dtype, finite output, and direct block latency. Do not call the full 30B config by accident.
2. **Inspect and freeze weights.** Verify router and expert tensor names, dimensions, dtype, and storage. Capture the reference block's `state_dict` once. Keep a read-only copy in the coordinator for baseline validation. Worker 0 receives only its assigned expert slices; worker 1 receives only its slices. The coordinator retains router weights. Assert no worker loads the entire expert bank. Record per-process RSS after warmup.
3. **Baseline.** Route and execute the reference block in one process with `block(x)`. For instrumentation, separately time the installed router and expert execution on the same block and input. The direct `block(x)` call is the numerical oracle and end-to-end single-process measurement.
4. **Coordinator path.** Spawn exactly two long-lived child processes with `torch.multiprocessing.get_context("spawn")`; guard the entry point with `if __name__ == "__main__"`. Create bounded, per-worker request queues and a response channel; identify each request with `run_id` and `request_id`. Wait for ready acknowledgements before timing. Compute routing once in the coordinator, group selected token rows by owning worker, and send each worker only its selected rows, expert IDs, top-k slots or weights, and request ID. Include a zero-work message or explicit skip accounting for a worker with no hits. Workers run only their local expert slices and return `(token_indices, weighted_outputs)` plus their compute duration. Gather both results and add into the original flat token order, then restore `[batch, sequence, hidden]`.
5. **Transport and lifecycle.** Use CPU tensors with `torch.multiprocessing` queues, or preallocated shared-memory buffers plus small control messages; document the choice and measure it. A queue can move tensor storage into shared memory on first send, so distinguish that copy/serialization cost from expert compute. Bound queues, set response timeouts, propagate worker tracebacks, fail on stale/mismatched IDs, and always terminate/join workers in `finally`. Do not fork after importing threaded numerical libraries; limit `torch.set_num_threads` and inter-op threads per process to avoid oversubscription. Warm up after workers start, outside timed samples. See [PyTorch multiprocessing](https://docs.pytorch.org/docs/stable/multiprocessing.html) and [best practices](https://docs.pytorch.org/docs/stable/notes/multiprocessing.html).
6. **Parity tests before benchmarks.** Compare `block(x)` and coordinator output from the same frozen state. Use `torch.testing.assert_close` with a documented CPU float32 tolerance (initial target `rtol=1e-5`, `atol=1e-6`), then report max absolute/relative error. If reduction order causes a legitimate difference, explain it and tighten/adjust tolerance based on evidence rather than weakening it broadly. Include routing indices/weights parity where observable.

## Required tests

- Deterministic parity across seeds and the three input shapes above, including batches with hits on both workers and a case where one worker receives no selected expert. Construct the latter with a known router/input or controlled logits, not hope from a random seed.
- Top-k `1` and `2`, `norm_topk_prob` both on and off, and expert counts/partitions that are not evenly divisible by two. Confirm every expert has one owner, no assignment is lost or duplicated, and each selected `(token, top-k slot)` contributes once.
- Identical checkpoint hash and expert-slice values in baseline/worker path. A test should fail if a worker uses altered weights.
- Timeout, worker crash, bad request ID, and clean shutdown tests; no leaked child process or shared-memory resource after the test suite.
- CPU-only smoke command succeeds in a fresh `uv sync --frozen` environment without a pretrained download. Document the exact command in project README.

## Benchmark protocol and metric definitions

Use `time.perf_counter_ns()` for all **coordinator wall-clock** spans and monotonic clocks inside workers. Run one scenario at a time with the same input tensor, same frozen weights, and no other SPOI process. Warm up at least 20 requests per path; collect at least 100 measured requests per path unless runtime makes that impractical (then record why and the actual count). Alternate or randomize path order across repetitions to reduce drift. Repeat the whole scenario at least three times. Record raw per-request samples, not only aggregates. Do not include process startup or model initialization in steady-state latency, but report them separately.

For every request, record these boundaries precisely:

| Metric | Start → end | Interpretation |
| --- | --- | --- |
| `baseline_e2e_ns` | immediately before → after `block(x)` | direct HF single-process oracle |
| `router_ns` | before → after coordinator router | routing cost in distributed path |
| `pack_ns` | before grouping/packing → before queue sends | dispatch preparation |
| `dispatch_ns` | before first queue send → after last send returns | enqueue cost, **not** worker receipt |
| `wait_gather_ns` | after last send → all matching replies received | wait, worker compute, transport, scheduling |
| `aggregate_ns` | before output allocation/addition → final shape restored | output reconstruction |
| `distributed_e2e_ns` | before routing → after final output | coordinator steady-state wall time |
| `worker_compute_ns[worker]` | worker immediately before → after local expert math | worker-local duration; clocks across processes are not subtracted |

Report `overhead_ns = distributed_e2e_ns - baseline_e2e_ns` for paired samples and `overhead_ratio = distributed_e2e_ns / baseline_e2e_ns`. Also report median, p95 (state percentile method), min/max, interquartile range, samples/s for each path, RSS for coordinator/workers, and CPU model/thread settings. Component spans may overlap or omit worker startup and must **not** be summed to claim exact total overhead. These are local-process findings; shared-vCPU noise and IPC implementation affect them. Record whether both workers did actual work for a scenario.

## Reproducible run records

Write each run atomically to `target/spoi/results/<UTC-ISO8601-run-id>/` with `config.json`, `environment.json`, `samples.jsonl` or CSV, `summary.json`, `parity.json`, and a plain-text `README.txt` explaining how to rerun. Include Git commit and dirty-state indicator, lockfile SHA-256, package versions, OS/kernel, CPU flags/model, vCPU count, RAM, governor if available, thread counts, backend name, seed, tensor shapes/dtype, expert placement, warmup/sample counts, state hash, exact command, UTC timestamps, and any failure/timeouts. Logs go under `target/spoi/logs/` without credentials. Do not overwrite an existing run directory. Keep raw samples for later analysis and export the result bundle to the user.

## Optional follow-up, separate from v0.1 acceptance

After CPU parity is stable, explore loading actual `Qwen/Qwen3-30B-A3B` pretrained weights **only on appropriately sized hardware** and only after estimating RAM/VRAM, disk, quantization support, likely runtime, and rental cost. Do not keep a 32–64 GB VM running for v0.1 merely to preserve this option. The model has 128 experts and 8 active per token across 48 layers; the tiny one-block experiment is not a throughput proxy. Raw BF16/FP16 weights are about 61 GB decimal, and nominal 4-bit weights about 15.25 GB decimal plus metadata and runtime overhead. A 32 GB VM may support some quantized tests; 64 GB gives more headroom, while full BF16 generally needs substantially more. CPU-only generation can be slow. GPU use needs a separate memory and compatibility plan. Keep this as a new experiment and identify any quantization-specific parity differences. See the [model card](https://huggingface.co/Qwen/Qwen3-30B-A3B) and [base config](https://huggingface.co/Qwen/Qwen3-30B-A3B-Base/blob/main/config.json).

## Definition of done

Deliver the code, lockfile, concise project README, test output, and at least one complete run bundle. Show an actual command that reproduces parity and benchmarks natively on this Mac. State the baseline/distributed medians and p95, paired overhead, maximum parity error, exact versions, and hardware. Mark v0.1 complete only when all required tests pass and the benchmark produces raw samples and a summary. If the chosen Transformers version cannot expose a stable Qwen3 block/expert adapter, stop with a documented incompatibility and a pinned-version remedy; do not pass a handmade surrogate as the requested experiment.

