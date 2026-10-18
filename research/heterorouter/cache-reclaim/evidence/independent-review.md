# Independent review of the provisional cache-reclaim packet

Reviewed frozen commit `af9d34c` in `/workspace/spoj`. Repository role was read-only; this file and the source-verification output are reviewer scratch artifacts. No engine/model execution, downloads, model fixtures, synthetic storage benchmark, product tests, OS changes, or GitHub writes occurred.

## Disposition

APPROVED for a provisional primary-source, readiness, bounds, and missing-experiment packet only. No blocking substantive findings. This is not approval of an inference optimization or an unperformed physical result.

One minor documentation correction: the production-reliability row in `skills-review.md` refers to `TCPSession.close/_terminate`, but the current session implementation has no `_terminate` method. Refer to `TCPSession.close` alone. Its cleanup implementation is not being changed by this packet.

## Independently executed checks

Executed:

`python research/heterorouter/cache-reclaim/verify_sources.py --engine-root /workspace/scratch/deep-mechanism/colibri --kernel-root /workspace/scratch/deep-mechanism/linux > /workspace/scratch/deep-mechanism/reviewer-source-verification.json`

Exit 0; all 54 manifest-listed files verified. The verifier establishes local file identity against retained sizes and SHA-256 hashes, not an independent upstream retrieval or runtime correctness.

Also checked `/workspace/karlem-skills` HEAD equals `c41b2b27c91da7155d555eb4946ece348ac08657` and independently compared all 44 installed skill source files against that checkout: sizes and SHA-256 values match the installation manifest. Eleven project-local skill folders and their assessment rows are present. Registry refresh is explicitly not claimed; offline upstream validation is correctly limited to structure/link/evaluation wiring, not effectiveness. The skill assessment maps the relevant questions to actual local proof/research boundaries rather than creating eleven new workstreams.

## Primary-source and bounds assessment

The packet accurately follows the selected engine's invocation, sparse expert routing, pin/LRU lookup, miss loading, owned slab/scales, consumer wait, weighted expert accumulation, and swap-based LRU promotion. Coalesced contiguous reads, parallel blocking or PIPE loads, existing mmap/direct/io_uring alternatives, cache-budget tuning and RSS guard are acknowledged as established controls. It does not claim they are missing features.

The distinction between original file-backed bytes and possibly planarized owned memory is correct. Read-only mmap is a real existing alternative; the packet does not assume identical storage layout or force a buffered baseline to obtain a favorable answer. Direct reads can fall back, synchronous scales remain buffered, and io_uring has its own per-completed-read advice path. Configured flags alone are not accepted as path evidence.

`g_drop = getenv("DROP") ? 1 : 0` at engine line 12621 confirms the presence trap. The protocol correctly uses an unset baseline and `DROP=1` treatment, never `DROP=0` as disabled. Advice is after completed reads and does not eliminate the copy/free slabs. Contiguous tensor geometry, unchecked advice returns, noncontiguous-span limits, partial-page behavior, filesystem overrides and possible ignored advice are properly disclosed.

Kernel v6.18.55 source at the pinned revision supports the stated generic DONTNEED behavior, including LRU drain/invalidation/retry and partial-page handling. The packet explicitly does not establish that this source exactly identifies the running kernel binary or the model filesystem's actual path.

The g64 byte formulas are correct for the declared matrix geometry: packed weights plus float32 group scales yield 4.5 effective bits/weight when dimensions are multiples of 64. Dimensions/content remain unknown, so no observed footprint is invented. Wrapper-call counts are not confused with short-read/EINTR syscall counts. Potential reclaim is bounded by unique resident file-page ranges, not summed logical reads. The Amdahl bound uses exclusive exposed affected time, and the packet correctly leaves its numerical value unset.

## Correctness and strongest-baseline gates

