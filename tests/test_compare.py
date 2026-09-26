import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import compare  # noqa: E402

V1 = ROOT / "bench" / "receipts" / "gemma3-4b.json"


@unittest.skipUnless(V1.exists(), "v1 receipts not present")
class CompareTests(unittest.TestCase):
    def test_a_run_compared_with_itself_has_no_gap(self):
        rows = compare.load(str(V1))
        ids = sorted(rows)
        a = [rows[i] for i in ids]
        obs, lo, hi = compare.boot(a, a, "shuffled", "shuffled", compare.d_acc, 200, random.Random(0))
        self.assertEqual((obs, lo, hi), (0.0, 0.0, 0.0))
        obs, lo, hi = compare.boot(a, a, "shuffled", "shuffled", compare.d_flip, 200, random.Random(0))
        self.assertEqual((obs, lo, hi), (0.0, 0.0, 0.0))

    def test_plain_answer_can_be_the_other_side(self):
        rows = compare.load(str(V1))
        self.assertTrue(all("plain" in r for r in rows.values()))
        a = list(rows.values())
        # accuracy of 'plain' minus accuracy of 'shuffled' equals the difference of the two headline numbers
        gap = compare.d_acc(a, a, "shuffled", "plain")
        acc = lambda c: sum(r[c][1] for r in a) / len(a)
        self.assertAlmostEqual(gap, acc("plain") - acc("shuffled"))

    def test_a_clear_gap_is_flagged_by_the_interval(self):
        good = [{"x": (0.9, 1), "task": "t"} for _ in range(90)] + [{"x": (0.9, 0), "task": "t"} for _ in range(10)]
        bad = [{"x": (0.9, 1), "task": "t"} for _ in range(60)] + [{"x": (0.9, 0), "task": "t"} for _ in range(40)]
        obs, lo, hi = compare.boot(bad, good, "x", "x", compare.d_acc, 500, random.Random(1))
        self.assertAlmostEqual(obs, 0.30)
        self.assertGreater(lo, 0)


if __name__ == "__main__":
    unittest.main()
