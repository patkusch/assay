"""Tests for calibration and metrics, on made-up data where the right answer is known."""
import math
import os
import random
import tempfile
import unittest

from assay.calibrate import TemperatureCalibrator
from assay.metrics import (
    accuracy, accuracy_at_coverage, brier, ece, nll, reliability_bins,
)

LABELS = ["a", "b", "c"]


def synth(n, seed, true_acc, stated_conf):
    """A model that is right `true_acc` of the time but always claims `stated_conf`."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        truth = rng.choice(LABELS)
        guess = truth if rng.random() < true_acc else rng.choice([l for l in LABELS if l != truth])
        rest = (1 - stated_conf) / (len(LABELS) - 1)
        out.append({"probs": {l: (stated_conf if l == guess else rest) for l in LABELS}, "truth": truth})
    return out


def synth_varied(n, seed, true_acc):
    """Confidence varies between samples; accuracy is fixed, so the model is overconfident when it says more."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        truth = rng.choice(LABELS)
        guess = truth if rng.random() < true_acc else rng.choice([l for l in LABELS if l != truth])
        conf = rng.uniform(0.5, 0.99)
        rest = (1 - conf) / 2
        out.append({"probs": {l: (conf if l == guess else rest) for l in LABELS}, "truth": truth})
    return out


class MetricTests(unittest.TestCase):
    def test_brier_perfect_is_zero(self):
        self.assertEqual(brier([{"probs": {"a": 1.0, "b": 0.0}, "truth": "a"}]), 0.0)

    def test_brier_hand_computed(self):
        # probs (0.7, 0.3), truth a: 0.3^2 + 0.3^2 = 0.18; probs (0.5, 0.5), truth b: 0.25 + 0.25 = 0.5
        s = [{"probs": {"a": 0.7, "b": 0.3}, "truth": "a"}, {"probs": {"a": 0.5, "b": 0.5}, "truth": "b"}]
        self.assertAlmostEqual(brier(s), (0.18 + 0.5) / 2)

    def test_brier_worst_case(self):
        self.assertAlmostEqual(brier([{"probs": {"a": 1.0, "b": 0.0}, "truth": "b"}]), 2.0)

    def test_nll_hand_computed(self):
        s = [{"probs": {"a": 0.5, "b": 0.5}, "truth": "a"}]
        self.assertAlmostEqual(nll(s), math.log(2))

    def test_nll_zero_probability_is_finite(self):
        self.assertTrue(math.isfinite(nll([{"probs": {"a": 1.0, "b": 0.0}, "truth": "b"}])))

    def test_accuracy(self):
        s = [{"probs": {"a": 0.9, "b": 0.1}, "truth": "a"}, {"probs": {"a": 0.9, "b": 0.1}, "truth": "b"}]
        self.assertEqual(accuracy(s), 0.5)

    def test_ece_perfectly_calibrated_toy_set(self):
        # ten answers all at 80% confidence, exactly eight right
        s = [{"probs": {"a": 0.8, "b": 0.2}, "truth": "a" if i < 8 else "b"} for i in range(10)]
        self.assertAlmostEqual(ece(s), 0.0)

    def test_ece_overconfident_toy_set(self):
        # ten answers at 90% confidence, only five right: gap of 0.4
        s = [{"probs": {"a": 0.9, "b": 0.1}, "truth": "a" if i < 5 else "b"} for i in range(10)]
        self.assertAlmostEqual(ece(s), 0.4)

    def test_reliability_bins(self):
        s = [
            {"probs": {"a": 0.55, "b": 0.45}, "truth": "a"},
            {"probs": {"a": 1.0, "b": 0.0}, "truth": "a"},
            {"probs": {"a": 0.95, "b": 0.05}, "truth": "b"},
        ]
        bins = reliability_bins(s, bins=10)
        self.assertEqual(len(bins), 10)
        self.assertEqual(sum(b["n"] for b in bins), 3)
        self.assertEqual(bins[5]["n"], 1)
        top = bins[9]
        self.assertEqual(top["n"], 2)  # 1.0 lands in the last bin
        self.assertAlmostEqual(top["mean_confidence"], 0.975)
        self.assertAlmostEqual(top["accuracy"], 0.5)
        self.assertEqual((top["lo"], top["hi"]), (0.9, 1.0))

    def test_accuracy_at_coverage(self):
        # confident ones are right, unsure ones are wrong
        s = [{"probs": {"a": 0.9, "b": 0.1}, "truth": "a"}] * 5 + [{"probs": {"a": 0.6, "b": 0.4}, "truth": "b"}] * 5
        out = accuracy_at_coverage(s, (1.0, 0.5, 0.4))
        self.assertAlmostEqual(out[1.0], 0.5)
        self.assertAlmostEqual(out[0.5], 1.0)
        self.assertAlmostEqual(out[0.4], 1.0)

    def test_empty_samples_error(self):
        with self.assertRaises(ValueError):
            brier([])


