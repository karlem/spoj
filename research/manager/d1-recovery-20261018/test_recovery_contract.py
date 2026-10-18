import json
import unittest

from run_fixture import run


class RecoveryContractTest(unittest.TestCase):
    def test_deterministic_contract(self):
        first = run()
        second = run()
        self.assertEqual(first, second)
        self.assertEqual(first["naive_duplicate_count"], 1)
        self.assertEqual(first["final_state"]["acked_index"], 3)
        self.assertEqual(len(first["final_state"]["client_accepts"]), 3)
        self.assertTrue(all(first["checks"].values()))
        json.dumps(first, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
