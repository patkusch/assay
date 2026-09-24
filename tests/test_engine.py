import unittest

from assay import Question, Request, decide, decide_one
from assay.backends.mock import KeywordBackend, PositionBiasedBackend
from assay.engine import orderings


class EngineTests(unittest.TestCase):
    def test_orderings_rotate_each_label_through_first_slot(self):
        labels = ["a", "b", "c", "d"]
        firsts = {o[0] for o in orderings(labels, 4)}
        self.assertEqual(firsts, set(labels))

    def test_position_bias_is_cancelled(self):
        q = Question("choice", "pick", options=["x", "y", "z"])
        one = decide_one(PositionBiasedBackend("z"), "s", q, n_orders=1)
        many = decide_one(PositionBiasedBackend("z"), "s", q, n_orders=3)
        self.assertNotEqual(one.value, "z")  # a single ordering is fooled by the bias
        self.assertEqual(many.value, "z")    # rotating orderings recovers the truth
        self.assertLess(many.stability, 1.0)  # and the answer admits it was order-sensitive

    def test_noul_and_score_types(self):
        r = Request("this is spam spam spam", {
            "is_spam": Question("noul", "spam?"),
            "level": Question("score", "how spammy", levels=3),
        })
        out = decide(KeywordBackend(), r)
        self.assertEqual(set(out.answers), {"is_spam", "level"})
        self.assertAlmostEqual(sum(out.answers["is_spam"].probabilities.values()), 1.0)
        self.assertTrue(1.0 <= out.answers["level"].value <= 3.0)

    def test_bad_question_rejected(self):
        with self.assertRaises(ValueError):
            decide_one(KeywordBackend(), "s", Question("choice", "x", options=["only"]))


if __name__ == "__main__":
    unittest.main()
