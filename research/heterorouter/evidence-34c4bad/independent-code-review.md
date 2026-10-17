# Independent executable research review

Reviewed frozen commit 34c4bad in /workspace/spoj, read-only repository inspection. Source: online_sketch.py, test_online_sketch.py, online-results.json, beam-counterexample.json, online-walkthrough.md and prior primary-source analysis. No repository edits, worker/socket/model tests or full repository suite executed by this reviewer.

## Outcome

APPROVED for the documented restricted synthetic snapshot model. No blocking findings. This does not approve inference integration or reproduce author experiments.

## Independently executed validation

`python -m unittest discover -s research/heterorouter -p 'test_online_sketch.py' -v`: exit 0; 12 tests passed.

Executed `python research/heterorouter/online_sketch.py` via subprocess and parsed stdout; exit 0. Complete decoded JSON exactly matched checked-in online-results.json. Independently asserted each policy completed + model-infeasible + search-failed count equals 100. Every policy completes 99, reports one model-infeasible and zero search-failed snapshots. No latency benefit is obtained by silently omitting failed work.

Separately reconstructed all four snapshot6 route scores with Python Fraction arithmetic, without importing or calling online_sketch.evaluate. Verified chosen aggregation remains fixed when switching bandwidth truth. Predicted/realized milliseconds match walkthrough: exact_true49.971733/49.971733; exact_perceived and beam59.858667/52.485867; greedy60.621333/53.248533. Verified 0-to-1 observed500000 versus true5000000 B/s and unchanged reverse1000000 B/s.

## Code assessment

feasible sums work for the current prefix and tests only participating servers, so an unrelated overloaded server no longer invalidates routes. Prefix pruning is valid for the fixed nonnegative work/admission inputs. exhaustive enumerates the full eligible product with deterministic tuple ties and uses the same declared aggregation heuristic as its comparator contract. beam ranks total partial cost, not a falsely attributed fully specified paper beam; it can discard feasible/global-optimal completions, with retained counterexamples. refine accepts strictly decreasing feasible moves and terminates on this finite domain at a one-exchange fixed point; there is no unjustified capped-sweep/local-optimality claim.

run selects assignment and gather using perceived parameters for perceived policies, then reevaluates that same assignment AND gather against assumed true bandwidth. True bandwidth does not affect those policy choices. Model feasibility is bandwidth-independent here, making true-exact existence a valid model-infeasibility classifier. Signed gap is honestly restricted to the Eq11-constrained exact comparator rather than universal nonnegative regret. Seeds, finite input distribution, full JSON and bounded worked trace make the documented run reproducible.

The math implements Eq11 SUM gather selection and Eq10 three phase maxima with explicitly declared co-located-work/loading sums and queue-once extension. Units are compatible. Inputs are internal synthetic positive rates/nonnegative workloads; this is not a validated external-input API or physical measurement model. No author implementation, full algorithm, quality substitution, feedback, temporal queue evolution, network execution or HF numerical parity is claimed.
