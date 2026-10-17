# HetRoute primary-source review for SPOJ research issue #7

This extraction was written before the bounded sketch; its concluding proposed next step is historical. Executed results now appear in online-walkthrough.md.

Source: user-attached `1-2608.00577.pdf`; printed pages 1–15. Read the primary PDF's layout text and raw extraction of p.5. Equation references below follow the **printed PDF**, correcting stale internal references in its prose. This is a source review, not a reproduction or verification of paper performance.

## Identity and provenance correction

Printed p.1: **HetRoute: Heterogeneous and Cost-aware Collaborative Routing Framework for Distributed Edge MoE Inference**. Authors: **Xin Yuan, Ning Li, Wenchao Xu, Song Guo, Haijun Zhang** — five authors. Athanasios V. Vasilakos appears in one prior metadata mirror but **is not in this attachment's byline**. The attachment is authoritative for this review. Do not merge author lists across sources/versions. The PDF retains IEEE manuscript/template placeholders; do not describe it as accepted/published in an IEEE journal on that basis.

This resolves the prior primary-access blocker: the attached PDF is available locally even though direct arXiv requests were blocked. Earlier notes remain historical, not the current source status.

## Mathematical contract from the paper

**Deployment/state, pp.4–6, Sec.III.** `x[E,n]` says replica exists, `y[E,n]` says GPU-resident, with `y<=x`. A CPU replica has `x=1,y=0`; absent is `x=0`, not a CPU placement. Replica precision controls its size `v[E,n]` and profiled quality cost `q[E,n]`. GPU and CPU capacities are constraints c.1–c.2. Constraint c.4 requires at least one full-precision exact copy per expert. `F[n]` is FLOPs/s, `beta[n]` GPU–CPU bytes/s, directed `B[a,n]` inter-server bytes/s, `Q[n](t)` admitted GPU backlog in FLOPs.

**Targets and candidates, pp.4–5, Sec.III-B, Eq.5–7.** The learned gate produces fixed top-k target IDs. An actual execution is `(target E, executed expert Ehat, server n)`. Own-expert replicas are tried first; substitute experts from a similarity group are activated only if all exact candidates are inadmissible. One actual execution per target is c.7. Candidate servers may exceed k; participating servers cannot exceed k for one token/layer.

**Quality, p.5, Sec.III-C, Eq.8.** The budget quantity is an additive surrogate:

`Lambda_i = sum_over_layers_and_assignments [q(Ehat,n) + Qsub(E,Ehat)]`.

Quantization losses are profiled mean validation/KL changes on calibration data; exact full-precision execution is normalized to zero increment. The paper explicitly calls additivity a first-order approximation and checks task metrics empirically. A hard bound on this surrogate is **not a theorem bounding every token's actual task loss**, nor a tensor-parity guarantee.

**Per-assignment cost, p.5, Eq.9**, simplified notation:

`C(E,Ehat,n) = 1[n != theta]*d_in/B[theta,n] + (1-y[Ehat,n])*v[Ehat,n]/beta[n] + (w[Ehat]+Q[n])/F[n] + lambda_q*(q[Ehat,n]+Qsub(E,Ehat))`.

The expert is always GPU-computed; a CPU-resident copy incurs a load first. It is not CPU compute. Local transfer cost is zero. Explicit RTT/propagation, retransmissions and shared-link schedules do not appear in this equation.

**Layer latency, p.5, Eq.10** has three sequential phases:

`D = max_remote_fanout(d_in/B) + max_participating_server(load + compute_and_backlog) + max_remote_fanin(d_out/B)`.

This is a **sum of phase maxima**, not `max_over_branches(send+compute+return)` and not sum of individual expert costs. Different phases can attain their maxima at different servers. Same-destination input is sent once per participating server in this model. Aggregated output is one size `d_out` per branch. See unresolved multi-expert-on-one-server indexing below.

**Aggregation, p.5, Eq.11** selects the next residing server among participating servers:

`argmin_n [sum_{m in P excluding n} d_out/B[m,n] + one_step_next_layer_estimate(n)]`.

The text explicitly calls this heuristic; it does not optimize the complete multilayer trajectory. Zero lookahead is explicitly permitted. It minimizes a **sum** of gather transfer times, whereas Eq.10 includes a gather **maximum**; these are distinct criteria.

**Global objectives, pp.6–7, P0/P1 and Eq.12.** Ideal P0 minimizes total latency plus weighted quality, constrained by memory, exactly-once assignment, budget, and per-window compute capacity. P1 normalizes delay to a home-server full-precision reference and quality to its budget, weighted with weights summing to one. The paper says the two-stage method is a heuristic, not an exact joint solver. Online Sec.V instead states minimization of layer latency subject to guards; it does not provide a complete algebraic reconciliation of all these objectives.

## Offline Algorithm 1 — pp.7–8, Table I

Inputs: baseline experts and calibration traffic; GPU/CPU budgets; B/beta/F; precision set; replica cap; memory price mu.

