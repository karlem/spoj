# D2 primary-source decision report

Task: `d2-resume-20261018-1531/D2-sources`; issue #9. Worker: `/root/d2_sources`; actual model ID unavailable (not exposed by harness). Source-only; no external code executed, model downloaded, experiment or performance measurement performed. Sources retrieved 2026-10-18 UTC. Manager owns integration and decisions. Research scope is tool-turn waits, with arbitrary mid-generation suspension treated separately.

**Recommendation: UPSTREAM for generic token/KV suspend; UNRESOLVED for a useful workload-specific advantage.** ServerlessLLM already reconstructs KV from transferred tokens. llama.cpp already provides real KV serialization, disk slot save/restore, and automatic idle-slot RAM caching. A generic “serialize KV during tool waits” mechanism has no demonstrated novelty or superiority. The decisive remaining question is whether an existing cache policy fails a real tool-wait workload after physical resource, correctness and transfer costs are counted.

The most important negative finding: **clearing a llama.cpp slot releases reusable KV cells, not its preallocated backend memory buffers or shared model weights.** A calculation assuming physical K-byte release cannot be assigned to this implementation merely because slot erase succeeds. If the desired benefit is reusable GPU KV capacity rather than lower allocated GPU memory, measure that separately. CPU RAM cache may increase host RSS while freeing logical accelerator capacity.

## Pins and evidence strength

- ServerlessLLM: `9f50241baa5386e06a9321c51f19a9ef5f964c2b`.
- llama.cpp: `5aeac37a35b44fde4bdffaec9159f2fcb253b622`.
- Exact source URLs, retrieval UTC timestamps, bytes and SHA256 are in `manifest.jsonl`; the downloaded files retain upstream relative paths. API commit/tree metadata is retained separately. 14 successfully retrieved targeted source files plus 2 upstream license files, 1 failed target, 1,206,822 source/license bytes; API metadata adds 1,160,469 bytes. Total retrieved payload is below 10 MiB. One raw HTTP 404 is preserved in `failures.txt` (mistaken path `src/llama-sampling.cpp`; correct source is `src/llama-sampler.cpp`). No other retrieval failure observed.
- Statements below are **source-supported implementation observations/inferences**, not reproduced runtime results. Not inspecting a subsystem means unverified, not absent.

## Closest alternatives and implemented paths

| Alternative | Source-supported state path | Fit / limitation | Cost and strongest objection |
|---|---|---|---|
| Keep resident | No migration, retain request/context and sampler | Correct baseline for exact mid-generation continuation; between requests only the server's retained prompt state remains relevant | Occupies KV cells throughout wait; shared weights should not be charged once per request |
| ServerlessLLM token replay | Router starts target backend, fetches token lists, invokes target `resume_kv_cache`; Transformers implementation calls `model.generate(input_ids, past_key_values=..., max_new_tokens=1)` to reconstruct/extend target KV; preempted generation resumed with request data and final token output | Live whole-instance relocation, not an implemented durable arbitrary tool/application checkpoint | Small token payload versus KV, but repeats prefill and overlaps source + target model residency; may already beat KV transfer |
| llama.cpp per-sequence restore | Token list + memory state written to file, KV tensor bytes copied through host buffers, restored into existing backend tensors | Practical same-model/backend baseline for prompt reuse across a tool turn; storage API is not a full process snapshot | Save/load IO and staging, format/shape constraints; existing mechanism defeats generic serialization novelty |
| llama.cpp built-in idle-slot cache | `prompt_save` serializes target/draft sequence state into RAM; on new task, cache idle slots and clear them with unified KV; `prompt_load` delegates cache lookup/restore | Strongest ready policy baseline for concurrent sessions waiting on tools; validate actual settings and hit behavior | Bounded RAM cache, pressure/eviction effects; may already achieve the proposed reusable capacity benefit without a new subsystem |

### ServerlessLLM trace

`serverlessllm/sllm/routers/migration_router.py`:
- `inference`, lines 74–90: preempted result routes to target `resume_generate` with original request data and `current_output`; decrements remaining token budget.
- `execute_migration_plan`, lines 104–165: starts and initializes target for the same model/backend configuration before source is removed.
- Lines 174–201: repeated `get_current_tokens` -> `resume_kv_cache(current_tokens)`, stopping by token delta. The transferred object in this path is token IDs, not serialized tensor bytes.
- Lines 219–225: source backend shutdown, `ray.kill`, scheduler resource deallocation. This is whole-instance release; destination remains resident. A source actor kill does not prove cluster-wide total memory saving.

`serverlessllm/sllm/backends/transformers_backend.py`:
- `get_current_tokens`, 395–403, returns stream token state.
- `resume_kv_cache`, 405–420, reconstructs target KV using generation; `resume_generate`, 422–470, uses cached state and current output plus request parameters.
- `shutdown`, 367–381, signals deleting, waits, deletes model. No per-request tensor-export path is shown here.