class CalibratorTests(unittest.TestCase):
    def test_overconfident_gets_T_above_one_and_lower_ece(self):
        samples = synth(600, seed=1, true_acc=0.70, stated_conf=0.95)
        cal = TemperatureCalibrator().fit(samples)
        self.assertGreater(cal.temperature, 1.0)
        r = cal.report
        self.assertLess(r["ece_after"], r["ece_before"])
        self.assertLess(r["ece_after"], 0.05)
        self.assertLess(r["nll_after"], r["nll_before"])
        self.assertLess(r["brier_after"], r["brier_before"])

    def test_underconfident_gets_T_below_one(self):
        samples = synth(600, seed=2, true_acc=0.90, stated_conf=0.60)
        cal = TemperatureCalibrator().fit(samples)
        self.assertLess(cal.temperature, 1.0)
        self.assertLess(cal.report["ece_after"], cal.report["ece_before"])

    def test_transform_sums_to_one_and_keeps_order(self):
        cal = TemperatureCalibrator().fit(synth(100, 3, 0.7, 0.95))
        out = cal.transform({"a": 0.9, "b": 0.07, "c": 0.03})
        self.assertAlmostEqual(sum(out.values()), 1.0)
        self.assertEqual(max(out, key=out.get), "a")
        self.assertLess(out["a"], 0.9)

    def test_identity_before_fit(self):
        cal = TemperatureCalibrator()
        p = {"a": 0.6, "b": 0.3, "c": 0.1}
        self.assertEqual(cal.transform(p), p)
        self.assertEqual(cal.prediction_set(p), ["a"])

    def test_prediction_set_never_empty_and_contains_top(self):
        cal = TemperatureCalibrator().fit(synth(100, 4, 0.7, 0.95))
        for p in ({"a": 0.34, "b": 0.33, "c": 0.33}, {"a": 1.0, "b": 0.0, "c": 0.0}):
            ps = cal.prediction_set(cal.transform(p))
            self.assertGreaterEqual(len(ps), 1)
            self.assertEqual(ps[0], "a")

    def test_unsure_input_gets_bigger_set_than_sure_input(self):
        cal = TemperatureCalibrator().fit(synth_varied(400, 5, 0.7), alpha=0.1)
        sure = cal.prediction_set(cal.transform({"a": 0.98, "b": 0.01, "c": 0.01}))
        unsure = cal.prediction_set(cal.transform({"a": 0.4, "b": 0.35, "c": 0.25}))
        self.assertGreaterEqual(len(unsure), len(sure))
        self.assertGreater(len(unsure), 1)

    def test_conformal_coverage_on_holdout_over_many_seeds(self):
        alpha = 0.1
        samples = synth_varied(300, 99, 0.7)
        coverages = []
        for seed in range(40):
            r = TemperatureCalibrator().fit_holdout(samples, alpha=alpha, seed=seed)
            coverages.append(r["coverage"])
            self.assertGreaterEqual(r["coverage"], 1 - alpha - 0.10)  # single split is noisy
        self.assertGreaterEqual(sum(coverages) / len(coverages), 1 - alpha - 0.02)

    def test_coverage_across_fresh_datasets(self):
        alpha = 0.2
        coverages = []
        for seed in range(40):
            samples = synth_varied(200, 1000 + seed, 0.6)
            coverages.append(TemperatureCalibrator().fit_holdout(samples, alpha=alpha, seed=seed)["coverage"])
        self.assertGreaterEqual(sum(coverages) / len(coverages), 1 - alpha - 0.02)

    def test_fit_holdout_reports_improvement(self):
        r = TemperatureCalibrator().fit_holdout(synth(600, 7, 0.7, 0.95), alpha=0.1, seed=1)
        self.assertEqual(r["n_fit"] + r["n_holdout"], 600)
        self.assertLess(r["ece_after"], r["ece_before"])
        self.assertGreaterEqual(r["avg_set_size"], 1.0)

    def test_fit_holdout_is_deterministic_per_seed(self):
        s = synth(200, 8, 0.7, 0.9)
        a = TemperatureCalibrator().fit_holdout(s, seed=3)
        b = TemperatureCalibrator().fit_holdout(s, seed=3)
        self.assertEqual(a, b)

    def test_report_keys(self):
        cal = TemperatureCalibrator().fit(synth(50, 9, 0.7, 0.9), alpha=0.2)
        for k in ("n", "T", "alpha", "qhat", "ece_before", "ece_after", "brier_before",
                  "brier_after", "nll_before", "nll_after", "avg_set_size"):
            self.assertIn(k, cal.report)
        self.assertEqual(cal.report["n"], 50)
        self.assertEqual(cal.report["alpha"], 0.2)

    def test_tiny_sample_error(self):
        with self.assertRaisesRegex(ValueError, "need at least 20 labelled examples"):
            TemperatureCalibrator().fit(synth(19, 1, 0.7, 0.9))
        with self.assertRaises(ValueError):
            TemperatureCalibrator().fit_holdout(synth(30, 1, 0.7, 0.9))

    def test_bad_alpha(self):
        with self.assertRaises(ValueError):
            TemperatureCalibrator().fit(synth(50, 1, 0.7, 0.9), alpha=1.5)

    def test_save_load_round_trip(self):
        cal = TemperatureCalibrator().fit(synth(200, 10, 0.7, 0.95), alpha=0.15)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cal.json")
            cal.save(path)
            back = TemperatureCalibrator.load(path)
        self.assertEqual(back.temperature, cal.temperature)
        self.assertEqual(back.qhat, cal.qhat)
        self.assertEqual(back.alpha, cal.alpha)
        self.assertEqual(back.report, cal.report)
        p = {"a": 0.5, "b": 0.3, "c": 0.2}
        self.assertEqual(back.transform(p), cal.transform(p))
        self.assertEqual(back.prediction_set(back.transform(p)), cal.prediction_set(cal.transform(p)))

    def test_json_round_trip_of_unfitted(self):
        back = TemperatureCalibrator.from_json(TemperatureCalibrator().to_json())
        self.assertFalse(back.fitted)
        self.assertEqual(back.prediction_set({"a": 0.2, "b": 0.8}), ["b"])


if __name__ == "__main__":
    unittest.main()