The protocol requires a permitted real container, pinned metadata/build, actual storage and resource topology, exact inputs, and an independent oracle for effective same-container quantized weights. The native replay explicitly discards logits and cannot serve as that oracle. The existing tiny random HF fixture does not qualify a trained g64 model. Strict teacher-forcing and timing are separate processes; replay/strict-mode incompatibility and REF_FORCE/calibration-generation conflicts are acknowledged rather than bypassed.

Strong baseline qualification explicitly includes applicable upstream tuning candidates, smaller cache budgets, mmap and direct I/O, and supported io_uring. If another existing path wins, the buffered-retention hypothesis is rejected for that regime. Only DROP changes after a buffered configuration is legitimately selected. Safety/controller actions are retained and measured rather than silently disabled.

The paired session unit, pilot exclusion, A/A controls, balanced order, failed preparation accounting, correlated token caveat, bootstrap uncertainty, perturbation check and bounded trace plan are appropriate for the stated missing experiment. None is represented as collected data. Prediction equality/finiteness and unchanged retained router decisions are a future quantized acceptance gate, not a claim of full floating-point identity today.

## Readiness and limitations

Inspected retained evidence distinguishes a four-core quota from five allowed vCPUs, cgroup memory from physical hardware, guest device labels from actual media, tmpfs from file-backed persistent storage, and logical byte counters from physical I/O. The disabled own-process userspace perf event opened successfully; this does not establish sampling or hardware-counter access. The retained strace readiness attempt failed with EPERM, and no tracing success is substituted. No artifact was found in accessible searched locations, and the reported model is larger than available workspace storage. The no-download constraint remains in force.

The numerical TCP transcript replay is correctly called historical offline validation, not fresh socket or storage performance evidence. No synthetic fixture or proxy result substitutes for the missing physical experiment. The packet's blocked classification is therefore justified.

## Independence disclosure

This review was performed by a separate read-only agent within the same session and shared workspace, not an external lab or independent physical reproduction. The actual serving model ID was not exposed and is not invented. Review approval concerns source reasoning and experimental boundaries; physical mechanism, quantitative benefit, assistant usefulness, native Mac acceptance, and any upstream contribution remain unproven.


## Affected-change addendum

Reviewed the working-tree changes after `af9d34c` only: README source-recovery/reproduction instructions, skills assessment correction, and authorized strace readiness evidence. No repository edits, source recovery downloads, engine/model execution or tests were performed by this reviewer.

The minor `_terminate` reference is resolved: the production-reliability row now names only `TCPSession.close`. The profiling row and README preserve the restricted EPERM failure while distinguishing the subsequently authorized own-child strace retry. The retained authorized JSON records exit 0 and the log shows dynamic-loader calls followed by successful process exit; this supports tracing readiness for `/bin/true` only, not model/storage profiling, sampling access, or unconditional permission in every execution context.

The added source-recovery commands use pinned repository content revisions and check expected byte lengths/SHA-256 before writing the recovered selected files. Verifier invocation and the 54-file scope match the independently executed check. Environment collection and package/IPC prerequisites are accurately separated from inference evidence. Dependency synchronization is presented as reproduction, not a new completed physical check.

No new blocking findings in these affected changes. Approval remains limited to the provisional source/readiness/bounds packet. The reported restricted product check failed and must remain recorded as failed; authorized IPC revalidation was still running at this review boundary, so this addendum makes no claim that the regression suite passed. No guard or numerical check change is implied or approved.


## Single-token oracle-path addendum

Reviewed only the newly tightened README/protocol correctness paragraphs against pinned engine source. The strict teacher-forcing branch calls `forward_all`, while timed replay calls `step` one token at a time and discards returned logits. `run_consist` compares the engine's batched and single-token paths to each other; it is not independent numerical evidence, and its relative-gap threshold/printed argmax flips cannot be relabeled as the existing Qwen float32 acceptance rule.

