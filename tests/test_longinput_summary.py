import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import longinput_summary  # noqa: E402

RECEIPTS = [ROOT / "bench" / "receipts" / f for _, f in longinput_summary.RUNS]


class LongInputSummaryTests(unittest.TestCase):
    @unittest.skipUnless(all(p.exists() for p in RECEIPTS), "long-input receipts not present")
    def test_main_writes_a_table_naming_every_mode(self):
        longinput_summary.main()
        text = (ROOT / "bench" / "receipts" / "longinput-summary.md").read_text()
        for label, _ in longinput_summary.RUNS:
            self.assertIn(label.split(" (")[0], text)
        self.assertIn("None beat doing nothing", text)


if __name__ == "__main__":
    unittest.main()
