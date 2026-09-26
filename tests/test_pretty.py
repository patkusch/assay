import contextlib
import io
import unittest

from assay import cli
from assay.pretty import format_answers


def answer(value, probs, **kw):
    top = max(probs.values())
    return {"value": value, "probabilities": probs, "confidence": top, "stability": kw.get("stability", 1.0),
            "prediction_set": kw.get("set", [max(probs, key=probs.get)]), "abstain": kw.get("abstain", False), "calibrated": kw.get("cal", False)}


class PrettyTests(unittest.TestCase):
    def test_choice_shows_a_bar_per_option_and_marks_the_top(self):
        text = format_answers({"model": "m", "latency_ms": 12.0,
                               "answers": {"team": answer("billing", {"billing": 0.9, "technical": 0.1})}})
        self.assertIn("team: billing", text)
        self.assertIn("* billing", text)
        self.assertIn("  technical", text)         # not the top: no star
        self.assertIn("90%", text)
        self.assertIn("not calibrated", text)
        self.assertEqual(text.count("█") + text.count("░"), 2 * 24)

    def test_abstain_and_calibrated_are_called_out(self):
        text = format_answers({"model": "m", "latency_ms": 1, "answers": {
            "q": answer("a", {"a": 0.5, "b": 0.4, "c": 0.1}, abstain=True, set=["a", "b"], cal=True)}})
        self.assertIn("⚠ not sure: a or b", text)
        self.assertIn("calibrated", text)
        self.assertNotIn("not calibrated", text)

    def test_score_and_yes_no_values_are_readable(self):
        text = format_answers({"model": "m", "latency_ms": 1, "answers": {
            "u": answer(3.4, {"1": 0.05, "2": 0.1, "3": 0.35, "4": 0.4, "5": 0.1}),
            "y": answer(0.88, {"yes": 0.88, "no": 0.12})}})
        self.assertIn("u: 3.40", text)
        self.assertIn("y: 88% yes", text)
        self.assertIn("* yes", text)

    def test_a_tiny_probability_is_still_a_sliver(self):
        text = format_answers({"model": "m", "latency_ms": 1, "answers": {"q": answer("a", {"a": 0.999, "b": 0.001})}})
        line = [l for l in text.splitlines() if l.strip().startswith("b")][0]
        self.assertIn("█", line)

    def test_cli_pretty_format_end_to_end(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["decide", "--backend", "keyword", "--format", "pretty", "--state", "billing billing",
                             "--question", "choice:Which team?:billing|technical"])
        self.assertEqual(code, 0)
        self.assertIn("q1: billing", out.getvalue())
        self.assertIn("Which team?", out.getvalue())


if __name__ == "__main__":
    unittest.main()
