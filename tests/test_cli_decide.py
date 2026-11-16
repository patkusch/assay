import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from assay import cli
from assay.server import BadRequest
from assay.types import BackendError


def call(argv, stdin=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        if stdin is not None:
            with mock.patch.object(sys, "stdin", io.StringIO(stdin)):
                code = cli.main(argv)
        else:
            code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


STATE = "The build failed on the payment tests. Payment retries exhausted. Payment gateway timed out."


class Questions(unittest.TestCase):
    def test_a_choice_names_its_options_after_the_last_colon(self):
        self.assertEqual(cli.parse_question_arg("choice:Which part is it:payment|search|login"),
                         {"type": "choice", "instructions": "Which part is it", "options": ["payment", "search", "login"]})

    def test_a_colon_inside_the_instructions_of_a_choice_is_kept(self):
        q = cli.parse_question_arg("choice:Pick one: carefully:a|b")
        self.assertEqual((q["instructions"], q["options"]), ("Pick one: carefully", ["a", "b"]))

    def test_a_choice_with_no_options_is_refused(self):
        with self.assertRaisesRegex(BadRequest, "a choice question needs options"):
            cli.parse_question_arg("choice:Which part is it")

    def test_a_score_takes_its_number_of_levels_only_when_the_last_part_is_a_number(self):
        self.assertEqual(cli.parse_question_arg("score:How severe:7"), {"type": "score", "instructions": "How severe", "levels": 7})
        self.assertEqual(cli.parse_question_arg("score:How severe"), {"type": "score", "instructions": "How severe"})
        self.assertEqual(cli.parse_question_arg("score:Ratio is 3:4"), {"type": "score", "instructions": "Ratio is 3", "levels": 4}, "a trailing number is always read as the levels")
        self.assertEqual(cli.parse_question_arg("score:Why: now")["instructions"], "Why: now")

    def test_a_yes_no_question_is_just_its_words(self):
        self.assertEqual(cli.parse_question_arg("noul:Is it urgent?"), {"type": "noul", "instructions": "Is it urgent?"})

    def test_text_with_no_kind_is_refused_with_the_expected_shape(self):
        with self.assertRaisesRegex(BadRequest, r"must look like kind:instructions\[:opt1\|opt2\]"):
            cli.parse_question_arg("just words")


class Decide(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.dir = Path(self._t.name)
        self.addCleanup(self._t.cleanup)

    def test_the_backends_command_lists_them_as_json(self):
        code, out, _ = call(["backends"])
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(out)), {"ollama", "keyword"})

    def test_questions_on_the_command_line_are_numbered_q1_q2_and_answered(self):
        code, out, err = call(["decide", "--backend", "keyword", "--state", STATE,
                               "--question", "noul:Is it about payment?", "--question", "choice:Which part:payment|search"])
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(list(data["answers"]), ["q1", "q2"])
        self.assertEqual(data["answers"]["q2"]["value"], "payment", "the keyword model counts the word in the state")
        self.assertEqual(data["model"], "keyword")

    def test_a_request_file_is_read_in_the_servers_own_shape(self):
        request = self.dir / "r.json"
        request.write_text(json.dumps({"state": STATE, "questions": {"hit": {"type": "choice", "instructions": "Which?", "options": ["payment", "login"]}}}))
        code, out, _ = call(["decide", "--backend", "keyword", "--request", str(request)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["answers"]["hit"]["value"], "payment")

    def test_a_dash_reads_the_request_from_standard_input(self):
        body = json.dumps({"state": STATE, "questions": {"x": {"type": "noul", "instructions": "Payment?"}}})
        code, out, _ = call(["decide", "--backend", "keyword", "--request", "-"], stdin=body)
        self.assertEqual(code, 0)
        self.assertIn("x", json.loads(out)["answers"])

    def test_pretty_output_is_readable_text_not_json(self):
        code, out, _ = call(["decide", "--backend", "keyword", "--state", STATE, "--format", "pretty",
                             "--question", "choice:Which part:payment|search"])
        self.assertEqual(code, 0)
        with self.assertRaises(ValueError):
            json.loads(out)
        self.assertIn("Which part", out)
        self.assertIn("payment", out)

    def test_no_request_and_no_state_and_question_is_a_plain_error_with_exit_2(self):
        for argv in (["decide", "--backend", "keyword"],
                     ["decide", "--backend", "keyword", "--state", "only a state"],
                     ["decide", "--backend", "keyword", "--question", "noul:Only a question?"]):
            code, out, err = call(argv)
            self.assertEqual(code, 2, argv)
            self.assertEqual(out, "")
            self.assertIn("give --request FILE, or --state plus at least one --question", json.loads(err)["error"])

    def test_a_missing_or_broken_request_file_is_exit_2_with_a_json_error(self):
        code, _, err = call(["decide", "--backend", "keyword", "--request", str(self.dir / "nope.json")])
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(err))
        broken = self.dir / "broken.json"
        broken.write_text("{not json")
        code, _, err = call(["decide", "--backend", "keyword", "--request", str(broken)])
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(err))

    def test_a_badly_formed_question_is_refused_before_anything_runs(self):
        code, _, err = call(["decide", "--backend", "keyword", "--state", "s", "--question", "no kind here"])
        self.assertEqual(code, 2)
        self.assertIn("must look like kind:instructions", json.loads(err)["error"])

    def test_a_backend_that_fails_is_exit_3_and_says_it_was_the_backend(self):
        with mock.patch.object(cli, "run_request", side_effect=BackendError("Ollama is not running")):
            code, out, err = call(["decide", "--backend", "keyword", "--state", "s", "--question", "noul:Q?"])
        self.assertEqual((code, out), (3, ""))
        self.assertEqual(json.loads(err), {"error": "backend failed: Ollama is not running"})

    def test_a_calibration_file_for_a_different_model_prints_a_warning_but_still_answers(self):
        request = self.dir / "r.json"
        request.write_text(json.dumps({"questions": {"hit": {"type": "choice", "instructions": "Which?", "options": ["payment", "login"]}}}))
        labelled = self.dir / "l.jsonl"
        labelled.write_text("\n".join(json.dumps({"question": "hit", "state": f"{w} payment {w}", "truth": "payment"}) for w in "abcdefghijklmnopqrstuvwx") + "\n")
        bundle = self.dir / "cal.json"
        code, _, err = call(["calibrate", "--backend", "keyword", "--request", str(request), "--labelled", str(labelled), "--out", str(bundle)])
        self.assertEqual(code, 0, err)
        self.assertTrue(bundle.exists())
        code, out, _ = call(["decide", "--backend", "keyword", "--state", STATE, "--question", "choice:Which?:payment|login",
                             "--calibration", str(bundle)])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["answers"]["q1"]["calibrated"] in (True, False))


if __name__ == "__main__":
    unittest.main()
