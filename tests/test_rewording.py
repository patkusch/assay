import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import rewording  # noqa: E402
from assay.backends.mock import KeywordBackend  # noqa: E402

# terms every wording must keep, so a reworded question never changes what the labels mean
MUST_KEEP = {
    "phishing": ["password", "payment", "personal data"],
    "command_safety": ["safe", "risky", "destructive", "dry run", "shared history", "permissions", "system-wide", "permanently", "disk", "database"],
    "routing": ["billing", "technical", "sales", "cancel", "other", "invoice", "refund", "tax", "payment method", "demo", "discount", "subscription", "press", "jobs", "privacy"],
    "urgency": ["1", "2", "3", "4", "5", "workaround", "deadline", "outage", "data loss", "security"],
}
# ideas that may be phrased more than one way: every wording must use at least one phrase from each group
ANY_OF = {"urgency": [["facts", "actually happening"]]}


class Sensitive:
    """A stand-in model whose answer depends on the wording, to prove the test can see wording effects."""
    name = "sensitive"

    def logprobs(self, state, question, labels):
        h = sum(map(ord, question.instructions)) % len(labels)
        return [3.0 if l == labels[0] else 0.0 for l in sorted(labels)] if h == 0 else [float(i == h) * 3 for i in range(len(labels))]


class RewordingTests(unittest.TestCase):
    def test_every_wording_keeps_the_label_definitions(self):
        words = json.loads((ROOT / "bench" / "rewordings.json").read_text())
        spec = json.loads((ROOT / "bench" / "tasks_v2" / "tasks.json").read_text())
        for task, texts in words.items():
            self.assertEqual(len(texts), 3, task)
            for text in [spec[task]["question"]["instructions"]] + texts:
                low = text.lower()
                for term in MUST_KEEP[task]:
                    self.assertIn(term, low, f"{task}: '{term}' missing from: {text[:70]}")
                for group in ANY_OF.get(task, []):
                    self.assertTrue(any(g in low for g in group), f"{task}: none of {group} in: {text[:70]}")
            self.assertEqual(len(set(texts)), 3, f"{task}: duplicate wordings")

    def test_a_model_that_ignores_wording_never_changes_its_answer(self):
        r = rewording.run(KeywordBackend(), per_task=10, orders=2, tasks_dir=ROOT / "bench" / "tasks_v2", names=["routing"])
        s = rewording.summarise(r)
        self.assertEqual(s["pooled"]["answer_changed_with_wording"], 0.0)
        self.assertEqual(s["pooled"]["accuracy_spread"], 0.0)

    def test_a_model_that_reacts_to_wording_is_caught(self):
        r = rewording.run(Sensitive(), per_task=15, orders=1, tasks_dir=ROOT / "bench" / "tasks_v2", names=["phishing", "routing"])
        s = rewording.summarise(r)
        self.assertGreater(s["pooled"]["answer_changed_with_wording"], 0.0)
        self.assertIn("Rewording test", rewording.markdown({**r, "config": {"backend": "sensitive", "orders": 1}, "timestamp": "t"}, s))


if __name__ == "__main__":
    unittest.main()
