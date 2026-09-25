"""Tests for the benchmark: are the task files sound, and does the whole harness run end to end?

The harness tests use the keyword stand-in backend and a fake local Ollama server, so no model is needed.
Live model use is opt-in: set ASSAY_LIVE=1 (and optionally ASSAY_MODEL, default gemma3).
"""
import json
import os
import sys
import tempfile
import threading
import unittest
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "bench"
for p in (str(ROOT / "src"), str(BENCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import _local  # noqa: E402
import report  # noqa: E402
import run as bench_run  # noqa: E402
from assay import Question, decide_one  # noqa: E402
from assay.backends.mock import KeywordBackend, PositionBiasedBackend  # noqa: E402

TASK_NAMES = ["phishing", "command_safety", "routing", "urgency"]


def read_rows(name):
    return [json.loads(l) for l in (BENCH / "tasks" / f"{name}.jsonl").read_text().splitlines() if l.strip()]


class TaskFileTests(unittest.TestCase):
    def setUp(self):
        self.specs = json.loads((BENCH / "tasks" / "tasks.json").read_text())

    def test_four_tasks_are_described(self):
        self.assertEqual(sorted(self.specs), sorted(TASK_NAMES))
        for name, spec in self.specs.items():
            q = spec["question"]
            self.assertTrue(q["instructions"].strip(), name)
            Question(q["type"], q["instructions"], q.get("options", []), q.get("levels", 5)).validate()

    def test_ids_are_unique_across_all_tasks(self):
        ids = [r["id"] for n in TASK_NAMES for r in read_rows(n)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_task_has_about_sixty_items_in_both_splits(self):
        for name in TASK_NAMES:
            rows = read_rows(name)
            self.assertTrue(55 <= len(rows) <= 65, f"{name}: {len(rows)} items")
            splits = Counter(r["split"] for r in rows)
            self.assertEqual(set(splits), {"dev", "test"}, name)
            for s, n in splits.items():
                self.assertGreaterEqual(n, 25, f"{name} {s}")
            for r in rows:  # the id prefix and the split field must agree
                self.assertTrue(r["id"].startswith(f"{name}-{r['split']}-"), r["id"])

    def test_truth_is_a_valid_answer_and_every_answer_is_used_in_both_splits(self):
        for name in TASK_NAMES:
            q = self.specs[name]["question"]
            labels = Question(q["type"], q["instructions"], q.get("options", []), q.get("levels", 5)).labels()
            rows = read_rows(name)
            for r in rows:
                self.assertIn(r["truth"], labels, r["id"])
            for split in ("dev", "test"):
                used = {r["truth"] for r in rows if r["split"] == split}
                self.assertEqual(used, set(labels), f"{name} {split} is missing answers")

    def test_hard_cases_are_roughly_a_third_and_spread_over_answers(self):
        for name in TASK_NAMES:
            rows = read_rows(name)
            hard = [r for r in rows if r["hard"]]
            self.assertTrue(0.25 <= len(hard) / len(rows) <= 0.40, f"{name}: {len(hard)}/{len(rows)}")
            self.assertGreaterEqual(len({r["truth"] for r in hard}), 2, name)
            for split in ("dev", "test"):
                self.assertGreaterEqual(sum(r["hard"] for r in rows if r["split"] == split), 5, f"{name} {split}")

    def test_states_are_non_empty_and_not_duplicated_within_a_task(self):
        for name in TASK_NAMES:
            states = [r["state"].strip() for r in read_rows(name)]
            self.assertTrue(all(states))
            self.assertEqual(len(states), len(set(states)), name)

    def test_readme_states_how_labels_were_made(self):
        text = (BENCH / "tasks" / "README.md").read_text().lower()
        for phrase in ("by construction", "synthetic", "small", "author-labelled"):
            self.assertIn(phrase, text)


class ScoringHelperTests(unittest.TestCase):
    def test_scored_probabilities_match_the_engine(self):
        q = Question("choice", "pick", options=["safe", "risky", "destructive"])
        state = "risky risky safe"
        mine = bench_run.score(KeywordBackend(), state, q, q.labels(), 3)
        theirs = decide_one(KeywordBackend(), state, q, n_orders=3).probabilities
        for l in q.labels():
            self.assertAlmostEqual(mine[l], theirs[l])

    def test_local_metrics_agree_with_assay_metrics_when_available(self):
        try:
            from assay import metrics
        except ImportError:
            self.skipTest("assay.metrics not present")
        samples = [{"probs": {"a": 0.7, "b": 0.2, "c": 0.1}, "truth": "a"}, {"probs": {"a": 0.5, "b": 0.4, "c": 0.1}, "truth": "b"},
                   {"probs": {"a": 0.1, "b": 0.1, "c": 0.8}, "truth": "c"}, {"probs": {"a": 0.34, "b": 0.33, "c": 0.33}, "truth": "c"},
                   {"probs": {"a": 0.9, "b": 0.05, "c": 0.05}, "truth": "b"}]
        self.assertAlmostEqual(_local.accuracy(samples), metrics.accuracy(samples))
        self.assertAlmostEqual(_local.brier(samples), metrics.brier(samples))
        self.assertAlmostEqual(_local.nll(samples), metrics.nll(samples))
        self.assertAlmostEqual(_local.ece(samples), metrics.ece(samples))
        theirs = metrics.accuracy_at_coverage(samples)
        for c in (1.0, 0.8, 0.6, 0.4):
            self.assertAlmostEqual(_local.accuracy_at_coverage(samples, c), theirs[c])

    def test_a_failed_baseline_reply_counts_as_wrong(self):
        labels = ["yes", "no"]
        failed = bench_run.baseline_sample({"failed": True, "answer": None, "confidence": None}, labels, "yes")
        self.assertEqual(_local.accuracy([failed]), 0.0)
        ok = bench_run.baseline_sample({"failed": False, "answer": "yes", "confidence": 0.9}, labels, "yes")
        self.assertEqual(_local.accuracy([ok]), 1.0)
        self.assertAlmostEqual(ok["probs"]["yes"], 0.9)
        self.assertAlmostEqual(sum(ok["probs"].values()), 1.0)
        pct = bench_run.baseline_sample({"failed": False, "answer": "no", "confidence": 85}, labels, "no")
        self.assertAlmostEqual(pct["probs"]["no"], 0.85)  # "85" is read as a percentage
        low = bench_run.baseline_sample({"failed": False, "answer": "no", "confidence": 0.1}, labels, "no")
        self.assertAlmostEqual(low["probs"]["no"], 0.5)   # never lower than an even split, so the answer stays on top


class FakeOllama:
    """A tiny local server that answers /api/generate like Ollama does, and remembers what it was asked."""

    def __init__(self, reply):
        self.requests = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                data = json.dumps({"response": reply if isinstance(reply, str) else json.dumps(reply)}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                data = json.dumps({"version": "test"}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.host = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class BaselineTests(unittest.TestCase):
    def test_baseline_sends_schema_at_temperature_zero_and_parses_reply(self):
        srv = FakeOllama({"answer": "risky", "confidence": 0.7})
        self.addCleanup(srv.close)
        q = Question("choice", "Classify.", options=["safe", "risky", "destructive"])
        res = bench_run.make_ollama_baseline("gemma3", srv.host, 10)("git push --force", q)
        self.assertEqual((res["answer"], res["confidence"], res["failed"]), ("risky", 0.7, False))
        req = srv.requests[0]
        self.assertEqual(req["options"]["temperature"], 0)
        self.assertFalse(req["stream"])
        self.assertEqual(req["format"]["properties"]["answer"]["enum"], ["safe", "risky", "destructive"])
        self.assertIn("confidence", req["format"]["required"])

    def test_answer_outside_the_options_is_a_failure(self):
        srv = FakeOllama({"answer": "maybe", "confidence": 0.7})
        self.addCleanup(srv.close)
        q = Question("noul", "Phishing?")
        res = bench_run.make_ollama_baseline("gemma3", srv.host, 10)("x", q)
        self.assertTrue(res["failed"])
        self.assertIsNone(res["answer"])

    def test_unreachable_server_is_recorded_not_raised(self):
        q = Question("noul", "Phishing?")
        res = bench_run.make_ollama_baseline("gemma3", "http://127.0.0.1:9", 2)("x", q)
        self.assertTrue(res["failed"])
        self.assertTrue(res["error"])


def synthetic_tasks(n_per_split=20):
    """A tiny task where the backend under test is known to be position-biased, to check the flip logic."""
    q = Question("choice", "pick", options=["x", "y", "z"])
    items = [{"id": f"s-{sp}-{i}", "split": sp, "truth": "z", "state": f"item {i}"} for sp in ("dev", "test") for i in range(n_per_split)]
    return {"synthetic": {"spec": {}, "question": q, "items": items}}


class HarnessTests(unittest.TestCase):
    def test_end_to_end_with_keyword_backend_writes_receipts_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "kw.json"
            rc = bench_run.main(["--backend", "keyword", "--tasks", "all", "--orders", "3", "--limit", "20", "--out", str(out)])
            self.assertEqual(rc, 0)
            receipts = json.loads(out.read_text())
            md = out.with_suffix(".md").read_text()

        self.assertEqual(sorted(receipts["tasks"]), sorted(TASK_NAMES))
        for key in ("timestamp", "config", "versions", "pooled"):
            self.assertIn(key, receipts)
        self.assertEqual(receipts["config"]["orders"], 3)
        self.assertIn("python", receipts["versions"])
        for name, t in receipts["tasks"].items():
            self.assertEqual(t["n_dev"], 20)
            self.assertEqual(t["n_test"], 20)
            for cond in ("single", "shuffled", "calibrated"):
                m = t["conditions"][cond]["test"]
                for k in ("accuracy", "ece", "brier", "latency_p50_ms", "latency_p95_ms", "flip_rate"):
                    self.assertIn(k, m, f"{name} {cond}")
                self.assertEqual(set(m["accuracy_at_coverage"]), {"100", "80", "60", "40"})
                self.assertEqual(m["n"], 20)
            cal = t["conditions"]["calibrated"]
            self.assertNotIn("dev", cal)  # the calibrator is never graded on the data it learned from
            self.assertIsNotNone(cal["test"]["abstain_rate"])
            self.assertEqual(t["conditions"]["llm_baseline"], {"skipped": "not run"})
            self.assertEqual(len(t["items"]), 40)
            self.assertEqual({r["split"] for r in t["items"]}, {"dev", "test"})
        # the keyword stand-in is not a model, so the report must say so and must give a verdict
        self.assertIn("keyword stand-in", md)
        self.assertRegex(md, r"\*\*(PASS|FAIL)\.\*\*")
        self.assertIn("What it means", md)

    def test_calibrator_is_fitted_on_dev_only(self):
        tasks = bench_run.load_tasks(["routing"], limit=25)
        receipts = bench_run.run_benchmark(KeywordBackend(), tasks, orders=3, config={"backend": "keyword"})
        t = receipts["tasks"]["routing"]
        dev = [{"probs": r["shuffled"]["probs"], "truth": r["truth"]} for r in t["items"] if r["split"] == "dev"]
        Cal, _ = bench_run._load_calibrator()
        refit = Cal().fit(dev, 0.1)
        self.assertAlmostEqual(t["calibrator"]["temperature"], refit.temperature, places=6)
        self.assertEqual(t["calibrator"]["n_fit"], len(dev))

    def test_too_few_dev_items_skips_calibration_instead_of_faking_it(self):
        tasks = bench_run.load_tasks(["phishing"], limit=5)
        receipts = bench_run.run_benchmark(KeywordBackend(), tasks, orders=3, config={"backend": "keyword"})
        self.assertIn("skipped", receipts["tasks"]["phishing"]["conditions"]["calibrated"])
        self.assertIn("NOT EVALUATED", report.build_report(receipts))

    def test_shuffling_cuts_the_flip_rate_for_a_position_biased_model_and_the_report_says_pass(self):
        receipts = bench_run.run_benchmark(PositionBiasedBackend("z"), synthetic_tasks(), orders=3, config={"backend": "position-biased"})
        single = receipts["pooled"]["single"]["test"]["flip_rate"]
        shuffled = receipts["pooled"]["shuffled"]["test"]["flip_rate"]
        self.assertEqual(single, 1.0)      # always picks whatever is shown first, so reversing the list flips every answer
        self.assertEqual(shuffled, 0.0)    # rotating the orders cancels the bias
        v = report.verdicts(receipts)
        self.assertTrue(v[0]["passed"])
        md = report.build_report(receipts)
        self.assertIn("**PASS.** Shuffling", md)

    def test_report_says_not_applicable_when_the_model_is_already_order_proof(self):
        # the keyword stand-in has no position bias, so there is nothing for shuffling to fix: not a pass and not a fail
        tasks = bench_run.load_tasks(["urgency"], limit=20)
        receipts = bench_run.run_benchmark(KeywordBackend(), tasks, orders=3, config={"backend": "keyword"})
        v = report.verdicts(receipts)
        self.assertIsNone(v[0]["passed"])
        md = report.build_report(receipts)
        self.assertIn("**NOT APPLICABLE / NOT EVALUATED.** Shuffling", md)
        self.assertIn("flip n/a", md)

    def test_report_says_fail_when_shuffling_makes_flips_worse(self):
        tasks = bench_run.load_tasks(["urgency"], limit=20)
        receipts = bench_run.run_benchmark(KeywordBackend(), tasks, orders=3, config={"backend": "keyword"})
        # hand-edit the pooled and per-task numbers so a single ordering flips a little and shuffling flips more
        for cond, rate in (("single", 0.05), ("shuffled", 0.20)):
            receipts["pooled"][cond]["test"]["flip_rate"] = rate
            for t in receipts["tasks"].values():
                t["conditions"][cond]["test"]["flip_rate"] = rate
        self.assertFalse(report.verdicts(receipts)[0]["passed"])
        self.assertIn("**FAIL.** Shuffling", report.build_report(receipts))

    def test_baseline_condition_runs_with_an_injected_generator(self):
        tasks = bench_run.load_tasks(["phishing"], limit=20)
        labels = tasks["phishing"]["question"].labels()

        def fake(state, q):
            return {"answer": "no", "confidence": 0.9, "latency_ms": 5.0, "failed": False, "error": None}

        receipts = bench_run.run_benchmark(KeywordBackend(), tasks, orders=2, baseline=fake, config={"backend": "keyword"})
        m = receipts["pooled"]["llm_baseline"]["test"]
        self.assertAlmostEqual(m["accuracy"], 0.5)          # always says "no" on a 50/50 task
        self.assertAlmostEqual(m["latency_p50_ms"], 5.0)
        self.assertIn("Against an ordinary LLM answer", report.build_report(receipts))
        self.assertEqual(labels, ["yes", "no"])

    def test_report_cli_rewrites_markdown_from_receipts(self):
        tasks = bench_run.load_tasks(["phishing"], limit=20)
        receipts = bench_run.run_benchmark(KeywordBackend(), tasks, orders=3, config={"backend": "keyword"})
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            p.write_text(json.dumps(receipts))
            self.assertEqual(report.main([str(p)]), 0)
            self.assertTrue((Path(d) / "r.md").read_text().startswith("# assay scoreboard"))


@unittest.skipUnless(os.environ.get("ASSAY_LIVE") == "1", "live model test; set ASSAY_LIVE=1 to run")
class LiveTests(unittest.TestCase):
    def test_small_live_run_against_local_ollama(self):
        model = os.environ.get("ASSAY_MODEL", "gemma3")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "live.json"
            bench_run.main(["--backend", "ollama", "--model", model, "--tasks", "phishing", "--limit", "20", "--orders", "3", "--out", str(out)])
            receipts = json.loads(out.read_text())
        self.assertEqual(receipts["config"]["model"], model)
        self.assertNotIn("skipped", receipts["pooled"]["llm_baseline"])
        self.assertTrue(receipts["pooled"]["shuffled"]["test"]["latency_p50_ms"] > 0)


if __name__ == "__main__":
    unittest.main()