`serverlessllm/sllm/backends/vllm_backend.py`:
- `get_current_tokens`, 295–308, concatenates prompt IDs and first output's token IDs.
- `resume_kv_cache`, 310–322, submits `generate` with input token IDs and one requested output token.
- `shutdown`, 265–281, aborts requests, deletes engine, collects garbage and empties/synchronizes CUDA cache.
- End-to-end migration with this backend is **unverified**: neither this file nor its inspected abstract base defines the `resume_generate` method called by the router. Do not infer the entire route works from method names or this partial inspection.

`docs/features/live_migration.md`, 5–21, describes locality-driven migration and a two-GPU, 20-GB-host-memory example for version 0.6. These are documented example prerequisites, not measurements or proof current HEAD has run here.

### llama.cpp trace

`llama/src/llama-context.cpp`:
- `llama_io_write_file::write_tensor`, 3012–3025: `ggml_backend_tensor_get` into a host vector, then write bytes; corresponding read at 3036–3050 calls `ggml_backend_tensor_set`. This is real tensor transfer, not token replay.
- `state_seq_save_file`, 3588–3605: magic/version, token count/IDs, then sequence memory state.
- `state_seq_load_file`, 3534–3585: header and token capacity checks, reads tokens then sequence memory state. Null token output only reads count and does not restore.
- `state_seq_write_data`/`state_seq_read_data`, 3654–3669: delegate to memory module. No sampler, external tool state, model tensors or backend process is serialized here.
- Whole-context `state_write_data`/`state_read_data`, 3608–3651: architecture string and memory module; TODO acknowledges incomplete model identity verification. At this pin these bodies do **not** write logits or embeddings despite the broader comment at `include/llama.h:829`. Prefer implementation over that comment.

`llama/src/llama-kv-cache.cpp`:
- Constructor, 277–295: allocates backend tensors and retains buffers in `ctxs_bufs`.
- `clear`, 391–401: resets cells and optionally zeros retained buffers; it does not deallocate them.
- `seq_rm`, 404–468: removes sequence membership and updates free-cell search head; it does not release backend buffers. Cells shared with another sequence need not become reusable merely because one sequence is erased.
- `state_write`, 2073–2143: selects occupied sequence cells, skips SWA-masked cells as applicable, writes metadata and tensor data.
- `state_write_data`, 2256–2354: serializes K/V layout and values; this standard KV implementation is inspected, other memory modules/hybrid model support remain unverified.
- `state_read_sinfo`, 2149–2221, checks stream count; `state_read_data`, 2535 onward, checks layer count, cell capacity, V transposition, rotation, type and row sizes. Insufficient capacity or incompatible layout can fail.

`llama/tools/server/server-context.cpp`:
- `prompt_save`/`prompt_load`, 308–340: in-memory target and optional draft sequence snapshots.
- `prompt_clear`, 343–349: `mem.seq_rm` then prompt metadata clear.
- New-task dispatch, 2883–2897: saves idle slot to prompt cache and clears it under unified KV.
- Slot save/restore/erase handlers, 2991–3147: only operate on idle slots (processing requests deferred), use sequence state file calls, return byte/time counters; save itself is not erase.
- `save_slot_checkpoints`, 2646–2684, appends prompt context checkpoints. `save_slot_draft`, 2745–2774, adds draft context and speculative state. Corresponding loaders may ignore/drop unavailable/incompatible appendices. Do not describe current server slot files as containing only main KV: these additions exist.
- `init_sampler`, 418–439, resets sampler and accepts prompt tokens. `launch_slot_with_task`, 1923–1948, creates sampler from request parameters. This is suitable to a newly declared turn, not a claim to preserve the random draw stream of an interrupted turn.

`llama/tools/server/README.md:168–170` documents bounded `--cache-ram` and `--cache-idle-slots` (requires cache RAM), with unified KV clearing. Lines 1155–1203 document save/restore/erase endpoints; example timing numbers are documentation examples and are **not used as measurements**.

## Complete-state inventory for the bounded text-only workload

