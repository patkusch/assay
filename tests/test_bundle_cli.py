"""Tests for calibration bundles, the calibrate command and the calibration options on decide/serve. No real model."""
import contextlib
import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from assay import Question
from assay.backends.mock import KeywordBackend, PositionBiasedBackend
from assay.bundle import CalibrationBundle, fit_bundle, load_labelled, score_probs
from assay.cli import main as cli_main
from assay.engine import decide_one
from assay.server import make_server

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
Q = Question("choice", "which one", options=["a", "b"])


class Overconfident:
    """Always shouts 'the answer is whatever the state says to pick', with near-total certainty."""
    name = "overconfident"
    model = "toy"

    def logprobs(self, state, question, labels):
        pick = state.split("pick:")[1].strip()
        return [8.0 if l == pick else 0.0 for l in labels]


def half_wrong_rows(n=40, qid="q"):
    """The model picks 'a' every time; the truth agrees on exactly half of them."""
    return [{"question": qid, "state": "pick:a", "truth": "a" if i % 2 == 0 else "b"} for i in range(n)]


def keyword_rows(n=30, qid="q1"):
    rows = []
    for i in range(n):
        word = "spam" if i % 2 == 0 else "ham"
        wrong = i % 5 == 0  # one in five is labelled against the words, so the fit has something to do
        truth = ("ham" if word == "spam" else "spam") if wrong else word
        rows.append({"question": qid, "state": f"{word} {word}", "truth": truth})
    return rows


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        finally:
            e.close()


