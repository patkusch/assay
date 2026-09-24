"""Tests for the Von and Verdict adapters (bench/adapters).

Two layers:
  * plumbing tests use a fake worker script, so they always run and need no clone, no model and no network;
  * live tests run the real projects and skip cleanly unless the clones, their venvs and cached weights are present
    (they live in assay-clones/, or wherever ASSAY_CLONES points).
"""
import json
import math
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT / "src"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from assay.types import BackendError, Question  # noqa: E402
from bench.adapters._subproc import FLOOR, WorkerBackend, clones_dir  # noqa: E402
from bench.adapters.verdict import VerdictBackend  # noqa: E402
from bench.adapters.von import VonBackend  # noqa: E402

FAKE_WORKER = r'''
import json, sys
print(json.dumps({"ready": True}), flush=True)
for line in sys.stdin:
    req = json.loads(line)
    n = len(req["labels"])
    if req["state"] == "boom":
        print(json.dumps({"ok": False, "error": "ValueError: nope"}), flush=True)
    elif req["state"] == "short":
        print(json.dumps({"ok": True, "probs": [1.0]}), flush=True)
    else:
        probs = [0.0] + [1.0 / (n - 1)] * (n - 1)      # first label gets exactly zero
        print(json.dumps({"ok": True, "probs": probs, "truncated": req["state"] == "long", "descriptions": req["descriptions"],
                          "abstain_p": 0.1}), flush=True)
'''


def make_fake(tmp: Path) -> Path:
    (tmp / "fake" / ".venv" / "bin").mkdir(parents=True)
    (tmp / "workers").mkdir()
    (tmp / "fake" / ".venv" / "bin" / "python").symlink_to(sys.executable)
    (tmp / "workers" / "fake_worker.py").write_text(FAKE_WORKER)
    return tmp


class FakeBackend(WorkerBackend):
    name = "fake"
    repo_dir = "fake"
    worker_file = "fake_worker.py"


CHOICE = Question(type="choice", instructions="pick", options=["a", "b", "c"])
SCORE = Question(type="score", instructions="rate", levels=4)
NOUL = Question(type="noul", instructions="is it?")


class PlumbingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.b = FakeBackend(make_fake(Path(self.tmp.name)))
        self.addCleanup(self.b.close)
        self.addCleanup(self.tmp.cleanup)

    def test_probabilities_become_floored_log_probabilities(self):
        lp = self.b.logprobs("x", CHOICE, CHOICE.labels())
        self.assertEqual(len(lp), 3)
        self.assertAlmostEqual(lp[0], math.log(FLOOR))          # a probability of exactly 0 is floored, never -inf
        self.assertAlmostEqual(lp[1], math.log(0.5))

    def test_worker_is_kept_alive_across_calls(self):
        self.b.logprobs("x", NOUL, NOUL.labels())
        pid = self.b.proc.pid
        self.b.logprobs("y", NOUL, ["no", "yes"])
        self.assertEqual(self.b.proc.pid, pid)
        self.assertEqual(self.b.calls, 2)

    def test_truncation_and_abstain_are_recorded(self):
        self.b.logprobs("long", CHOICE, CHOICE.labels())
        self.b.logprobs("short text", CHOICE, CHOICE.labels())
        self.assertEqual(self.b.truncated_items, 1)
        self.assertEqual(self.b.abstain_mass, [0.1, 0.1])

    def test_worker_error_and_bad_length_raise_backend_error(self):
        with self.assertRaises(BackendError):
            self.b.logprobs("boom", CHOICE, CHOICE.labels())
        with self.assertRaises(BackendError):
            self.b.logprobs("short", CHOICE, CHOICE.labels())

    def test_missing_clone_raises_backend_error(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(BackendError):
                FakeBackend(Path(empty)).logprobs("x", CHOICE, CHOICE.labels())

    def test_score_levels_use_the_template(self):
        self.assertEqual(self.b.descriptions(SCORE, SCORE.labels()), ["1", "2", "3", "4"])
        worded = FakeBackend(Path(self.tmp.name), level_template="Level {label} of {levels}")
        self.assertEqual(worded.descriptions(SCORE, ["2", "1"]), ["Level 2 of 4", "Level 1 of 4"])
        self.assertEqual(self.b.descriptions(CHOICE, CHOICE.labels()), ["a", "b", "c"])


def _weights_cached(fragment: str, filename: str) -> bool:
    """True only when the finished download is present (a half-finished one leaves no file under snapshots/)."""
    hub = clones_dir() / ".hf-cache" / "hub"
    return hub.exists() and any(True for d in hub.glob(f"models--{fragment}/snapshots/*/{filename}"))


@unittest.skipUnless(VonBackend().installed() and _weights_cached("wfzyx--von", "option_marker.pt"), "Von clone/venv/weights not installed")
class VonLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = VonBackend()

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def test_easy_items_and_all_three_question_types(self):
        # only the shape is asserted for every type; one very clear phishing email also checks the direction
        cases = [
            (Question(type="noul", instructions="Is this email a phishing attempt?"),
             "From: it@c0mpany-support.top\nSubject: Verify now\n\nSend us your password to keep your mailbox.", "yes"),
            (Question(type="choice", instructions="Which team should handle this?", options=["billing", "technical", "cancel"]),
             "I was charged twice this month, please refund one of the payments.", None),
        ]
        for q, state, want in cases:
            labels = q.labels()
            lp = self.b.logprobs(state, q, labels)
            self.assertEqual(len(lp), len(labels))
            self.assertTrue(all(math.isfinite(x) and x <= 0 for x in lp))
            if want:
                self.assertEqual(labels[lp.index(max(lp))], want)
        s = Question(type="score", instructions="Rate the urgency 1 to 5: 5 = production is down.", levels=5)
        self.assertEqual(len(self.b.logprobs("All customers get 503 errors, production is down.", s, s.labels())), 5)

    def test_order_does_not_matter_for_von(self):
        q = Question(type="choice", instructions="Which team should handle this?", options=["billing", "technical", "cancel"])
        state = "The API returns an empty list although the web page shows my projects."
        fwd = dict(zip(q.labels(), self.b.logprobs(state, q, q.labels())))
        rev = dict(zip(reversed(q.labels()), self.b.logprobs(state, q, list(reversed(q.labels())))))
        for l in q.labels():
            self.assertAlmostEqual(fwd[l], rev[l], delta=0.01)


@unittest.skipUnless(VerdictBackend().installed() and _weights_cached("heman10x--rlcd-modernbert-151m", "model.safetensors"),
                     "Verdict clone/venv/weights not installed")
class VerdictLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = VerdictBackend()

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def test_all_three_question_types_return_one_score_per_label(self):
        for q in (Question(type="noul", instructions="Is this email a phishing attempt?"),
                  Question(type="choice", instructions="Which team should handle this?", options=["billing", "technical", "cancel"]),
                  Question(type="score", instructions="Rate the urgency 1 to 5.", levels=5)):
            lp = self.b.logprobs("I was charged twice this month, please refund one of the payments.", q, q.labels())
            self.assertEqual(len(lp), len(q.labels()))
            self.assertTrue(all(math.isfinite(x) and x <= 0 for x in lp))

    def test_long_state_is_counted_as_truncated(self):
        q = Question(type="noul", instructions="Is this email a phishing attempt?")
        before = self.b.truncated_items
        self.b.logprobs("padding " * 800 + "send your password", q, q.labels())
        self.assertEqual(self.b.truncated_items, before + 1)


if __name__ == "__main__":
    unittest.main()
