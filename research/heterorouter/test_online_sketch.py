"""Hand arithmetic and independent finite-model checks; stdlib unittest only."""
import itertools
import json
from pathlib import Path
import random
import unittest
import online_sketch as m


def hand(k=2):
    return {'home': 0, 'eligible': [[0, 1, 2] for _ in range(k)],
            'work': [1.] * k, 'compute': [1.] * 3, 'pcie': [1.] * 3,
            'load_bytes': [[0.] * 3 for _ in range(k)], 'backlog': [0.] * 3,
            'admitted': [0.] * 3, 'window': 100., 'in_bytes': 1., 'out_bytes': 1.}


def independent_oracle(s, b):
    """Literal tiny enumeration with independently written objective and guard."""
    scores = []
    for a in itertools.product(*s['eligible']):
        servers = sorted(set(a))
        work = {n: sum(s['work'][e] for e in range(len(a)) if a[e] == n) for n in servers}
        if any(work[n]+s['admitted'][n] > s['compute'][n]*s['window'] for n in servers):
            continue
        g = min(servers, key=lambda n: (sum(s['out_bytes']/b[x][n] for x in servers if x!=n), n))
        out = max([0.] + [s['in_bytes']/b[s['home']][n] for n in servers if n != s['home']])
        service = max((work[n]+s['backlog'][n])/s['compute'][n] +
                      sum(s['load_bytes'][e][n]/s['pcie'][n] for e in range(len(a)) if a[e]==n)
                      for n in servers)
        incoming = max([0.] + [s['out_bytes']/b[n][g] for n in servers if n != g])
        scores.append((out+service+incoming, a))
    return min(scores)[1] if scores else None


class Checks(unittest.TestCase):
    def test_unrelated_overloaded_server_does_not_block_route(self):
        s = hand(1)
        s['eligible'] = [[0]]
        s['admitted'][2] = 101.
        self.assertTrue(m.feasible(s, (0,)))

    def test_narrow_beam_can_miss_feasible_completion(self):
        s = hand(); s['eligible'] = [[0,1], [0]]; s['window'] = 1.
        b = [[1.] * 3 for _ in range(3)]
        self.assertEqual(m.exhaustive(s,b), (1,0))
        self.assertIsNone(m.beam(s,b,width=1))
        self.assertIsNone(m.greedy(s,b))
        self.assertEqual(m.beam(s,b,width=8), (1,0))

    def test_narrow_beam_local_optimum_can_be_suboptimal(self):
        fixture = json.loads(Path(__file__).with_name('beam-counterexample.json').read_text())
        s = fixture['inputs_assumed']; b = s['perceived_bandwidth']
        exact = m.exhaustive(s,b); narrow = m.beam(s,b,width=1)
        self.assertEqual(exact, (1,1,0))
        self.assertEqual(narrow, (0,1,1))
        self.assertAlmostEqual(m.evaluate(s,exact,b)['latency'], .0811648)
        self.assertAlmostEqual(m.evaluate(s,narrow,b)['latency'], .0911648)
        self.assertEqual(m.refine(s,narrow,b), narrow)

    def test_local_colocation_and_single_copy(self):
        s = hand(); b = [[1.] * 3 for _ in range(3)]
        self.assertEqual(m.evaluate(s, (0, 0), b)['latency'], 2.)
        self.assertEqual(m.evaluate(s, (1, 1), b)['latency'], 3.)
        s['eligible'] = [[0], [0]]
        self.assertEqual(m.exhaustive(s, b), (0, 0))

    def test_backlog_and_load_counted_correctly(self):
        s = hand(); b = [[1.] * 3 for _ in range(3)]
        s['backlog'][0] = 3.; s['load_bytes'] = [[2.,0.,0.], [4.,0.,0.]]
        self.assertEqual(m.evaluate(s, (0,0), b)['latency'], 11.)

    def test_joint_admission_and_infeasible(self):
        s = hand(); s['window'] = 1.
        self.assertTrue(m.feasible(s, (0,)))
        self.assertFalse(m.feasible(s, (0,0)))
        s['eligible'] = [[0],[0]]; b = [[1.] * 3 for _ in range(3)]
        self.assertIsNone(m.exhaustive(s,b)); self.assertIsNone(m.beam(s,b))

    def test_gather_sum_is_not_max(self):
        s = hand(3)
        # transfer-time matrix: column0 sum10/max9, column1 sum12/max6.
        times = [[0.,6.,8.], [1.,0.,8.], [9.,6.,0.]]
        b = [[1e30 if x==y else 1/times[x][y] for y in range(3)] for x in range(3)]
        e = m.evaluate(s, (0,1,2), b)
        self.assertEqual(e['aggregation'], 0)
        self.assertEqual(e['fanin'], 9.)
        self.assertEqual(min(range(3), key=lambda n: max(times[x][n] for x in range(3))), 1)
        self.assertEqual(e['latency'], 18.)

    def test_phases_are_barriers_not_branch_max(self):
        s = hand(3); s['backlog'][0] = 9.
        times = [[0.,10.,1.], [1.,0.,20.], [10.,20.,0.]]
        b = [[1e30 if x==y else 1/times[x][y] for y in range(3)] for x in range(3)]
        e = m.evaluate(s, (0,1,2), b)
        self.assertEqual(e['aggregation'], 0)
        self.assertEqual(e['latency'], 30.)
        self.assertLess(max(10.,10.+1.+1.,1.+1.+10.),e['latency'])

    def test_exact_independent_oracle_and_full_beam(self):
        rng = random.Random(72)
        for _ in range(50):
            s = m.scenario(rng); b = s['true_bandwidth']
            oracle = independent_oracle(s,b)
            self.assertEqual(m.exhaustive(s,b), oracle)
            self.assertEqual(m.beam(s,b,width=1000), oracle)

    def test_exchange_fixed_point(self):
        rng = random.Random(14)
        for _ in range(30):
            s = m.scenario(rng); b = s['true_bandwidth']; a = m.beam(s,b,width=1)
            if a is None: continue
            self.assertEqual(m.refine(s,a,b),a)
            for e, allowed in enumerate(s['eligible']):
                for n in allowed:
                    other = a[:e]+(n,)+a[e+1:]
                    if m.feasible(s,other):
                        self.assertGreaterEqual(m.evaluate(s,other,b)['latency'],m.evaluate(s,a,b)['latency'])

    def test_stale_decision_evaluated_against_same_truth(self):
        result = m.run(count=100)
        trace = result['one_bounded_trace']
        self.assertIsNotNone(trace)
        decisions = trace['decisions']
        self.assertNotEqual(decisions['exact_true']['assignment'],decisions['exact_perceived']['assignment'])
        self.assertGreater(result['policy_summary']['exact_perceived']['signed_gap_sum_s'],0.)
        self.assertEqual(result,m.run(count=100))

    def test_realized_keeps_perceived_aggregation(self):
        s = hand(2)
        observed = [[1.,1.,1.], [1.,1.,1.], [1.,10.,1.]]
        truth = [[1.,1.,1.], [1.,1.,10.], [1.,1.,1.]]
        chosen = m.evaluate(s,(1,2),observed)['aggregation']
        self.assertEqual(chosen,1)
        self.assertEqual(m.evaluate(s,(1,2),truth)['aggregation'],2)
        realized = m.evaluate(s,(1,2),truth,fixed_aggregation=chosen)
        self.assertEqual(realized['aggregation'],1)
        self.assertGreater(realized['fanin'],m.evaluate(s,(1,2),truth)['fanin'])


if __name__ == '__main__':
    unittest.main()
