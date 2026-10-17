# Independent review and executed replay

Reviewer: independent read-only Codex agent tcp_contract_review, same Codex cloud/API harness; exact serving model identifier unavailable. No simultaneous writer or process test suite. Reviewed implementation c1fc09c, correction 7858fa6 and test-only lifetime fix 1193fcf8733ae73bde4ff3f18fdaf2c5c61932d7.

Initial finding P2: normal close suppressed invalid/missing shutdown acknowledgements and nonzero exits; terminal duplicate could be ignored. Corrected by collecting errors, completing bounded cleanup and rejecting normal exit while preserving a pre-existing failure. Added final duplicate, bad-stopped, nonzero-stop and stalled-shutdown checks. Independent re-review confirmed resolved, no additional blockers. Reviewer separately confirmed the module-fixture idle-timeout diagnosis and class-scoped correction without deadline/assertion changes.

Reviewer actually executed:

```sh
UV_CACHE_DIR=/workspace/.cache/uv UV_PROJECT_ENVIRONMENT=/workspace/spoj/target/tcp/fresh-1193fcf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --project spoi --frozen python -m spoi.verify_tcp_trace target/tcp/final-demo/trace.json
```

Observed exit 0; verified true, 33 frames, 14 contributions, 3 requests, 3 workers, maximum absolute error 0. Trace SHA256 0188250560dd213c9fa1173fadeab002cbf48f2e95976c794503a362f58b796a.

Reviewer independently inspected actual trace provenance (commit1193fcf, dirty=false, unchanged lock, exact guarded versions/source fingerprint, worker exitcodes [0,0,0]), actual JUnit (272 testcases, 0 failure/error/skipped, time606.978s), and four negative command logs (each exit1 for intended digest, numerical-parity or coverage rejection).

Final independent review APPROVED for the bounded local TCP milestone. Native Mac full/fresh acceptance remains outstanding. This is independent-agent source review and executed offline replay, not external human review or an independent audit of compiled PyTorch kernels. No multi-host, speedup, reduced total memory or full-model claim.