class BundleTests(unittest.TestCase):
    def test_fit_save_load_round_trip(self):
        b = fit_bundle(Overconfident(), {"q": Q}, half_wrong_rows(40), n_orders=2, alpha=0.1)
        self.assertEqual(b.backend_name, "overconfident")
        self.assertEqual(b.n_examples, {"q": 40})
        self.assertIsNotNone(b.held_out["q"])  # 40 rows is enough for a held-out check
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "calib.json"
            b.save(path)
            data = json.loads(path.read_text())
            self.assertEqual(data["format_version"], 1)
            self.assertEqual(data["backend"], {"name": "overconfident", "model": "toy"})
            self.assertEqual(data["n_examples"], 40)
            b2 = CalibrationBundle.load(path)
        self.assertEqual(b2.backend_name, "overconfident")
        self.assertEqual(b2.model, "toy")
        self.assertEqual(b2.fitted_at, b.fitted_at)
        self.assertEqual(b2.held_out, b.held_out)
        c1, c2 = b.calibrators["q"], b2.calibrators["q"]
        self.assertAlmostEqual(c1.temperature, c2.temperature)
        self.assertEqual(c1.qhat, c2.qhat)
        probs = {"a": 0.99, "b": 0.01}
        self.assertEqual(c1.transform(probs), c2.transform(probs))

    def test_refuses_under_twenty_examples(self):
        with self.assertRaisesRegex(ValueError, "'q' has 19 labelled examples; need at least 20"):
            fit_bundle(Overconfident(), {"q": Q}, half_wrong_rows(19))

    def test_refusal_names_the_thin_question_even_if_another_is_fine(self):
        rows = half_wrong_rows(30, "big") + half_wrong_rows(5, "small")
        with self.assertRaisesRegex(ValueError, "'small'"):
            fit_bundle(Overconfident(), {"big": Q, "small": Q}, rows)

    def test_bad_rows_are_refused_plainly(self):
        with self.assertRaisesRegex(ValueError, "not in the questions"):
            fit_bundle(Overconfident(), {"q": Q}, [{"question": "zzz", "state": "pick:a", "truth": "a"}])
        with self.assertRaisesRegex(ValueError, "not one of"):
            fit_bundle(Overconfident(), {"q": Q}, [{"question": "q", "state": "pick:a", "truth": "c"}] * 20)
        with self.assertRaisesRegex(ValueError, "must have"):
            fit_bundle(Overconfident(), {"q": Q}, [{"question": "q"}])

    def test_under_forty_examples_says_scores_are_not_held_out(self):
        b = fit_bundle(Overconfident(), {"q": Q}, half_wrong_rows(25))
        self.assertIsNone(b.held_out["q"])
        self.assertIn("same examples", b.summary()["questions"]["q"]["note"])

    def test_mismatch_warning(self):
        b = fit_bundle(Overconfident(), {"q": Q}, half_wrong_rows(20))
        self.assertIsNone(b.check("overconfident"))
        warning = b.check("ollama:gemma3")
        self.assertIn("overconfident", warning)
        self.assertIn("ollama:gemma3", warning)

    def test_unknown_format_version_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            CalibrationBundle.from_dict({"format_version": 99, "questions": {}})

    def test_score_probs_matches_the_engine_before_calibration(self):
        backend = PositionBiasedBackend("b")
        q = Question("choice", "x", options=["a", "b", "c"])
        engine_probs = decide_one(backend, "s", q, n_orders=3).probabilities
        self.assertEqual(score_probs(backend, "s", q, 3), engine_probs)

    def test_calibrated_answer_differs_on_an_overconfident_backend(self):
        backend = Overconfident()
        b = fit_bundle(backend, {"q": Q}, half_wrong_rows(40), n_orders=2)
        raw = decide_one(backend, "pick:a", Q, n_orders=2)
        cal = decide_one(backend, "pick:a", Q, n_orders=2, calibrator=b.calibrators["q"])
        self.assertGreater(raw.confidence, 0.99)
        self.assertFalse(raw.calibrated)
        self.assertTrue(cal.calibrated)
        self.assertLess(cal.confidence, 0.9)          # right half the time, so it should no longer claim certainty
        self.assertGreater(b.calibrators["q"].temperature, 1.0)
        self.assertTrue(cal.abstain)                  # both answers stay possible
        self.assertEqual(sorted(cal.prediction_set), ["a", "b"])

    def test_example_labelled_file_is_valid_but_too_thin_to_fit(self):
        rows = load_labelled(EXAMPLES / "labelled_example.jsonl")
        self.assertGreaterEqual(len(rows), 20)
        ids = {r["question"] for r in rows}
        self.assertEqual(len(ids), 3)
        questions = {}
        for f in EXAMPLES.glob("*.json"):
            questions.update({k: Question(v["type"], v["instructions"], v.get("options", []), v.get("levels", 5))
                              for k, v in json.loads(f.read_text())["questions"].items()})
        for r in rows:
            self.assertIn(str(r["truth"]), questions[r["question"]].labels(), r)
        with self.assertRaisesRegex(ValueError, "need at least 20"):
            fit_bundle(KeywordBackend(), questions, rows)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.request = self.dir / "questions.json"
        self.request.write_text(json.dumps({"questions": {
            "q1": {"type": "choice", "instructions": "what", "options": ["spam", "ham"]}}}))
        self.labelled = self.dir / "labelled.jsonl"
        self.labelled.write_text("\n".join(json.dumps(r) for r in keyword_rows(30)) + "\n")
        self.calib = self.dir / "calib.json"

    def tearDown(self):
        self.tmp.cleanup()

    def calibrate(self):
        return run_cli("calibrate", "--backend", "keyword", "--request", str(self.request),
                       "--labelled", str(self.labelled), "--out", str(self.calib), "--alpha", "0.2", "--orders", "2")

    def test_calibrate_writes_bundle_and_prints_plain_report(self):
        rc, out, err = self.calibrate()
        self.assertEqual((rc, err), (0, ""))
        self.assertIn("Calibration error", out)
        self.assertIn("before", out)
        self.assertIn("after", out)
        self.assertIn("30 labelled examples", out)
        bundle = CalibrationBundle.load(self.calib)
        self.assertEqual(bundle.backend_name, "keyword")
        self.assertEqual(list(bundle.calibrators), ["q1"])
        self.assertEqual(bundle.calibrators["q1"].alpha, 0.2)

    def test_calibrate_too_few_examples_exits_2_with_message(self):
        self.labelled.write_text("\n".join(json.dumps(r) for r in keyword_rows(10)) + "\n")
        rc, out, err = self.calibrate()
        self.assertEqual(rc, 2)
        self.assertIn("need at least 20", err)
        self.assertFalse(self.calib.exists())

    def test_decide_with_calibration_end_to_end(self):
        self.calibrate()
        args = ["decide", "--backend", "keyword", "--state", "spam spam", "--question", "choice:what:spam|ham"]
        rc, plain_out, _ = run_cli(*args)
        rc2, out, err = run_cli(*args, "--calibration", str(self.calib))
        self.assertEqual((rc, rc2, err), (0, 0, ""))
        plain, cal = json.loads(plain_out)["answers"]["q1"], json.loads(out)["answers"]["q1"]
        self.assertFalse(plain["calibrated"])
        self.assertTrue(cal["calibrated"])
        self.assertNotEqual(plain["confidence"], cal["confidence"])
        self.assertEqual(cal["choice"], "spam")

    def test_decide_with_mismatched_calibration_warns_on_stderr_and_continues(self):
        fit_bundle(Overconfident(), {"q1": Q}, half_wrong_rows(20, "q1")).save(self.calib)
        rc, out, err = run_cli("decide", "--backend", "keyword", "--state", "spam spam",
                               "--question", "choice:what:spam|ham", "--calibration", str(self.calib))
        self.assertEqual(rc, 0)
        self.assertIn("overconfident", err)
        self.assertIn("keyword", err)
        self.assertTrue(json.loads(out)["answers"]["q1"]["calibrated"])

    def test_missing_calibration_file_exits_2(self):
        rc, out, err = run_cli("decide", "--backend", "keyword", "--state", "s",
                               "--question", "noul:x", "--calibration", str(self.dir / "nope.json"))
        self.assertEqual(rc, 2)
        self.assertIn("error", err)

    def test_confidence_floor_makes_answer_abstain(self):
        args = ["decide", "--backend", "keyword", "--state", "spam spam", "--question", "choice:what:spam|ham"]
        self.assertFalse(json.loads(run_cli(*args)[1])["answers"]["q1"]["abstain"])
        out = run_cli(*args, "--confidence-floor", "0.999")[1]
        self.assertTrue(json.loads(out)["answers"]["q1"]["abstain"])


