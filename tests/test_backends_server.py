import json
import math
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from assay import BackendError, Question
from assay.backends.mock import KeywordBackend
from assay.backends.ollama import OllamaBackend, build_prompt, parse_scores
from assay.cli import main as cli_main, parse_question_arg
from assay.server import make_server


def call(base, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        finally:
            e.close()


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = make_server(KeywordBackend(), port=0)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_healthz(self):
        code, body = call(self.base, "/healthz")
        self.assertEqual((code, body["status"]), (200, "ok"))

    def test_systemone_all_three_types(self):
        code, body = call(self.base, "/v1/systemone", {
            "state": ["the invoice is late", "late again"],
            "questions": {
                "kind": {"type": "choice", "instructions": "what is it", "options": ["late", "early"]},
                "sev": {"type": "score", "instructions": "how bad", "levels": 3},
                "bad": {"type": "noul", "instructions": "is it bad"},
            },
        })
        self.assertEqual(code, 200)
        a = body["answers"]
        self.assertEqual(a["kind"]["choice"], "late")
        self.assertEqual(a["kind"]["value"], "late")
        self.assertTrue(1.0 <= a["sev"]["score"] <= 3.0)
        self.assertEqual(a["bad"]["noul"], a["bad"]["value"])
        self.assertIn("latency_ms", body)
        self.assertAlmostEqual(sum(a["kind"]["probabilities"].values()), 1.0)

    def test_non_string_state_is_json_dumped(self):
        code, body = call(self.base, "/v1/systemone", {
            "state": {"note": "spam spam"},
            "questions": {"q": {"type": "choice", "instructions": "x", "options": ["spam", "ham"]}},
        })
        self.assertEqual((code, body["answers"]["q"]["choice"]), (200, "spam"))

    def test_bad_input_is_400(self):
        good_q = {"q": {"type": "noul", "instructions": "x"}}
        cases = [
            {"questions": good_q},                                     # no state
            {"state": "s"},                                            # no questions
            {"state": "s", "questions": {"q": {"type": "nope", "instructions": "x"}}},
            {"state": "s", "questions": {"q": {"type": "choice", "instructions": "x", "options": ["a"]}}},
            {"state": "s", "questions": {"q": {"type": "noul"}}},      # no instructions
            [1, 2],
        ]
        for c in cases:
            code, body = call(self.base, "/v1/systemone", c)
            self.assertEqual(code, 400, c)
            self.assertIn("error", body)
        code, body = call(self.base, "/v1/systemone", raw=b"{not json")
        self.assertEqual(code, 400)

    def test_unknown_path_404(self):
        self.assertEqual(call(self.base, "/nope")[0], 404)


class FailingBackend:
    name = "failing"

    def logprobs(self, state, question, labels):
        raise BackendError("model is down")


class ServerBackendErrorTest(unittest.TestCase):
    def test_backend_error_is_502(self):
        srv = make_server(FailingBackend(), port=0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            code, body = call(f"http://127.0.0.1:{srv.server_address[1]}", "/v1/systemone", {
                "state": "s", "questions": {"q": {"type": "noul", "instructions": "x"}}})
            self.assertEqual(code, 502)
            self.assertIn("model is down", body["error"])
        finally:
            srv.shutdown()
            srv.server_close()


def tops(**kw):
    return {"logprobs": [{"token": "A", "logprob": 0, "top_logprobs": [
        {"token": t, "logprob": lp} for t, lp in kw.items()]}]}


class OllamaParsingTests(unittest.TestCase):
    def test_prompt_lists_lettered_options_in_given_order(self):
        q = Question("choice", "Which team?", options=["billing", "tech"])
        prompt, codes = build_prompt("Card was charged twice.", q, ["tech", "billing"])
        self.assertEqual(codes, ["A", "B"])
        self.assertIn("A. tech\nB. billing", prompt)
        self.assertIn("Card was charged twice.", prompt)
        self.assertIn("Which team?", prompt)

    def test_score_prompt_describes_scale(self):
        q = Question("score", "How urgent?", levels=4)
        prompt, _ = build_prompt("s", q, q.labels())
        self.assertIn("1 = lowest", prompt)
        self.assertIn("4 = highest", prompt)

    def test_many_labels_use_letters_then_digits_and_cap(self):
        _, codes = build_prompt("s", Question("choice", "x", options=[str(i) for i in range(30)]), [str(i) for i in range(30)])
        self.assertEqual(len(set(codes)), 30)
        with self.assertRaises(BackendError):
            build_prompt("s", Question("choice", "x"), [str(i) for i in range(40)])

    def test_parse_pools_spellings_and_floors_missing(self):
        s = parse_scores(tops(A=-1.0, **{" a": -2.0}, B=-3.0, Z=-9.0), ["A", "B", "C"])
        self.assertAlmostEqual(s[0], math.log(math.exp(-1.0) + math.exp(-2.0)))
        self.assertEqual(s[1], -3.0)
        self.assertEqual(s[2], -14.0)  # lowest seen (-9) minus 5

    def test_parse_no_letter_raises(self):
        with self.assertRaises(BackendError):
            parse_scores(tops(Sure=-0.1, **{"**": -2.0}), ["A", "B"])

    def test_parse_missing_logprobs_raises(self):
        with self.assertRaises(BackendError):
            parse_scores({"response": "A"}, ["A", "B"])


class FakeOllama(BaseHTTPRequestHandler):
    seen: list = []
    mode = "ok"

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOllama.seen.append(body)
        if FakeOllama.mode == "missing":
            self.send_response(404)
            payload = {"error": "model 'nope' not found"}
        else:
            self.send_response(200)
            payload = tops(A=-0.2, B=-1.7)
        data = json.dumps(payload).encode()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


class OllamaBackendHttpTests(unittest.TestCase):
    def setUp(self):
        FakeOllama.seen, FakeOllama.mode = [], "ok"
        self.srv = HTTPServer(("127.0.0.1", 0), FakeOllama)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.host = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def test_request_shape_and_scores(self):
        b = OllamaBackend("m", host=self.host)
        q = Question("noul", "Is it spam?")
        scores = b.logprobs("win money", q, ["yes", "no"])
        self.assertEqual(scores, [-0.2, -1.7])
        sent = FakeOllama.seen[0]
        self.assertEqual(sent["model"], "m")
        self.assertIs(sent["stream"], False)
        self.assertIs(sent["logprobs"], True)
        self.assertEqual(sent["top_logprobs"], 20)
        self.assertEqual(sent["options"], {"temperature": 0, "num_predict": 1})
        self.assertEqual(b.name, "ollama:m")

    def test_missing_model_is_clear(self):
        FakeOllama.mode = "missing"
        with self.assertRaisesRegex(BackendError, "does not have model"):
            OllamaBackend("nope", host=self.host).logprobs("s", Question("noul", "x"), ["yes", "no"])

    def test_unreachable_is_clear(self):
        self.srv.shutdown()
        self.srv.server_close()
        with self.assertRaisesRegex(BackendError, "cannot reach Ollama"):
            OllamaBackend(host=self.host, timeout=2).logprobs("s", Question("noul", "x"), ["yes", "no"])
        self.srv = HTTPServer(("127.0.0.1", 0), FakeOllama)  # so tearDown has something to close
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()


class CliTests(unittest.TestCase):
    def test_parse_question_arg(self):
        self.assertEqual(parse_question_arg("choice:Which team?:billing|tech"),
                         {"type": "choice", "instructions": "Which team?", "options": ["billing", "tech"]})
        self.assertEqual(parse_question_arg("noul:Is it spam?"), {"type": "noul", "instructions": "Is it spam?"})
        self.assertEqual(parse_question_arg("score:How urgent?:7")["levels"], 7)

    def test_decide_prints_json(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["decide", "--backend", "keyword", "--state", "spam spam",
                           "--question", "choice:what:spam|ham"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue())["answers"]["q1"]["choice"], "spam")


@unittest.skipUnless(os.environ.get("ASSAY_LIVE") == "1", "set ASSAY_LIVE=1 to test against a real Ollama model")
class LiveOllamaTests(unittest.TestCase):
    def test_live_gemma(self):
        b = OllamaBackend(os.environ.get("ASSAY_LIVE_MODEL", "gemma3"))
        q = Question("choice", "Which team should handle this?", options=["billing", "technical support"])
        scores = b.logprobs("I was charged twice for my subscription this month.", q, q.options)
        self.assertEqual(len(scores), 2)
        self.assertGreater(scores[0], scores[1])


if __name__ == "__main__":
    unittest.main()
