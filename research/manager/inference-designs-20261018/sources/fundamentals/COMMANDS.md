# Retrieval, inspection, and publication record

Worker `/root/inference_fundamentals`; run `inference-designs-20261018-1841`.
Owned path: `/workspace/scratch/inference-fundamentals`. Read-only repository
instructions came from `/workspace/spoj-inference-designs/{AGENTS.md,
docs/engineering/factory.md,research/manager/README.md}`.

## What ran

1. Read the repository instructions with `cat`.
2. Created this scratch directory with `mkdir -p`.
3. Fetched the pinned skills README, nine targeted SKILL.md files, 17 focused
   references, source coverage, and license using Python 3 standard-library
   `urllib.request.urlopen`, with 20–30 second timeouts and per-response limits of
   2–4 MiB. Independent fetch batches used up to four threads. The inherited proxy
   configuration was used without bypass. Exact URLs, timestamps, sizes, HTTP
   results, and SHA-256 fingerprints are in `provenance.json`.
4. Fetched three relevant primary sources. Two guessed Roofline endpoints failed,
   and one OSTI URL returned the wrong paper; those records remain in provenance.
   The wrong paper was identified by reading its extracted title and excluded.
5. Inspected original Markdown/RST with `cat`, `sed -n`, and `rg -n`.
6. `command -v pdftotext` returned `/usr/bin/pdftotext`. Extracted PDFs locally:

   ```text
   pdftotext -layout raw-primary/linearizability.pdf raw-primary/linearizability.txt
   pdftotext -layout raw-primary/roofline-osti.pdf raw-primary/roofline-osti.txt
   pdftotext -layout raw-primary/roofline-berkeley.pdf raw-primary/roofline-berkeley.txt
   ```

7. Read the identified paper sections described in the report. No paper code,
   external repository scripts, installer, model, or benchmark was executed.
8. Recomputed SHA-256 for all 33 successful retrieved bodies and compared them
   with the acquisition manifest. All matched. Downloaded bodies total 5,220,278
   bytes (about 4.98 MiB), including the excluded unrelated paper. Parsed text is
   additional scratch data, still far below the 100 MiB artifact limit.
9. Checked that each short quotation in `public-evidence.json` occurs in the
   corresponding source after whitespace normalization. All seven matched.

A web search tool call returned `isError: true` and empty content; no results
were used. Retrieval failures are acquisition events, not failed implementation
attempts or failed performance experiments. No product check or inference
experiment ran in this worker; the manager owns repository validation.

## Reproduction and limitations

For successful records, retrieve `record.url`, hash the response bytes with
`hashlib.sha256`, and compare against `record.sha256`. Skill URLs include the
exact commit `c41b2b27c91da7155d555eb4946ece348ac08657`. Primary HTTP URLs other than
Linux's release-tag URL are rolling locations; hashes identify the actual bodies
read. A different future body is not a reproduced snapshot. HTTP 200 alone is not
source identity validation, as the retained OSTI mismatch demonstrates.

No paid downloads, books, external code execution, repository installation,
remote machine access, product changes, or host configuration changes occurred.
This is original analysis of retrieved sources, not independent validation of
the complete skills library or a measurement of the proposed engine.

## Publication set

Copy only these files to the research packet:

- `REPORT.md`
- `provenance.json`
- `public-evidence.json`
- `COMMANDS.md`
- `KARLEM-SKILLS-LICENSE`
- `MANIFEST.sha256`

The fetched papers, their full extracted text, and full skill/reference snapshots
remain in scratch. The license is retained for original MIT-licensed skills
material; it does not change the licenses of linked source material.