The added requirement for a separate bounded run retaining actual S=1 predictions and comparing them to an independent same-container oracle is appropriate. The missing observation hook and reference fixture are explicitly unimplemented gates, rather than silently counted as complete. Recording the real chat/control-token template also appropriately distinguishes valid task-shaped inputs from arbitrary in-range token IDs.

No new blocking issue in the source/bounds packet: its physical experiment is still blocked, now with the single-token correctness path made explicit. This does not approve an implementation of the hook, a model invocation, a relaxed oracle, or transfer of the Qwen tolerances. No engine or repository code was executed or changed for this addendum.


## Final generic buffered-read source and decision-memo addendum

Independently reran the source verifier after the kernel manifest addition: exit 0, 55 files verified. `mm/filemap.c` SHA-256 is `d459b729997e815900015e0ea6607ddf8667486f7aa6ce24403d4768beedbe92`, matching the retained manifest. The cited `filemap_get_pages`/`filemap_read` path and line 2811 `copy_folio_to_iter` support the generic cached-folio/read/copy explanation. README correctly distinguishes that generic source path from the untraced model filesystem, device and actual kernel binary.

The `IOCB_DONTCACHE` dropbehind observation is present in the inspected kernel source and is accurately limited to established kernel policy; the packet neither claims userspace availability or engine use nor adds a second intervention/performance result.

Reviewed `decision-memo.md` as a condensation of the prior approved packet. It preserves the blocked physical status, strongest baseline qualification, unset-DROP control, separate single-token oracle gate, missing hardware/artifact/performance inputs, and within-session review independence. No new substantive issue found. Approval remains for the source/readiness/bounds fallback only. No code, model or regression tests were run for this addendum.


## Final installation and validation-provenance addendum

Independently compared all 44 personal skill files under `/home/agent/.agents/skills` against the pinned installation manifest: sizes and SHA-256 hashes match. The personal MIT license matches the project-local license. The updated README and assessment correctly limit this installation to the current worker account, retain the branch-portable project copy, and do not claim that the host registry refreshed or that other workers received it.

Inspected `validation.json` and authorized-suite metadata: the required unchanged regression suite records exit 0 with 272 passed in 615.84 seconds at evaluated commit `af9d34c32cf6ea464705b6dae730fc130bcbce6f`. The earlier restricted-context suite failure remains recorded separately; neither is physical trained-model evidence. This reviewer inspected those metadata rather than independently rerunning the product suite.

Checked the retained source-verifier outputs: the initial reviewer snapshot reports 54 files, while the final reviewer and root verification outputs report 55. The metadata packaging mismatch and correction are explicitly recorded; the actual independently rerun final output is retained, not a relabeled initial result. No source or physical test failure was converted into a pass.

No new blocking findings. Provisional source/readiness/bounds approval remains unchanged, with model/strong-baseline/independent S=1 oracle/physical effect and native Mac gates still unrun. This addendum involved read-only metadata and file-identity checks only, with no engine/model execution, downloads or product tests.


## Linux-only collector guard addendum

Inspected only the new early platform guard in `collect_environment.py`. After argument parsing and before output-directory creation, commands or syscalls, it rejects `platform.system() != "Linux"` with `parser.error`. This prevents Linux syscall numbers from being issued on native macOS or other non-Linux hosts. It changes only the readiness helper, not the product-tested `spoi` implementation or checks.

No blocking finding in this change. Approval remains limited to collector safety by source inspection and the provisional packet. This reviewer did not execute a non-Linux test or rerun the collector; the parent retains the separate Linux rerun/hash evidence. Product regression results remain attributed to `af9d34c`, while publication must identify the later helper/documentation/evidence change rather than claiming the exact published helper ran in that earlier suite.

Final baseline clarification reviewed: both DROP states are existing upstream configurations; unset DROP is the controlled reference, the winning state belongs to the strongest upstream baseline, and B>A supports only a configuration region, not SPOJ superiority over Colibri. No remaining weak-baseline or novelty ambiguity in this clarification.
