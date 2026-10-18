import unittest
from cost_model import GIB, evaluate, kv_bytes


class EconomicBoundTests(unittest.TestCase):
    def case(self, **changes):
        args = dict(size_bytes=GIB, tokens=8192, wait_s=1,
                    write_gib_s=8, read_gib_s=8, prefill_tokens_s=100000,
                    domain='separate', allocator_releases=True)
        args.update(changes)
        return evaluate(**args)

    def policy(self, result, name):
        return next(p for p in result['policies'] if p['policy'] == name)

    def test_gqa_bytes(self):
        self.assertEqual(kv_bytes(32, 8, 128, 2, 8192), GIB)
        self.assertEqual(kv_bytes(32, 8, 128, 2, 32768), 4*GIB)

    def test_hand_calculated_snapshot(self):
        r = self.case()
        p = self.policy(r, 'snapshot')
        self.assertEqual(r['export_seconds'], .13)
        self.assertEqual(p['added_resume_seconds'], .13)
        self.assertEqual(p['physical_saved_gib_s'], .87)
        self.assertEqual(p['kv_transfer_bytes'], 2*GIB)
        self.assertTrue(p['physical_economic_candidate'])
        self.assertFalse(p['accepted_inference_result'])

    def test_return_during_export(self):
        p = self.policy(self.case(wait_s=.05), 'snapshot')
        self.assertEqual(p['physical_saved_gib_s'], 0)
        self.assertEqual(p['added_resume_seconds'], .21)
        self.assertFalse(p['slot_economic_candidate'])

    def test_same_domain_has_no_physical_saving(self):
        p = self.policy(self.case(domain='same'), 'snapshot')
        self.assertTrue(p['slot_economic_candidate'])
        self.assertEqual(p['physical_saved_gib_s'], 0)
        self.assertEqual(p['source_domain_payload_peak_bytes'], 2*GIB)
        self.assertFalse(p['physical_economic_candidate'])

    def test_preallocated_pool_has_no_physical_saving(self):
        for p in self.case(allocator_releases=False)['policies']:
            self.assertEqual(p['physical_saved_gib_s'], 0)
            self.assertFalse(p['physical_economic_candidate'])

    def test_replay_accounts_for_prefill_and_overhead(self):
        p = self.policy(self.case(), 'replay')
        self.assertEqual(p['added_resume_seconds'], .10192)
        self.assertEqual(p['post_return_kv_reservation_gib_s_upper_bound'], .10192)
        self.assertTrue(p['physical_economic_candidate'])
        self.assertEqual(p['kv_transfer_bytes'], 0)
        self.assertFalse(self.policy(self.case(prefill_tokens_s=2000), 'replay')
                         ['physical_economic_candidate'])

    def test_exact_threshold_and_adjacent_failure(self):
        args = dict(wait_s=1, write_gib_s=2, export_fixed_s=.25,
                    read_gib_s=4, restore_fixed_s=0)
        p = self.policy(self.case(**args), 'snapshot')
        self.assertEqual(p['physical_saving_fraction'], .25)
        self.assertEqual(p['added_resume_seconds'], .25)
        self.assertTrue(p['physical_economic_candidate'])
        args['wait_s'] = '.999999999999999999'
        self.assertFalse(self.policy(self.case(**args), 'snapshot')
                         ['physical_economic_candidate'])

    def test_incompatible_state_never_qualifies(self):
        for p in self.case(compatible=False)['policies']:
            self.assertFalse(p['physical_economic_candidate'])
            self.assertFalse(p['slot_economic_candidate'])
            self.assertEqual(p['correctness'], 'incompatible_metadata')

    def test_invalid_inputs_rejected(self):
        for key, value in [('wait_s', 0), ('wait_s', float('nan')),
                           ('write_gib_s', 0), ('read_gib_s', float('inf')),
                           ('prefill_tokens_s', -1), ('tokens', True),
                           ('size_bytes', 1.5), ('allocator_releases', 1),
                           ('min_saving', 1.1), ('domain', 'unknown')]:
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    self.case(**{key:value})


if __name__ == '__main__':
    unittest.main()
