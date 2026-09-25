import json
import unittest
from pathlib import Path

from assay.backends.mock import KeywordBackend
from assay.server import run_request

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class ExampleTests(unittest.TestCase):
    def test_every_example_is_a_valid_request(self):
        files = sorted(EXAMPLES.glob("*.json"))
        self.assertGreaterEqual(len(files), 3)
        for f in files:
            body = json.loads(f.read_text())
            out = run_request(KeywordBackend(), body)
            self.assertEqual(set(out["answers"]), set(body["questions"]), f.name)
            for a in out["answers"].values():
                self.assertAlmostEqual(sum(a["probabilities"].values()), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
