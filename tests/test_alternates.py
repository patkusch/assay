import unittest

from assay import Question, Request, decide, decide_one
from assay.backends.mock import KeywordBackend
from assay.engine import average_probs
from assay.server import BadRequest, parse_request


class WordingSensitive:
    """Answers by the wording: instructions containing 'A-way' favour the first label, 'B-way' the second."""
    name = "wording-sensitive"

    def __init__(self):
        self.seen = []

    def logprobs(self, state, question, labels):
        self.seen.append(question.instructions)
        want = "x" if "A-way" in question.instructions else "y"
        return [4.0 if l == want else 0.0 for l in labels]


class AlternatesTests(unittest.TestCase):
    def test_without_alternates_nothing_changes(self):
        q = Question("choice", "pick", options=["x", "y", "z"])
        b = KeywordBackend()
        a = decide_one(b, "x x x y", q, n_orders=3)
        probs, per_call = average_probs(b, "x x x y", q, 3)
        self.assertEqual(len(per_call), 3)
        self.assertEqual(a.probabilities, probs)

    def test_every_wording_is_used_and_odds_are_averaged(self):
        b = WordingSensitive()
        q = Question("choice", "A-way", options=["x", "y"], alternates=["B-way one", "B-way two"])
        a = decide_one(b, "s", q, n_orders=1)
        self.assertEqual(len(b.seen), 3)                       # one call per wording
        self.assertEqual(set(b.seen), {"A-way", "B-way one", "B-way two"})
        self.assertEqual(a.value, "y")                          # two of three wordings said y
        self.assertAlmostEqual(sum(a.probabilities.values()), 1.0)
        self.assertLess(a.stability, 1.0)                       # and the answer admits the wordings disagreed

    def test_the_backend_never_sees_alternates_and_calls_are_the_larger_count(self):
        seen = []

        class Spy:
            name = "spy"

            def logprobs(self, state, question, labels):
                seen.append((question.instructions, tuple(labels), list(question.alternates)))
                return [0.0] * len(labels)

        q = Question("choice", "one", options=["a", "b", "c"], alternates=["two", "three", "four", "five"])
        decide_one(Spy(), "s", q, n_orders=3)
        self.assertEqual(len(seen), 5)                          # 5 wordings > 3 rotations
        self.assertTrue(all(alts == [] for _, _, alts in seen))
        self.assertGreater(len({order for _, order, _ in seen}), 1)   # options were rotated too
        seen.clear()
        decide_one(Spy(), "s", Question("choice", "one", options=["a", "b", "c"], alternates=["two"]), n_orders=3)
        self.assertEqual(len(seen), 3)                          # 2 wordings < 3 rotations: rotations decide

    def test_the_server_accepts_alternates_and_rejects_bad_ones(self):
        body = {"state": "s", "questions": {"q": {"type": "choice", "instructions": "i", "options": ["a", "b"], "alternates": ["j", "k"]}}}
        req, _ = parse_request(body)
        self.assertEqual(req.questions["q"].alternates, ["j", "k"])
        body["questions"]["q"]["alternates"] = "not a list"
        with self.assertRaises(BadRequest):
            parse_request(body)
        body["questions"]["q"]["alternates"] = [""]
        with self.assertRaises(BadRequest):
            parse_request(body)

    def test_bundle_scoring_uses_the_same_path(self):
        from assay.bundle import score_probs
        b = WordingSensitive()
        q = Question("choice", "A-way", options=["x", "y"], alternates=["B-way"])
        self.assertEqual(score_probs(b, "s", q, 1), decide_one(b, "s", q, n_orders=1).probabilities)


if __name__ == "__main__":
    unittest.main()