| State | ServerlessLLM inspected migration | llama.cpp inspected sequence/slot save | What a correct experiment must preserve/check |
|---|---|---|---|
| Exact prompt and generated token IDs / positions | Token lists transferred; original request retained by router | Tokens in file; positions/sequence metadata in memory module | Exact tokenizer/chat template, token IDs and position policy |
| Main KV tensors | Reconstructed at target | Actually copied/restored | Exact model, adapters, context/RoPE, KV types/layout; ensure exclusive/reusable cells distinguished |
| RNG and sampler state | No transfer shown in token migration path | Absent from these serialization bodies | For interrupted stochastic generation preserve RNG, sampler chain/history, grammar/reasoning budget; alternatively define new-turn sampler semantics |
| Sampler state available elsewhere | Unverified | `common/sampling.cpp:112–135,518–528` has grammar, budget, chain, token history and RNG; in-process clone copies them. `src/llama-sampler.cpp:1124–1148,1240–1256` explicitly copies distribution RNG state | Clone is not a portable durable serialization promise. A repeated seed alone does not necessarily equal prior RNG position |
| Last logits/embeddings/output cursor | Unverified | Not in inspected sequence body or current whole-context body | At next-turn boundary tool result tokens need decoding anyway; arbitrary mid-token boundary may need a re-decode/extra state; test rather than assume |
| Draft/speculative/checkpoint state | Unverified | Current server appends draft/speculative/context checkpoints | Disable speculative decoding in smallest test, or validate compatible appendices and costs |
| Model weights and exact identity | Reinitialized target from same model config; source whole instance killed | Not exported; model object remains separate and resident | Pin full model content hash, tokenizer, adapter hashes and engine commit; reject mismatches before restore |
| Backend/device/allocator/graph | Target initialized separately | Restore into existing backend tensors; layouts checked partially | Same build/backend/config initially; cross-device/migration remains separate unverified scope |
| Application transcript, tool call IDs/result, task ownership/ACKs, cancellation/timeouts, external side effects | Request data shown, complete durable app checkpoint unverified | Not in inspected KV/slot serialization | Persist/replay by application; no duplicate tool execution, idempotence and exact result insertion |
| Shared weights physically released? | Source instance shutdown/kill requests release; actual device/cluster memory unmeasured | No; model owns buffers independently (`src/llama-model.cpp:1247–1267`), `llama_model_free` separately deletes model (3379–3381) | Count shared weights once; unload only if no users; include later load latency and page-cache retention |

Compatibility is **not** proven by successful deserialize alone. The sequence file path does not hash the model or compare its content. Whole-context checks architecture only plus lower-level state constraints, and even has a TODO for identity. Same-shaped different weights could pass structural checks yet yield wrong outputs; the application must enforce identity. Portable cross-commit or cross-backend support is unverified.

## Bounds and decision criterion (inferred, not benchmark results)

For ordinary non-shared standard KV, raw tensor bytes are approximately `K = N * sum_layers(dK*bK + dV*bV)` plus metadata; quantized types use actual row sizes, not this simple element-width formula. Sequence export may omit SWA-masked cells, and shared prefixes change marginal capacity. Use measured API serialized size and exclusive cell occupancy in an eventual run.

With wait `W`, export time `S`, resume restore time `R`, and actual releasable exclusive KV bytes `K_rel`, an optimistic wait-only memory-time saving is `K_rel * max(0, W-S)`. Relative to `K*W`, fraction is `(K_rel/K)*max(0,1-S/W)`. The proposed 25% gate is impossible if `K_rel/K < 0.25`; if all K is releasable and no other costs, it requires `W >= S/0.75`. This is an optimistic bound, not a model of page cache, duplication or whole-cycle occupancy. For inspected slot erase, physical allocated-buffer release is not established and should be zero for this operation; reusable-cell release can be nonzero.

End-to-end restore latency includes queueing, destination/context readiness, serialization/storage read, host-device transfer, validation, optional model load and tool-result prefill. Restore wins over token replay only if those incremental costs are below reconstruction with the same prompt and warm/cold state. Data traffic is at least exported tensor bytes out plus restored bytes in (apart from metadata), with extra staging copies shown in source. On-device snapshots keep tensors on device (`include/llama.h:930–932`) and must not be counted as physical GPU-memory release.

The 25% saving and 250-ms added-resume thresholds supplied by manager are **screening gates**, not real measurements or user SLOs. No numeric hardware parameters were available, so no performance outcome is claimed.

## Smallest follow-up and stop rule

Use one already available, authorized text model and the pinned engine (no download) in a matched same-host, two-session tool-turn experiment. Fix model/tokenizer/backend/config hashes; disable draft/speculative decoding, use greedy decoding first, supply identical recorded tool-result bytes, and pin the output boundary. Compare (1) resident cache, (2) token replay, (3) upstream slot save/erase/restore, and (4) built-in idle-slot RAM caching with unified KV and bounded cache RAM. Include one competing request while the other is idle; otherwise logical KV reuse has no capacity benefit.

Measure exported bytes, actual allocated VRAM/RSS, reusable cells, serialized-cache RAM/page-cache cost, full save and resume wall time, tool-result-prefill time and generated token equality. Validate restoration independently from the artifact into a newly created compatible context; negative tests: wrong model fingerprint, insufficient KV capacity, and absent application tool-result identity must fail at the appropriate layer. Use a separate validator and preserve failures. No need to construct a new suspend format before this test.

A useful first observation is whether existing idle caching already reuses enough cells without violating resume latency. If it does, recommend configuring/integrating upstream and stop the generic hypothesis. If only physical memory release is valuable, demonstrate a real release path (context/engine teardown or allocator reclaim) and charge reconstruction/model reload; slot erase cannot stand in for it. Without an authorized local model/backend, verdict stays UNRESOLVED for runtime advantage; source novelty objection remains supported.