class ServerCalibrationTests(unittest.TestCase):
    def start(self, **kw):
        srv = make_server(KeywordBackend(), port=0, **kw)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (srv.shutdown(), srv.server_close()))
        return f"http://127.0.0.1:{srv.server_address[1]}"

    def test_calibration_404_when_none_loaded(self):
        code, body = get(self.start() + "/v1/calibration")
        self.assertEqual(code, 404)
        self.assertIn("error", body)

    def test_calibration_summary_when_loaded(self):
        bundle = fit_bundle(KeywordBackend(), {"q1": Question("choice", "what", options=["spam", "ham"])},
                            keyword_rows(45), n_orders=2, alpha=0.2)
        base = self.start(bundle=bundle)
        code, body = get(base + "/v1/calibration")
        self.assertEqual(code, 200)
        self.assertEqual(body["question_ids"], ["q1"])
        q = body["questions"]["q1"]
        self.assertEqual((q["n"], q["alpha"]), (45, 0.2))
        self.assertGreater(q["T"], 0)
        self.assertIn("ece_before", q["held_out"])
        self.assertIn("coverage", q["held_out"])
        self.assertEqual(body["backend"], "keyword")
        self.assertIsNone(body["warning"])

    def test_answers_are_marked_calibrated_when_bundle_is_loaded(self):
        bundle = fit_bundle(KeywordBackend(), {"q1": Question("choice", "what", options=["spam", "ham"])}, keyword_rows(30))
        base = self.start(bundle=bundle)
        req = urllib.request.Request(base + "/v1/systemone", headers={"Content-Type": "application/json"}, data=json.dumps({
            "state": "spam spam",
            "questions": {"q1": {"type": "choice", "instructions": "what", "options": ["spam", "ham"]},
                          "other": {"type": "noul", "instructions": "x"}}}).encode())
        with urllib.request.urlopen(req, timeout=10) as r:
            a = json.loads(r.read())["answers"]
        self.assertTrue(a["q1"]["calibrated"])
        self.assertFalse(a["other"]["calibrated"])  # no calibrator was fitted for this one


if __name__ == "__main__":
    unittest.main()
