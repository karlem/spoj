"""Restricted HetRoute-inspired snapshot model; all inputs synthetic, no tensor/network run.

Implements printed Eq10 phases / Eq11 zero-lookahead gather selection. Explicit
extension: sum colocated expert work/loading, preexisting queue counted once.
No offline optimizer, approximate experts, adaptive prices, or emergency fallback.
"""
import itertools
import json
import random


def feasible(s, assignment):
    load = [0.] * len(s['compute'])
    for target, n in enumerate(assignment):
        if n not in s['eligible'][target]:
            return False
        load[n] += s['work'][target]
    return all(s['admitted'][n] + load[n] <= s['compute'][n] * s['window']
               for n in set(assignment))


def evaluate(s, assignment, bandwidth, fixed_aggregation=None):
    if not assignment:
        return {'latency': 0., 'aggregation': s['home'], 'participants': [],
                'fanout': 0., 'compute': 0., 'fanin': 0.}
    participants = sorted(set(assignment))
    transfer = lambda a, b, size: 0. if a == b else size / bandwidth[a][b]
    # Eq11 explicitly minimizes SUM gather cost, not Eq10 MAX gather delay.
    aggregation = (min(participants, key=lambda n:
                       (sum(transfer(m, n, s['out_bytes']) for m in participants), n))
                   if fixed_aggregation is None else fixed_aggregation)
    if aggregation not in participants:
        raise ValueError('aggregation must be a participating server')
    fanout = max(transfer(s['home'], n, s['in_bytes']) for n in participants)
    service = {}
    for n in participants:
        targets = [e for e, owner in enumerate(assignment) if owner == n]
        work = sum(s['work'][e] for e in targets)
        loading = sum(s['load_bytes'][e][n] / s['pcie'][n] for e in targets)
        service[n] = loading + (work + s['backlog'][n]) / s['compute'][n]
    compute = max(service.values())
    fanin = max(transfer(n, aggregation, s['out_bytes']) for n in participants)
    return {'latency': fanout + compute + fanin, 'aggregation': aggregation,
            'participants': participants, 'fanout': fanout, 'compute': compute,
            'fanin': fanin, 'server_service': service}


def key(s, a, bandwidth):
    return (evaluate(s, a, bandwidth)['latency'], tuple(a))


def exhaustive(s, bandwidth):
    choices = (a for a in itertools.product(*s['eligible']) if feasible(s, a))
    return min(choices, key=lambda a: key(s, a, bandwidth), default=None)


def refine(s, assignment, bandwidth):
    if assignment is None:
        return None
    current = tuple(assignment)
    while True:
        candidates = []
        for e, allowed in enumerate(s['eligible']):
            for n in allowed:
                candidate = current[:e] + (n,) + current[e+1:]
                if (feasible(s, candidate) and
                    key(s, candidate, bandwidth)[0] < key(s, current, bandwidth)[0]):
                    candidates.append(candidate)
        if not candidates:
            return current
        current = min(candidates, key=lambda a: key(s, a, bandwidth))


def beam(s, bandwidth, width=8):
    if width < 1:
        raise ValueError('beam width must be positive')
    partials = [()]
    for allowed in s['eligible']:
        expanded = [a + (n,) for a in partials for n in allowed
                    if feasible(s, a + (n,))]
        # Negative marginal D for common prefixes amounts to ranking next full D
        # only WITHIN a prefix. Across prefixes use total partial D, explicitly.
        partials = sorted(expanded, key=lambda a: key(s, a, bandwidth))[:width]
        if not partials:
            return None
    best = min(partials, key=lambda a: key(s, a, bandwidth))
    return refine(s, best, bandwidth)


def greedy(s, bandwidth):
    a = ()
    for e, allowed in enumerate(s['eligible']):
        choices = [n for n in allowed if feasible(s, a + (n,))]
        if not choices:
            return None
        def cost(n):
            network = 0. if n == s['home'] else s['in_bytes']/bandwidth[s['home']][n]
            # Eq9 independent candidate cost; no fan-in or layer-set coupling.
            return (network + s['load_bytes'][e][n]/s['pcie'][n] +
                    (s['work'][e]+s['backlog'][n])/s['compute'][n], n)
        a += (min(choices, key=cost),)
    return a


