import json
from pathlib import Path
import unittest
from architecture_model import evaluate, os_bound, run


class ArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(Path(__file__).with_name('inputs.json').read_text())

    def case(self, **changes):
        args=dict(cold=4,gpu_ms=.2,cpu_ms=2,line_gbit_s=100,flows=1,rtt_ms=.2)
        args.update(changes)
        return evaluate(self.config,**args)

    def test_dimensions_and_line_units(self):
        r=self.case()
        self.assertEqual(r['selected_weight_bytes_per_cold_layer'],168*2**20)
        self.assertEqual(r['activation_roundtrip_bytes'],16384)
        self.assertEqual(r['payload_bytes_per_second'],10**10)
        self.assertEqual(r['weight_staging_wire_bytes']/r['near_weights_wire_bytes'],10752)

    def test_zero_miss_no_network(self):
        r=self.case(cold=0)
        for name in ('weight_staging_lower_ms','weight_staging_serial_ms',
                     'near_weights_lower_ms','near_weights_serial_ms',
                     'coarse_layer_design_ms_feasibility_unverified'):
            self.assertEqual(r[name],9.6)
        self.assertEqual(r['near_weights_wire_bytes'],0)
        self.assertEqual(r['conditional_decision'],'no_robust_20pct_winner')

    def test_independent_hand_cell(self):
        r=self.case(cold=1)
        # Common dense + 31 local expert groups = 3.2 + 6.2 = 9.4 ms.
        self.assertAlmostEqual(r['weight_staging_lower_ms'],9.4+.2+17.6160768)
        self.assertAlmostEqual(r['near_weights_serial_ms'],9.4+.2+2+.0016384+.000682666666666667)

    def test_monotonic_link_rtt_and_sharing(self):
        baseline=self.case()
        for worse in (self.case(line_gbit_s=10),self.case(rtt_ms=1),self.case(flows=4)):
            for metric in ('weight_staging_lower_ms','weight_staging_serial_ms',
                           'near_weights_lower_ms','near_weights_serial_ms'):
                self.assertGreaterEqual(worse[metric],baseline[metric])

    def test_cpu_can_be_the_bottleneck(self):
        r=self.case(cold=32,gpu_ms=.05,cpu_ms=10,line_gbit_s=400,rtt_ms=.02)
        self.assertEqual(r['conditional_decision'],'no_robust_20pct_winner')
        self.assertGreater(r['near_weights_lower_ms'],r['weight_staging_lower_ms'])

    def test_whole_grid_invariants(self):
        results=run(self.config)
        self.assertEqual(results['case_count'],1620)
        for r in results['rows']:
            self.assertLessEqual(r['weight_staging_lower_ms'],r['weight_staging_serial_ms'])
            self.assertLessEqual(r['near_weights_lower_ms'],r['near_weights_serial_ms'])
            self.assertEqual(r['inference_correctness'],'unverified')

    def test_amdahl_gate(self):
        self.assertEqual(os_bound(.05,1)['latency_reduction_fraction'],.05)
        self.assertFalse(os_bound(.1,1)['meets_20pct_latency_gate'])
        self.assertTrue(os_bound(.2,1)['meets_20pct_latency_gate'])
        self.assertFalse(os_bound(.2,.9)['meets_20pct_latency_gate'])
        self.assertEqual(os_bound(.2,1)['speedup_upper_bound'],1.25)

    def test_invalid_parameters(self):
        for changes in ({'cold':33},{'cold':-1},{'line_gbit_s':0},
                        {'rtt_ms':float('nan')},{'flows':True},{'cpu_ms':-1}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):self.case(**changes)
        with self.assertRaises(ValueError):os_bound(1,1)


if __name__=='__main__':unittest.main()
