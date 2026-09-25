import unittest

from assay import Question
from assay.backends import ollama as o
from assay.types import BackendError


def reply(pairs):
    return {"logprobs": [{"token": pairs[0][0], "logprob": pairs[0][1], "top_logprobs": [{"token": t, "logprob": lp} for t, lp in pairs]}]}


LABELS = ["billing", "technical", "sales", "cancel", "other"]


class WordScoringTests(unittest.TestCase):
    def test_prompt_lists_the_words_and_has_no_letter_codes(self):
        q = Question("choice", "Which team?", options=LABELS)
        p = o.build_word_prompt("my invoice is wrong", q, LABELS)
        self.assertIn("- billing", p)
        self.assertNotIn("A. billing", p)
        self.assertIn("exactly one of the options", p)

    def test_first_token_odds_are_matched_to_options_and_spellings_pooled(self):
        data = reply([("cancel", -0.2), ("Cancel", -3.0), ("bill", -2.5), ("other", -6.0)])
        s = o.parse_word_scores(data, LABELS)
        self.assertEqual(max(range(5), key=s.__getitem__), 3)          # cancel
        self.assertGreater(s[3], -0.2)                                  # 'cancel' and 'Cancel' pooled, so a little above the best single
        self.assertGreater(s[0], s[1])                                  # 'bill' is the start of billing only
        self.assertEqual(s[1], s[2])                                    # nobody ranked technical or sales: same floor
        self.assertLess(s[1], -6.0)

    def test_a_token_that_starts_two_options_is_ignored(self):
        labels = ["safe", "sudo"]
        s = o.parse_word_scores(reply([("s", -0.1), ("safe", -1.0)]), labels)
        self.assertGreater(s[0], s[1])   # 's' fits both, so only the whole word 'safe' counts

    def test_no_matching_token_is_an_error(self):
        with self.assertRaises(BackendError):
            o.parse_word_scores(reply([("Sure", -0.1), ("I", -1.0)]), LABELS)

    def test_conflicting_options_are_detected(self):
        self.assertEqual(o.word_conflicts(["billing", "technical", "sales"]), [])
        self.assertTrue(o.word_conflicts(["safe", "sales"]))          # 'sa' and 'sa'
        self.assertTrue(o.word_conflicts(["refund now", "refund later"]))

    def test_auto_uses_words_only_when_options_are_distinct(self):
        b = o.OllamaBackend("m", scoring="auto")
        self.assertTrue(b._use_words(LABELS))
        self.assertFalse(b._use_words(["safe", "sales"]))
        with self.assertRaises(BackendError):
            o.OllamaBackend("m", scoring="word")._use_words(["safe", "sales"])
        self.assertFalse(o.OllamaBackend("m")._use_words(LABELS))     # default stays letters

    def test_score_and_yes_no_labels_work(self):
        s = o.parse_word_scores(reply([("4", -0.3), ("5", -1.9)]), ["1", "2", "3", "4", "5"])
        self.assertEqual(max(range(5), key=s.__getitem__), 3)
        y = o.parse_word_scores(reply([("Yes", -0.1), ("no", -2.5)]), ["yes", "no"])
        self.assertGreater(y[0], y[1])

    def test_name_says_which_scoring_is_used(self):
        self.assertEqual(o.OllamaBackend("gemma3").name, "ollama:gemma3")
        self.assertEqual(o.OllamaBackend("gemma3", scoring="word").name, "ollama:gemma3:word")
        with self.assertRaises(ValueError):
            o.OllamaBackend("gemma3", scoring="nope")


if __name__ == "__main__":
    unittest.main()