1. Initialize a baseline deployment satisfying c.4 and all replicas CPU-resident (`Y=0`). Profile activation probabilities `pi[E]`.
2. Replay/simulate Algorithm 2 on calibration traffic to estimate the conditional probability `p_route[E,n]` that an activated expert uses each replica.
3. Eq.13, p.7: `g[E,n] = pi[E] * p_route[E,n] * v[E,n]/beta[n]`. Greedily promote positive-benefit replicas to GPU in descending g order while fitting capacity.
4. For absent replicas and each allowed precision, evaluate Eq.14: `b[E,n] = E_cal[C_old(E) - C_new(E,n)] - mu*v[E,n]`. Insert the feasible largest positive b, repeat until cap, no positive improvement, or capacity stop.
5. Recompute residency benefits and greedily reassign GPU residency globally. Diminishing-returns guard permits a second GPU copy of an expert only if its marginal g exceeds the best not-yet-resident distinct expert. Return X/Y/precisions/exact candidate lists.

Important limits: this is a heuristic. Greedy maximum g subject to variable replica sizes is not a general knapsack-optimal algorithm, despite p.8 prose saying it maximizes expected saving. Input baseline feasibility, transient GPU load workspace, exact recalibration/recomputation order, and how replicas' runtime selection probabilities change during insertions need implementation choices. The claimed sorting complexity O(|E|N), p.8, omits general comparison-sort cost and calibration replay/search cost.

## Online Algorithm 2 — pp.8–10, Table II

1. Start each token at its home server with accumulated surrogate degradation zero; process layers/tokens, obtain gate top-k.
2. For each target, construct its own-replica candidates. Prune by Eq.18 quality `Lambda_acc + delta <= Lambda_max` and Eq.19 workload `W[n]+w[Ehat] <= F[n]*Delta_t`. Only if no exact candidate remains, try its substitutes under the same guards. Union surviving servers gives the collaboration domain.
3. Local fast path: all targets have local GPU copies, local queue below threshold, and local cost provably no greater than a remote-branch lower bound. Assign local only if these conditions hold. The construction of that lower bound is not fully specified.
4. Small search: enumerate feasible complete assignments. Large search: beam of width B, expanded by negative marginal layer latency, Eq.20 `phi = -(D(partial plus assignment)-D(partial))`; then single-target 1-exchange improvement.
5. If no feasible complete assignment, use full-precision exact fallback, keeping the quality guard but relaxing the normal workload guard and queueing work. The prose describes the intent; table behavior has an important gap noted below.
6. Choose aggregation per Eq.11, scatter/execute/gather, update quality/backlog. Update component prices by projected feedback Eq.21, p.9: `alpha_j <- positive_part(alpha_j + eta*(rho_j-rhobar_j)) / sum_h positive_part(alpha_h + eta*(rho_h-rhobar_h))`.

P.11 evaluation settings: **beam width 8**, **exact-enumeration threshold 64 complete candidate assignments**, default quality budget 2%, replica-memory ratio 2.0. These are verified paper settings, not an instruction to adopt the quality-changing features in SPOJ.

## Guarantees and material implementation ambiguities

