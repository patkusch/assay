import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
from label_bias import label_bias, markdown, worst_bias  # noqa: E402


def rows(pairs):
    """pairs: list of (truth, predicted)."""
    return [{"truth": t, "shuffled": {"top": p}} for t, p in pairs]


class LabelBiasTests(unittest.TestCase):
    def test_an_unbiased_model_has_ratio_one_for_every_label(self):
        # right half the time, but its mistakes are spread evenly: no favourite
        r = rows([("a", "a"), ("a", "b"), ("b", "b"), ("b", "a")])
        bias = label_bias(r, "shuffled")
        self.assertAlmostEqual(bias["a"]["ratio"], 1.0)
        self.assertAlmostEqual(bias["b"]["ratio"], 1.0)
        _, ratio = worst_bias(bias)
        self.assertAlmostEqual(ratio, 1.0)

    def test_a_favourite_default_shows_a_high_ratio_and_catchall_share(self):
        # 'billing' is only ever true once but predicted every time: classic catch-all
        r = rows([("billing", "billing"), ("technical", "billing"), ("sales", "billing"), ("cancel", "billing")])
        bias = label_bias(r, "shuffled")
        self.assertEqual(bias["billing"]["true_rate"], 0.25)
        self.assertEqual(bias["billing"]["predicted_rate"], 1.0)
        self.assertEqual(bias["billing"]["ratio"], 4.0)
        self.assertEqual(bias["billing"]["catchall_share"], 1.0)   # every wrong answer is 'billing'
        worst, ratio = worst_bias(bias)
        self.assertEqual(worst, "billing")
        self.assertEqual(ratio, 4.0)

    def test_a_label_never_predicted_is_not_a_bias(self):
        r = rows([("a", "b"), ("b", "b")])
        bias = label_bias(r, "shuffled")
        self.assertEqual(bias["a"]["predicted_rate"], 0.0)
        self.assertEqual(bias["a"]["ratio"], 0.0)   # under-predicted, not a "favourite"

    def test_markdown_names_the_worst_bias(self):
        r = rows([("billing", "billing"), ("technical", "billing"), ("sales", "billing")])
        bias = label_bias(r, "shuffled")
        md = markdown("m", "routing", "shuffled", 3, bias)
        self.assertIn("Biggest bias: `billing`", md)
        self.assertIn("3.00x", md)


if __name__ == "__main__":
    unittest.main()
