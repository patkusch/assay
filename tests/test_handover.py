"""The hand-over: a small model answers when sure, a bigger one takes the rest."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))

from assay import Question, Request, decide  # noqa: E402
from assay.backends.mock import KeywordBackend  # noqa: E402
from assay.handover import decide_with_handover  # noqa: E402
from assay.pretty import format_answers  # noqa: E402
from assay.server import run_request  # noqa: E402
import handover as bench  # noqa: E402


class Flat:
    """Has no idea: every label gets the same score, so confidence is 1/n."""
    name = "flat"

    def logprobs(self, state, question, labels):
        return [0.0 for _ in labels]


class Sure:
    """Always picks 'b', strongly."""
    name = "sure"

    def logprobs(self, state, question, labels):
        return [8.0 if l == "b" else 0.0 for l in labels]


REQ = Request("anything", {"q": Question("choice", "Which?", options=["a", "b", "c"])})


class Engine(unittest.TestCase):
    def test_unsure_small_model_hands_the_question_up(self):
        r = decide_with_handover(Flat(), Sure(), REQ, below=0.8)
        a = r.answers["q"]
        self.assertEqual((a.value, a.answered_by), ("b", "sure"))
        self.assertGreater(a.confidence, 0.95)
        self.assertEqual(r.model, "flat, then sure when unsure")

    def test_sure_small_model_keeps_its_answer_and_the_big_model_is_never_asked(self):
        class Never(Sure):
            name = "never"

            def logprobs(self, *a):
                raise AssertionError("the big model was asked")
        a = decide_with_handover(Sure(), Never(), REQ, below=0.8).answers["q"]
        self.assertEqual((a.value, a.answered_by), ("b", "sure"))

    def test_the_cut_off_decides(self):
        # Flat's confidence is exactly 1/3; a cut-off at or under that keeps its answer
        self.assertEqual(decide_with_handover(Flat(), Sure(), REQ, below=0.3).answers["q"].answered_by, "flat")
        self.assertEqual(decide_with_handover(Flat(), Sure(), REQ, below=0.34).answers["q"].answered_by, "sure")
        with self.assertRaises(ValueError):
            decide_with_handover(Flat(), Sure(), REQ, below=1.5)

    def test_a_failing_big_model_says_so_plainly(self):
        from assay.types import BackendError

        class Down:
            name = "down"

            def logprobs(self, *a):
                raise BackendError("connection refused")
        with self.assertRaisesRegex(BackendError, "flat was not sure about 'q' and the hand-over model down failed: connection refused"):
            decide_with_handover(Flat(), Down(), REQ)
        # when the small model is sure, the big one is never called, so it can be down without harm
        self.assertEqual(decide_with_handover(Sure(), Down(), REQ).answers["q"].answered_by, "sure")

    def test_plain_answers_do_not_carry_an_answered_by_field(self):
        d = decide(KeywordBackend(), REQ).answers["q"].to_dict()
        self.assertNotIn("answered_by", d)
        d = decide_with_handover(Flat(), Sure(), REQ).answers["q"].to_dict()
        self.assertEqual(d["answered_by"], "sure")

    def test_server_path_and_pretty_view(self):
        body = {"state": "anything", "questions": {"q": {"type": "choice", "instructions": "Which?", "options": ["a", "b", "c"]}}}
        out = run_request(Flat(), body, handover=(Sure(), 0.8))
        self.assertEqual(out["answers"]["q"]["answered_by"], "sure")
        self.assertIn("answered by sure", format_answers(out, {"q": "Which?"}))


    def test_each_model_gets_its_own_calibration(self):
        class Flatten:  # a stand-in calibrator that halves every edge, so we can see it was applied
            def transform(self, probs):
                return {k: 0.5 * p + 0.5 / len(probs) for k, p in probs.items()}

            def prediction_set(self, probs):
                return [max(probs, key=probs.get)]
        body = {"state": "anything", "questions": {"q": {"type": "choice", "instructions": "Which?", "options": ["a", "b", "c"]}}}
        big_cal = {"q": Flatten()}
        handed = run_request(Flat(), body, handover=(Sure(), 0.8, big_cal))["answers"]["q"]
        self.assertEqual(handed["answered_by"], "sure")
        self.assertTrue(handed["calibrated"])
        self.assertLess(handed["confidence"], 0.95)  # the big model's odds were flattened by its own calibration
        kept = run_request(Sure(), body, handover=(Flat(), 0.8, big_cal))["answers"]["q"]
        self.assertFalse(kept["calibrated"])  # the small model's answer is not touched by the big model's calibration


class OverHttp(unittest.TestCase):
    def test_the_server_hands_over_too(self):
        import threading
        import urllib.request
        from assay.server import make_server
        srv = make_server(Flat(), port=0, handover=(Sure(), 0.8))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            body = json.dumps({"state": "anything", "questions": {"q": {"type": "choice", "instructions": "Which?", "options": ["a", "b", "c"]}}}).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/v1/systemone", data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                out = json.loads(r.read())
            self.assertEqual(out["answers"]["q"]["answered_by"], "sure")
            self.assertEqual(out["model"], "flat, then sure when unsure")
        finally:
            srv.shutdown()
            srv.server_close()


class Cli(unittest.TestCase):
    def test_decide_with_handover_flag(self):
        r = subprocess.run([sys.executable, "-m", "assay", "decide", "--backend", "keyword", "--handover", "keyword",
                            "--handover-below", "0.5", "--state", "billing billing billing",
                            "--question", "choice:Which team?:billing|sales"],
                           capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src"), "PATH": ""})
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["answers"]["q1"]["answered_by"], "keyword")
        self.assertEqual(out["model"], "keyword, then keyword when unsure")

    def test_handover_calibration_flag_is_accepted(self):
        env = {"PYTHONPATH": str(ROOT / "src"), "PATH": ""}
        with tempfile.TemporaryDirectory() as d:
            req, labelled, cal = Path(d) / "req.json", Path(d) / "labelled.jsonl", Path(d) / "big.json"
            req.write_text(json.dumps({"state": "spam spam", "questions": {"q1": {"type": "choice", "instructions": "Which?", "options": ["spam", "ham"]}}}))
            rows = []
            for i in range(30):  # the words say one thing; one row in five is labelled the other way, so the fit has work to do
                word = "spam" if i % 2 == 0 else "ham"
                truth = ("ham" if word == "spam" else "spam") if i % 5 == 0 else word
                rows.append(json.dumps({"question": "q1", "state": f"{word} {word}", "truth": truth}))
            labelled.write_text("\n".join(rows) + "\n")
            fit = subprocess.run([sys.executable, "-m", "assay", "calibrate", "--backend", "keyword", "--request", str(req),
                                  "--labelled", str(labelled), "--out", str(cal)], capture_output=True, text=True, env=env)
            self.assertEqual(fit.returncode, 0, fit.stderr)
            r = subprocess.run([sys.executable, "-m", "assay", "decide", "--backend", "keyword", "--handover", "keyword", "--handover-below", "0.99",
                                "--handover-calibration", str(cal), "--request", str(req)], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            a = json.loads(r.stdout)["answers"]["q1"]
            self.assertEqual((a["answered_by"], a["calibrated"]), ("keyword", True))  # handed up, and the big model's calibration applied


class BenchScript(unittest.TestCase):
    small = {"i1": dict(task="t", correct=1, confidence=0.9, unsure=False, ms=100.0),
             "i2": dict(task="t", correct=0, confidence=0.4, unsure=True, ms=100.0),
             "i3": dict(task="t", correct=0, confidence=0.6, unsure=False, ms=100.0),
             "i4": dict(task="t", correct=1, confidence=0.95, unsure=False, ms=100.0)}
    big = {k: dict(task="t", correct=1, confidence=0.99, unsure=False, ms=400.0) for k in small}

    def test_hand_over_by_rule(self):
        alone = bench.hand_over(self.small, self.big, lambda s: False)
        self.assertEqual((alone["accuracy"], alone["share_handed"], alone["ms_per_item"]), (0.5, 0.0, 100.0))
        unsure = bench.hand_over(self.small, self.big, lambda s: s["unsure"])
        self.assertEqual((unsure["accuracy"], unsure["share_handed"], unsure["ms_per_item"]), (0.75, 0.25, 200.0))
        below = bench.hand_over(self.small, self.big, lambda s: s["confidence"] < 0.7)
        self.assertEqual((below["accuracy"], below["share_handed"]), (1.0, 0.5))
        self.assertEqual((below["small_right_on_handed"], below["big_right_on_handed"]), (0.0, 1.0))
        self.assertIsNone(alone["small_right_on_handed"])

    def test_random_hand_over_matches_the_ends(self):
        self.assertEqual(bench.random_hand_over(self.small, self.big, 0.0), 0.5)
        self.assertEqual(bench.random_hand_over(self.small, self.big, 1.0), 1.0)

    def test_sweep_and_markdown(self):
        rows = bench.sweep(self.small, self.big)
        self.assertEqual([r["rule"] for r in rows][:2], ["small model alone", "hand up when not sure"])
        self.assertEqual(rows[-1]["rule"], "big model alone")
        md = bench.markdown(rows, "tiny", "huge", "calibrated")
        self.assertIn("| small model alone | 0.0% | 50.0% | -50.0 (-100.0 to +0.0) | 50.0% | 0.10 s | n/a | n/a |", md)
        self.assertIn("| big model alone | 100.0% | 100.0% | +0.0 (+0.0 to +0.0) | 100.0% | 0.50 s | 50.0% | 100.0% |", md)
        self.assertEqual(rows[-1]["gap_interval"], (0.0, 0.0))

    def test_own_cutoffs(self):
        rows = bench.sweep(self.small, self.big, (0.5, 0.95))
        self.assertEqual([r["rule"] for r in rows], ["small model alone", "hand up when not sure", "hand up below 50%", "hand up below 95%", "big model alone"])
        bad = bench.main([str(ROOT / "bench/receipts/v2-gemma3-4b.json"), str(ROOT / "bench/receipts/v2-gemma3-12b.json"), "--cutoffs", "1.5"])
        self.assertEqual(bad, 2)

    def test_gap_interval_brackets_the_gap_and_is_zero_width_for_identical_lists(self):
        a, b = [1, 0, 1, 1, 0, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1]
        lo, hi = bench.gap_interval(a, b, draws=400)
        self.assertLessEqual(lo, -0.25)
        self.assertLessEqual(-0.25, hi)
        self.assertEqual(bench.gap_interval(b, b, draws=50), (0.0, 0.0))

    def test_runs_on_the_real_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            out = str(Path(d) / "h")
            rc = bench.main([str(ROOT / "bench/receipts/v2-gemma3-4b.json"), str(ROOT / "bench/receipts/v2-gemma3-12b.json"), "--out", out])
            self.assertEqual(rc, 0)
            rows = json.loads(Path(out + ".json").read_text())["rows"]
            self.assertEqual(rows[0]["n"], 320)
            self.assertAlmostEqual(rows[0]["accuracy"], 0.7406, places=3)
            self.assertAlmostEqual(rows[-1]["accuracy"], 0.9, places=3)
            by_rule = {r["rule"]: r for r in rows}
            self.assertGreater(by_rule["hand up below 70%"]["accuracy"], by_rule["hand up below 70%"]["random_same_share"] + 0.05)
            self.assertTrue((ROOT / "bench/receipts/handover-4b-12b.md").read_text().startswith("# Hand-over"))


class LiveRecord(unittest.TestCase):
    def test_the_recorded_live_call_says_which_model_answered_each_question(self):
        text = (ROOT / "bench/receipts/handover-live-2026-11-07.md").read_text()
        self.assertEqual(text.count("answered by ollama:gemma3\n"), 2)
        self.assertEqual(text.count("answered by ollama:gemma3:12b\n"), 1)
        self.assertIn("not calibrated", text)


if __name__ == "__main__":
    unittest.main()