def scenario(rng, k=3):
    n = 3
    bandwidth = [[1e30 if a == b else rng.choice([1e6, 5e6, 20e6])
                  for b in range(n)] for a in range(n)]
    perceived = [row[:] for row in bandwidth]
    # Every stale observation is synthetic; no observer sees measured truth here.
    perceived[0][1] *= rng.choice([.1, 1., 10.])
    return {'home': 0, 'eligible': [list(range(n)) for _ in range(k)],
            'work': [rng.choice([1e5, 4e5, 1e6]) for _ in range(k)],
            'compute': [1e7, 3e7, 6e6], 'pcie': [1e8, 2e8, 1e8],
            'load_bytes': [[rng.choice([0., 1e6]) for _ in range(n)] for _ in range(k)],
            'backlog': [rng.choice([0., 5e5]) for _ in range(n)],
            'admitted': [rng.choice([0., 2e5]) for _ in range(n)], 'window': .1,
            'in_bytes': 4096., 'out_bytes': 4096.,
            'true_bandwidth': bandwidth, 'perceived_bandwidth': perceived}


def run(seed=1907, count=100):
    rng = random.Random(seed)
    stats = {p: {'model_infeasible': 0, 'search_failed_on_feasible_model': 0,
                 'completed': 0, 'signed_gap_sum_s': 0.,
                 'largest_gap_s': None, 'smallest_gap_s': None}
             for p in ['exact_true', 'exact_perceived', 'beam_perceived', 'greedy_perceived']}
    beam_misses = 0
    trace = None
    for i in range(count):
        s = scenario(rng)
        true, perceived = s['true_bandwidth'], s['perceived_bandwidth']
        best_true, best_perceived = exhaustive(s, true), exhaustive(s, perceived)
        selected = {'exact_true': best_true, 'exact_perceived': best_perceived,
                    'beam_perceived': beam(s, perceived),
                    'greedy_perceived': greedy(s, perceived)}
        decision_trace = {}
        if best_perceived is not None and (selected['beam_perceived'] is None or
            key(s, selected['beam_perceived'], perceived)[0] > key(s, best_perceived, perceived)[0]+1e-12):
            beam_misses += 1
        for p, a in selected.items():
            if a is None:
                stats[p]['model_infeasible' if best_true is None else
                         'search_failed_on_feasible_model'] += 1
                decision_trace[p] = {'assignment': None, 'aggregation': None}
            else:
                assert feasible(s, a) and len(a) == len(s['work'])
                observed = true if p == 'exact_true' else perceived
                predicted = evaluate(s, a, observed)
                aggregation = predicted['aggregation']
                realized = evaluate(s, a, true, fixed_aggregation=aggregation)
                regret = realized['latency']-evaluate(s, best_true, true)['latency']
                stats[p]['completed'] += 1
                stats[p]['signed_gap_sum_s'] += regret
                stats[p]['largest_gap_s'] = (regret if stats[p]['largest_gap_s'] is None
                                            else max(stats[p]['largest_gap_s'], regret))
                stats[p]['smallest_gap_s'] = (regret if stats[p]['smallest_gap_s'] is None
                                             else min(stats[p]['smallest_gap_s'], regret))
                decision_trace[p] = {'assignment': a, 'aggregation': aggregation,
                                     'realized_assumed': realized, 'predicted_assumed': predicted}
        if trace is None and selected['exact_true'] != selected['exact_perceived']:
            trace = {'snapshot_index': i, 'inputs_assumed': s,
                     'decisions': decision_trace}
    return {'status': 'restricted primary-source-inspired synthetic snapshot model',
            'seed': seed, 'snapshot_count': count, 'metrics_unit': 'one token, one MoE layer',
            'beam_width': 8, 'beam_perceived_cost_misses': beam_misses,
            'policy_summary': stats, 'one_bounded_trace': trace,
            'gap_definition': 'realized chosen route latency minus exact_true Eq11-constrained comparator; signed; sums over completed snapshots only, denominator is completed',
            'limits': ['not full HetRoute', 'no physical measurement or tensor execution',
                       'fixed fullprecision exact replicas', 'no fallback',
                       'per-server work/loading sum is an explicit Eq10 extension',
                       'beam ranks total partial D; paper tie/ordering details underspecified']}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, sort_keys=True))
