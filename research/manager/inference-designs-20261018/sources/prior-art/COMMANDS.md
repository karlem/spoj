# Retrieval and inspection commands

All commands ran in `/workspace` using Python 3.12.14, available standard-library dependencies only. The scripts perform bounded HTTP reads (5 MiB maximum response, 25-second timeout, at most five concurrent fetches), retain SHA-256/time/URL metadata, and do not execute retrieved code.

Executed in order, each exited 0 (individual HTTP failures remain in the manifest):

```sh
python /workspace/scratch/inference-prior-art/fetch.py
python /workspace/scratch/inference-prior-art/fetch_more.py
python /workspace/scratch/inference-prior-art/fetch_final.py
python /workspace/scratch/inference-prior-art/fetch_pins.py
python /workspace/scratch/inference-prior-art/fetch_closure.py
```

`rg`/`sed` and local standard-library HTML stripping inspected abstracts, the Ring Attention architecture/overlap/inference appendix, Flash-Decoding's article, pinned project README files, SGLang fork/radix-cache/DCP source and documentation, Parrot semantic variables/executor/scheduler, vLLM DCP documentation, and Mamba/Mamba-2 recurrent cache/step functions. No retrieved program was imported or executed. Exact retrieval inputs are in the scripts; raw inputs and their hashes are in `manifest.json` and `SHA256SUMS`. This source-inspection task did not run product checks or inference benchmarks.

An earlier `mcp__codex_apps__search_service_web_run` request for Parrot and FlowServe returned empty content with `isError=true`; no result was used. The direct HTTP scripts replaced search discovery.

Final local integrity command:

```sh
cd /workspace/scratch/inference-prior-art
sha256sum -c SHA256SUMS
```
