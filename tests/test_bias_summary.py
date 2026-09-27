import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import bias_summary  # noqa: E402

RECEIPTS = [ROOT / "bench" / "receipts" / f for _, f in bias_summary.SYSTEMS]


class BiasSummaryTests(unittest.TestCase):
    def test_load_returns_none_for_a_missing_file(self):
        self.assertIsNone(bias_summary.load("does-not-exist.json"))

    @unittest.skipUnless(all(p.exists() for p in RECEIPTS), "v2 receipts not present")
    def test_main_writes_a_report_naming_the_routing_bias(self):
        bias_summary.main()
        out = ROOT / "bench" / "receipts" / "bias-summary.md"
        text = out.read_text()
        self.assertIn("Label bias summary", text)
        self.assertIn("routing", text)
        self.assertIn("billing", text)  # every system's biggest routing bias, at time of writing


if __name__ == "__main__":
    unittest.main()
