import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import longinput_eval as le  # noqa: E402
from assay import Question  # noqa: E402
from assay.longinput import ChunkedBackend  # noqa: E402


class WindowBackend:
    """Reads only the first 3000 characters, like a model with a short context, and picks the label word it sees there."""
    name = "window"

    def logprobs(self, state, question, labels):
        head = state[:3000].lower()
        return [3.0 if l in head else 0.0 for l in labels]


class LongInputEvalTests(unittest.TestCase):
    def test_filler_never_contains_a_word_a_task_cares_about(self):
        text = " ".join(le.FILLER).lower()
        spec = json.loads((ROOT / "bench" / "tasks_v2" / "tasks.json").read_text())
        for task, s in spec.items():
            for word in s["question"].get("options", []):
                self.assertNotIn(word.lower(), text, f"{task}: filler contains '{word}'")
        for word in ("password", "invoice", "refund", "outage", "delete", "phishing", "urgent", "cancel", "billing", "sales"):
            self.assertNotIn(word, text)

    def test_padding_keeps_the_original_text_and_reaches_the_length(self):
        rng = random.Random(0)
        for pos in le.POSITIONS:
            padded = le.pad("THE ITEM", pos, 6000, rng)
            self.assertIn("THE ITEM", padded)
            self.assertGreater(len(padded), 5500)
        self.assertTrue(le.pad("X", "before", 500, rng).endswith("X"))
        self.assertTrue(le.pad("X", "after", 500, rng).startswith("X"))

    def test_chunking_recovers_a_label_buried_past_the_models_window(self):
        inner = WindowBackend()
        chunked = ChunkedBackend(inner, max_chars=3000, overlap=300)
        q = Question("choice", "which?", options=["alpha", "beta", "gamma"])
        items = [{"id": f"i{n}", "state": "the answer is beta", "truth": "beta"} for n in range(6)]
        rows = le.evaluate(inner, chunked, items, q, pad_chars=9000, orders=1)
        s = le.summarise({"t": rows})["pooled"]
        self.assertEqual(s["short"], 1.0)
        # with filler BEFORE the item the plain window backend never sees it, so it cannot be right; chunking finds it
        self.assertLess(s["before_plain"], 1.0)
        self.assertEqual(s["before_chunked"], 1.0)
        self.assertEqual(s["after_chunked"], 1.0)

    def test_markdown_reports_all_three_numbers(self):
        rows = [{"id": "a", "truth": "x", "short": "x", **{f"{p}_{m}": "x" for p in le.POSITIONS for m in ("plain", "chunked")}}]
        summary = le.summarise({"t": rows})
        md = le.markdown({"backend": "keyword", "pad_chars": 100, "chunk_chars": 50}, "now", summary)
        self.assertIn("Padded, plain backend", md)
        self.assertIn("Padded, with chunking", md)


if __name__ == "__main__":
    unittest.main()
