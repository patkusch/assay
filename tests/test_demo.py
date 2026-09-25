import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import make_demo  # noqa: E402

RECEIPTS = [("von", ROOT / "bench" / "receipts" / "v2-von.json"), ("verdict", ROOT / "bench" / "receipts" / "v2-verdict.json")]


@unittest.skipUnless(all(p.exists() for _, p in RECEIPTS), "v2 receipts not present")
class DemoTests(unittest.TestCase):
    def test_page_is_self_contained_and_replays_the_receipts(self):
        data = make_demo.build(RECEIPTS)
        self.assertEqual(len(data["systems"]), 2)
        self.assertGreater(len(data["items"]), 800)
        for it in data["items"]:
            for s in data["systems"]:
                probs = it["s"][s["id"]]["b"]
                self.assertEqual(len(probs), len(data["tasks"][it["t"]]["labels"]))
                self.assertAlmostEqual(sum(probs), 1.0, delta=0.02)  # rounded to 3 places
            self.assertIn(it["y"], range(len(data["tasks"][it["t"]]["labels"])))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "index.html"
            sys.argv = ["make_demo", "--out", str(out)]
            make_demo.main()
            html = out.read_text()
        self.assertNotIn("/*DATA*/", html)
        self.assertNotRegex(html, r'src="https?://')          # nothing loaded from the network
        blob = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1)
        self.assertEqual(json.loads(blob)["taskOrder"], data["taskOrder"])

    def test_generator_refuses_receipts_from_another_item_set(self):
        v1 = ROOT / "bench" / "receipts" / "gemma3-4b.json"
        if not v1.exists():
            self.skipTest("v1 receipts not present")
        with self.assertRaises(SystemExit):
            make_demo.build([("gemma", v1)])


if __name__ == "__main__":
    unittest.main()
