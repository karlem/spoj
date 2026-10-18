# Sources and coverage

Book orientation: *Systems Performance: Enterprise and the Cloud*, 2nd edition (2020; copyright 2021); Brendan Gregg.

**Coverage: partial. No full-book conversion.**

Commercial full edition not available; official sample contains Chapter 3 Operating Systems plus front matter/index. Author web documentation supplies performance methods and profiling details. Sample TOC/index entries are not treated as chapter coverage.

## Evidence map

| Source | Supports / locator |
| --- | --- |
| [Systems Performance, 2nd Edition — author site](https://www.brendangregg.com/systems-performance-2nd-edition-book.html) | Edition, contents and authoritative companion navigation |
| [Systems Performance, 2nd Edition — publisher sample](https://www.informit.com/content/images/9780136820154/samplepages/9780136820154_Sample.pdf) | Chapter 3 Operating Systems, printed pp. 89–128, plus front matter and index; NOT CPU chapter text |
| [The USE Method — Brendan Gregg](https://www.brendangregg.com/usemethod.html) | Utilization, saturation, errors and resource-oriented investigation |
| [Flame Graphs — Brendan Gregg](https://www.brendangregg.com/flamegraphs.html) | Aggregated stack/event weights and flame graph interpretation |
| [Linux perf Examples — Brendan Gregg](https://www.brendangregg.com/perf.html) | Sampling, stack capture, counters, overhead and profiling examples |
| [Off-CPU Analysis — Brendan Gregg](https://www.brendangregg.com/offcpuanalysis.html) | Blocked-time stacks and limits of CPU-only evidence |
| [Active Benchmarking — Brendan Gregg](https://www.brendangregg.com/activebenchmarking.html) | Observe the benchmark and system while measuring performance |
| [Linux kernel pressure stall information](https://docs.kernel.org/accounting/psi.html) | some/full, rolling percentages, cumulative totals, system and cgroup scope |

## Attribution boundaries

These procedures, scenarios, code, and decision tables are original engineering
synthesis. They are not quotations, reproductions of book examples, or a substitute
for the cited books. A contents page verifies scope/identity only. Supplemental
implementation documentation supports the stated mechanisms, not claims about
unread book chapters. Context-dependent choices are recommendations, not guarantees.

Read the mechanisms reference relevant to the task; do not load all references
automatically. Source snapshots were accessed on 2026-10-18. Original URLs, observed
HTTP status, hashes, extraction methods, and acquisition failures are recorded in
the repository’s `sources/manifest.json`. No source license transfers to this library.

## Not covered

- Full book, CPU chapter prose, BPF/Ftrace chapters, exhaustive hardware/storage tuning
