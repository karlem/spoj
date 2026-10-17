# Restricted online sketch validation

Executed commands, cwd `/workspace/scratch/heterorouter-research`:

```
python -m unittest discover -s /workspace/scratch/heterorouter-research -p test_online_sketch.py -v
python /workspace/scratch/heterorouter-research/online_sketch.py
```

Final exits: both 0. Nine tests passed; retained log `online-tests.log`; deterministic run output `online-results.json`. Root independent review remains pending.

Initial test run had 7 passes and 1 failure: `test_phases_are_barriers_not_branch_max`, assertion `aggregation == 0` observed actual `2`. The intended fixture accidentally made column2 gather sum cheaper than column0. Changed the fixture's link time from server1 to server2 from9 to20, making the hand-intended destination0 actually minimize Eq11. No model formula or tolerance was changed to satisfy the mistaken expectation. The raw initial output was returned in the tool transcript; this paragraph retains that failure evidence because it was not redirected to a file at the time.

Root review found an actual early implementation error before publication: realized evaluation recomputed the aggregation destination from true bandwidth, leaking truth into the route. Corrected by fixing the destination selected under each policy's own observation. Added a directed-link regression where perceived/truth destinations differ. Exact-true prediction uses true parameters; the other policies use perceived parameters. Both predicted and realized trace keep each chosen destination.

100 seeded synthetic snapshots (seed1907): all policies complete99; 1 model-infeasible snapshot; no heuristic search failures on feasible snapshots in this small sample. Width8 beam has0 observed perceived-cost misses. This does not establish beam optimality outside the sample. Latency differences versus exact-true **with Eq11 aggregation heuristic enforced** sum to0.0076341333333333344s for exact-perceived/beam-perceived, and0.5397813333333332s for independent greedy. Maximum gaps: .0032768s and .030s respectively. Sums are over99 completed snapshots each; no failed/infeasible result is included as zero latency.

The difference is a **signed gap**, not guaranteed nonnegative regret: Eq11 minimizes sum-gather but Eq10 uses max-gather, so a route choosing aggregation from stale information could theoretically beat the true-parameter comparator's aggregation under Eq10. The exact-true comparator enumerates assignments while enforcing Eq11; it does not jointly optimize every assignment/aggregation pair. Current sampled smallest gaps are0.

Declared beam interpretation: rank total partial-layer cost across prefixes, rather than compare only marginal costs from differing baselines; widths/ties/order are explicit. This is a transparent paper-inspired implementation choice, not verified reproduction of unspecified author code. Refinement runs until no strict feasible single-target improvement remains. No bounded-sweep local-optimality claim.

No physical latency, actual TCP, model tensors, quality-changing execution, offline placement, fallback, or adaptive feedback is validated here. Primary review documents the exact scope and equation extensions.


## Parent verification and independent review

Root added three checks: unrelated already-overloaded servers must not invalidate a route to another server; narrow beam can lose the only feasible completion; and a retained width-1/1-exchange local optimum is 10ms worse than exhaustive search. The first check failed before a targeted admission fix (`for n in set(assignment)` rather than all servers). The observed exit-1 output is retained in evidence-34c4bad/admission-regression-before-fix.log. All 12 tests then passed; complete JSON still matched the researcher run. Independent reviewer separately ran the 12 tests, reran JSON and recomputed the walkthrough with rational arithmetic; see evidence-34c4bad/independent-code-review.md.