1. **Co-located experts, Eq.10 p.5 versus Sec.V-B p.8.** The compute maximum is indexed by server n but retains a single executed expert Ehat in load/work terms. It does not explicitly sum work or loads over multiple targets assigned to that server. Text explicitly says such targets compete on the server. A simulator must resolve this; silently summing is a reasonable **stated extension**, not a literal reproduction of Eq.10.
2. **Joint quality/load feasibility.** Candidate guards alone are insufficient. Two targets can each cost .6 of the remaining quality budget, so both pass individually and their pair fails. Similarly each of two jobs can fit a server separately but exceed its remaining capacity jointly. Complete/partial search must check summed increments/reservations, counting existing backlog once per server.
3. **Fallback gap, p.9 Table II lines24–27.** It tests no feasible *complete* assignment, but its fallback loop only fills targets with *no admissible candidate*. If all candidate sets are nonempty yet every combination violates a coupled guard, that loop has no affected target and specifies no full completion. E.g. remaining quality1, each target's surviving low-precision choices cost.6, while full-precision choices were stability-pruned. This contradicts an unconditional literal-pseudocode reading of completion; an implementation needs an explicit repair policy/all-exact fallback.
4. **Reachability versus existence.** Property1 p.10 infers fallback is reachable from a deployed full-precision copy. Deployment alone does not imply the host/link remains reachable, especially since reachability is mentioned during pruning. The guarantee needs live, reachable fallback, enough execution workspace and eventual service. Stability relaxation ensures routing assignment, **not bounded completion time** under sustained overload, crash or partition.
5. **Search threshold inconsistency.** TableII p.9 and Sec.V-B test collaboration-domain size `|C_i,l| <= Rbar^k`; Property3 p.10 uses the *product* of per-target candidate counts; p.11 evaluation says 64 *assignments*. Domain cardinality does not bound the product as asserted. Use actual product size for a declared 64-assignment implementation; document that interpretation.
6. **Exact optimality scope, Property3 p.10.** Exhaustive evaluation is optimal for the explicitly defined per-layer feasible objective/candidate set/current snapshot, provided implementation really enumerates all combinations. It is not optimal for deployment, cross-token queues, future layers or physical runtime. Exact-first pruning itself restricts candidates.
7. **Beam and local optimality, Property4 pp.10–11.** Finite strict-improvement 1-exchange terminates and is locally optimal only when run until no improving feasible neighbor remains. Complexity proof p.11 assumes a constant number of sweeps; a fixed sweep cap does not in general establish that local optimum. No global approximation ratio is supplied. The proof also repeats a small-domain cardinality bound while discussing the larger domain.
8. **Incremental-cost complexity.** The O(1) marginal-evaluation assumption in Property5 must account for aggregation selection and shared-server maxima updates; it is not supplied as implementation. A tiny exact simulator should recompute transparently rather than claim these asymptotics.
9. **Objective/price coupling.** Eq.9 uses lambda_q, Eq.10 contains latency only, Eq.12 has normalized weights, and Eq.21 updates alpha components not visibly present in Eq.9/10. No complete executable rule shows how adaptive prices alter the stated D-only online selection. Also specify what happens if all projected Eq.21 weights sum to zero. Do not invent a linkage and attribute it to the paper.
10. **Model/measurement gap.** Eq.9/10 omit explicit RTT despite p.11 setup reporting .3–22ms propagation-plus-queueing; shared-link contention, packet framing, lost packets, observation age/error, and detailed window/backlog updates are not executable specifications. Source code/configs/traces are not linked in the PDF text inspected. Report model outputs separately from measured network latency.
11. **Quality guarantee scope.** Full-precision identical experts are zero in the surrogate by normalization. Lower precision and substitute experts deliberately permit quality change. The first-order profiled additive bound does not establish unchanged HF tensors; task-metric closeness reported on p.12 is empirical.
12. **Document consistency.** Many internal references point to old equation numbers (e.g. D cited as Eq.8 instead of10, aggregation as9 instead of11), headings mention exit-head/skip-exit though the presented algorithms concern placement/routing, and TableII repeats line numbers/goto labels. Cite printed equations, not these stale prose numbers. These are reasons to make adaptations reviewable, not grounds to dismiss the research.

## Bounded simulation subset proposed for the separate stream

One token/layer, fixed hypothetical full-precision identical replicas, fixed placement/residency, fixed current backlog/workload snapshot and directed bandwidth matrix. Gate targets remain fixed; all quality increments zero. Start with Eq.11's explicitly permitted zero-lookahead case. Compare exhaustive complete-assignment enumeration (ground truth for the chosen finite model), independent greedy choices, and marginal beam + 1-exchange; compare selected assignments under perceived versus realized parameters later.

Declared simulator interpretation: sum work and nonresident loading for all assigned targets per server; count preexisting queue once; phase barriers and fanout/fanin dedup per Eq.10; empty remote maxima zero. This resolves an underdefined equation openly. Keep Eq.11 sum-gather aggregation separate from Eq.10 max-gather latency and show when they disagree. Define deterministic ties and recheck joint capacity after each partial assignment. Return infeasible explicitly; do not pretend the incomplete fallback has been reproduced.

Exclude offline optimizer, substitution/quantization, adaptive prices, fallback, model tensor execution, actual sockets, physical machines and performance claims. This is a restricted paper-inspired model, not full HetRoute or a substitute for SPOJ numerical correctness. The old per-job EFT simulator remains a generic bootstrap, not this model.

Hand-checkable cases before comparisons:

- k=1 and one eligible copy: all methods choose it; local transfer zero.
- Two local targets: one fanout copy and compute sum; increasing second expert work must increase layer compute.
- Different servers dominate different phases: sum-of-maxima exceeds max-of-branch-sums; assert the intended definition.
- Two individually feasible targets collectively exceed capacity: reject the combination.
- All normal choices infeasible: explicit infeasible result; no fake completion.
- Asymmetric directed links: reversing direction changes fan-in correctly.
- Three candidate aggregation servers: construct sum-gather versus max-gather disagreement to expose Eq.11 heuristic.
- Tiny full Cartesian product: beam retaining every prefix equals enumeration. Deliberately narrow beam may lose optimum; retain the counterexample rather than promising equivalence.
- 1-exchange strict improvements reach a fixed point checked by enumerating every one-target neighbor; no fixed-sweep local-optimum claim.
- Every selected target appears exactly once; participating-server count <=k; all outputs retain assumed-versus-measured provenance.

No new derived simulator has been implemented in this review. The next step is to agree the explicit interpretation of ambiguities and keep it visible alongside eventual simulation results.
