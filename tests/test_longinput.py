import re
import unittest

from assay import Question, Request, decide
from assay.backends.mock import KeywordBackend
from assay.longinput import ChunkedBackend, split_text, COMBINE_MODES


class CueBackend:
    """Gives a label a high score in any chunk that contains its cue word. Records what it was shown."""
    name = "cue"

    def __init__(self, cues):
        self.cues, self.seen = cues, []

    def logprobs(self, state, question, labels):
        self.seen.append(state)
        return [6.0 if self.cues[l] in state else 0.0 for l in labels]


def filler(n_chars, tag="The weather report says nothing of interest today."):
    out, i = [], 0
    while sum(len(s) + 1 for s in out) < n_chars:
        out.append(f"{tag} Item {i} is routine.")
        i += 1
    return " ".join(out)


CUES = {"safe": "ALPHA", "scam": "OMEGA", "unsure": "SIGMA"}
Q = Question("choice", "what is it?", options=["safe", "scam", "unsure"])
NEEDLE = "Please wire the money to OMEGA account now."


def buried(size=20000):
    half = filler(size // 2)
    return f"{half}\n\n{NEEDLE}\n\n{half}"


class SplitTests(unittest.TestCase):
    def test_short_text_is_one_chunk(self):
        self.assertEqual(split_text("hello there", 100, 10), ["hello there"])

    def test_chunks_respect_size_and_never_cut_words(self):
        text = filler(9000)
        words = set(re.findall(r"\S+", text))
        chunks = split_text(text, 500, 80)
        self.assertGreater(len(chunks), 10)
        for c in chunks:
            self.assertLessEqual(len(c), 500)
            for w in re.findall(r"\S+", c):
                self.assertIn(w, words)

    def test_giant_word_is_kept_whole(self):
        big = "x" * 900
        chunks = split_text(f"start here. {big} end here. " + filler(2000), 300, 30)
        self.assertTrue(any(big in c for c in chunks))

    def test_no_text_is_lost(self):
        text = buried(8000)
        chunks = split_text(text, 700, 100)
        self.assertIn(NEEDLE, "".join(chunks))
        for w in set(re.findall(r"\S+", text)):
            self.assertTrue(any(w in c for c in chunks))

    def test_overlap_keeps_boundary_sentence_whole(self):
        sents = [f"Sentence number {i:03d} is here." for i in range(60)]
        text = " ".join(sents)
        chunks = split_text(text, 300, 80)
        for a, b in zip(chunks, chunks[1:]):
            last = re.findall(r"Sentence number \d+ is here\.", a)[-1]
            self.assertIn(last, b)  # the last sentence of one chunk reopens the next
        for s in sents:
            self.assertTrue(any(s in c for c in chunks))

    def test_no_overlap_when_zero(self):
        text = " ".join(f"Sentence number {i:03d} is here." for i in range(40))
        chunks = split_text(text, 300, 0)
        self.assertEqual("".join(chunks), text)

    def test_prefers_paragraph_break(self):
        para = "One two three four five six seven eight nine ten. " * 4
        text = "\n\n".join([para.strip()] * 6)
        chunks = split_text(text, len(para) * 2 + 20, 0)
        for c in chunks[:-1]:
            self.assertTrue(c.rstrip().endswith("ten."))
            self.assertTrue(c.endswith("\n\n"))


class ChunkedTests(unittest.TestCase):
    def test_short_input_is_identical_and_untouched(self):
        inner = KeywordBackend()
        state = "this is a scam scam"
        q = Question("choice", "x", options=["scam", "safe"])
        cb = ChunkedBackend(inner)
        self.assertEqual(cb.logprobs(state, q, ["scam", "safe"]), inner.logprobs(state, q, ["scam", "safe"]))
        self.assertTrue(cb.last_trace["delegated"])
        self.assertFalse(cb.last_trace["truncated"])

    def test_short_input_passes_state_verbatim(self):
        inner = CueBackend(CUES)
        ChunkedBackend(inner).logprobs("  odd   spacing OMEGA\n", Q, Q.labels())
        self.assertEqual(inner.seen, ["  odd   spacing OMEGA\n"])

    def test_max_evidence_finds_buried_sentence_but_truncation_misses_it(self):
        state = buried()
        naive = CueBackend(CUES).logprobs(state[:3000], Q, Q.labels())
        self.assertEqual(naive, [0.0, 0.0, 0.0])  # first-N-chars sees nothing
        inner = CueBackend(CUES)
        cb = ChunkedBackend(inner, max_chars=3000, overlap=300)
        scores = cb.logprobs(state, Q, Q.labels())
        self.assertEqual(Q.labels()[scores.index(max(scores))], "scam")
        trace = cb.last_trace
        self.assertGreater(trace["chunks"], 3)
        self.assertFalse(trace["truncated"])
        winner = trace["winners"]["scam"]
        self.assertIn("OMEGA", cb.inner.seen[winner])
        self.assertNotIn(winner, (0, trace["chunks"] - 1))  # it was in the middle

    def test_question_is_untouched(self):
        seen = []

        class Spy:
            name = "spy"

            def logprobs(self, state, question, labels):
                seen.append((question, tuple(labels)))
                return [0.0] * len(labels)

        ChunkedBackend(Spy(), max_chars=500).logprobs(buried(3000), Q, ["scam", "safe", "unsure"])
        self.assertTrue(len(seen) > 1)
        for question, labels in seen:
            self.assertIs(question, Q)
            self.assertEqual(labels, ("scam", "safe", "unsure"))

    def test_scores_stay_aligned_to_label_order(self):
        cb = ChunkedBackend(CueBackend(CUES), max_chars=1000, overlap=100)
        labels = ["unsure", "scam", "safe"]
        scores = cb.logprobs(buried(8000), Q, labels)
        self.assertEqual(labels[scores.index(max(scores))], "scam")

    def test_max_chunks_sampling_is_flagged_and_keeps_ends(self):
        cb = ChunkedBackend(CueBackend(CUES), max_chars=500, overlap=50, max_chunks=5)
        cb.logprobs(buried(20000), Q, Q.labels())
        t = cb.last_trace
        self.assertTrue(t["sampled"])
        self.assertTrue(t["truncated"])
        self.assertEqual(len(t["scored"]), 5)
        self.assertEqual(t["scored"][0], 0)
        self.assertEqual(t["scored"][-1], t["chunks"] - 1)
        self.assertEqual(len(t["scored"]) + len(t["skipped"]), t["chunks"])

    def test_not_truncated_when_within_max_chunks(self):
        cb = ChunkedBackend(CueBackend(CUES), max_chars=1000, max_chunks=50)
        cb.logprobs(buried(5000), Q, Q.labels())
        self.assertFalse(cb.last_trace["truncated"])
        self.assertFalse(cb.last_trace["sampled"])

    def test_mean_logprob_scores_every_chunk_and_averages(self):
        inner = CueBackend(CUES)
        cb = ChunkedBackend(inner, max_chars=1000, overlap=0, combine="mean_logprob")
        scores = cb.logprobs(buried(6000), Q, Q.labels())
        self.assertEqual(len(inner.seen), cb.last_trace["chunks"])
        # one decisive chunk out of many: the average lifts scam only a little but still above the others
        self.assertEqual(Q.labels()[scores.index(max(scores))], "scam")
        # and mean is weaker than max_evidence on the same input
        mx = ChunkedBackend(CueBackend(CUES), max_chars=1000, overlap=0).logprobs(buried(6000), Q, Q.labels())
        self.assertGreater(max(mx) - sorted(mx)[-2], max(scores) - sorted(scores)[-2])

    def test_first_and_last_only_scores_two_and_flags_skipped_middle(self):
        inner = CueBackend(CUES)
        cb = ChunkedBackend(inner, max_chars=1000, overlap=100, combine="first_and_last")
        scores = cb.logprobs(buried(6000), Q, Q.labels())
        self.assertEqual(len(inner.seen), 2)
        self.assertEqual(scores[0], scores[1])  # needle is in the middle, so no label stands out
        self.assertTrue(cb.last_trace["truncated"])
        self.assertFalse(cb.last_trace["sampled"])

    def test_first_and_last_finds_a_needle_at_the_end(self):
        state = filler(6000) + "\n\n" + NEEDLE
        cb = ChunkedBackend(CueBackend(CUES), max_chars=1000, combine="first_and_last")
        scores = cb.logprobs(state, Q, Q.labels())
        self.assertEqual(Q.labels()[scores.index(max(scores))], "scam")

    def test_first_and_last_two_chunks_is_not_truncated(self):
        cb = ChunkedBackend(CueBackend(CUES), max_chars=1000, overlap=0, combine="first_and_last")
        cb.logprobs(filler(1500), Q, Q.labels())
        self.assertEqual(cb.last_trace["chunks"], 2)
        self.assertFalse(cb.last_trace["truncated"])

    def test_head_tail_one_call_on_both_ends_and_flagged(self):
        inner = CueBackend(CUES)
        cb = ChunkedBackend(inner, max_chars=1000, combine="head_tail")
        state = "ALPHA opening. " + filler(8000) + " Closing SIGMA."
        scores = cb.logprobs(state, Q, Q.labels())
        self.assertEqual(len(inner.seen), 1)
        self.assertLessEqual(len(inner.seen[0]), 1000 + 20)
        self.assertIn("ALPHA", inner.seen[0])
        self.assertIn("SIGMA", inner.seen[0])
        self.assertEqual(scores[0], scores[2])
        self.assertTrue(cb.last_trace["truncated"])

    def test_head_tail_never_cuts_words(self):
        seen = []

        class Spy:
            name = "spy"

            def logprobs(self, state, question, labels):
                seen.append(state)
                return [0.0] * len(labels)

        text = filler(5000)
        ChunkedBackend(Spy(), max_chars=400, combine="head_tail").logprobs(text, Q, Q.labels())
        words = set(re.findall(r"\S+", text))
        for w in re.findall(r"\S+", seen[0].replace("[...]", "")):
            self.assertIn(w, words)

    def test_all_modes_return_aligned_scores(self):
        for mode in COMBINE_MODES:
            cb = ChunkedBackend(CueBackend(CUES), max_chars=800, combine=mode)
            self.assertEqual(len(cb.logprobs(buried(5000), Q, Q.labels())), 3, mode)

    def test_bad_settings_rejected(self):
        for kw in ({"combine": "nope"}, {"max_chars": 0}, {"overlap": 3000}, {"max_chunks": 1}):
            with self.assertRaises(ValueError):
                ChunkedBackend(CueBackend(CUES), **kw)

    def test_works_through_engine_decide(self):
        cb = ChunkedBackend(CueBackend(CUES), max_chars=3000, overlap=300)
        req = Request(buried(), {"kind": Q})
        resp = decide(cb, req, n_orders=3)
        self.assertEqual(resp.answers["kind"].value, "scam")
        self.assertEqual(resp.model, "chunked(cue)")
        self.assertIn("winners", cb.last_trace)

    def test_engine_answer_is_identical_for_short_input(self):
        q = Question("choice", "x", options=["scam", "safe"])
        req = Request("a scam, a scam", {"q": q})
        a = decide(KeywordBackend(), req).answers["q"].to_dict()
        b = decide(ChunkedBackend(KeywordBackend()), req).answers["q"].to_dict()
        self.assertEqual(a, b)


class ConfidenceWeightedTests(unittest.TestCase):
    """`combine="confident_weighted"`: chunks are blended by their own top-vs-second-place margin.

    This mode is untested against a real model (see docs/LONG_INPUT.md); these tests only check the
    arithmetic and the plumbing, not whether it helps a real one. They call `_confidence_weighted`
    directly on hand-built per-chunk distributions, so they do not depend on how many chunks the text
    splitter happens to produce.
    """

    def setUp(self):
        from assay.longinput import _confidence_weighted, _log_softmax
        self.combine = _confidence_weighted
        self.log_softmax = _log_softmax

    @staticmethod
    def _softmax(xs):
        import math
        m = max(xs)
        es = [math.exp(x - m) for x in xs]
        z = sum(es)
        return [e / z for e in es]

    def _weighted_by_hand(self, dists, floor=1e-3):
        weights = []
        for p in dists:
            top, second = sorted(p, reverse=True)[:2]
            weights.append(max(top - second, floor))
        z = sum(weights)
        n = len(dists[0])
        return [sum(w * p[j] for w, p in zip(weights, dists)) / z for j in range(n)]

    def test_matches_a_hand_computed_weighted_average(self):
        import math
        # three chunks, three labels, deliberately uneven confidence, none degenerate (all-zero margin)
        raw = [[3.0, -1.0, 0.0], [0.2, 0.1, 0.0], [-0.5, 1.0, 0.3]]
        dists = [self._softmax(r) for r in raw]
        expected = self._weighted_by_hand(dists)
        per_chunk = [self.log_softmax(r) for r in raw]
        got = [math.exp(x) for x in self.combine(per_chunk)]
        for g, e in zip(got, expected):
            self.assertAlmostEqual(g, e, places=6)
        self.assertAlmostEqual(sum(got), 1.0, places=6)

    def test_a_decisive_chunk_survives_more_flat_filler_than_mean_logprob_allows(self):
        """The real advantage over mean_logprob: a genuinely uninformative (flat) filler chunk should barely
        move the answer, however many of them there are, because its own margin is near zero. mean_logprob
        has no such protection and drifts toward uniform as filler chunks pile up."""
        import math
        decisive = [8.0, 0.0, 0.0]  # near-certain for label 0
        flat = [0.0, 0.0, 0.0]      # no opinion at all
        for n_filler in (2, 6, 20):
            scores = [decisive] + [flat] * n_filler
            per_chunk = [self.log_softmax(s) for s in scores]
            weighted = math.exp(self.combine(per_chunk)[0])
            meaned = self._softmax([sum(c[j] for c in per_chunk) / len(per_chunk) for j in range(3)])[0]
            self.assertGreater(weighted, meaned, f"n_filler={n_filler}")
            self.assertGreater(weighted, 0.9, f"n_filler={n_filler}")  # stays confident regardless of filler count

    def test_all_flat_chunks_do_not_crash_and_stay_uniform(self):
        per_chunk = [self.log_softmax([0.0, 0.0, 0.0])] * 4
        out = self.combine(per_chunk)
        self.assertAlmostEqual(out[0], out[1])
        self.assertAlmostEqual(out[1], out[2])

    def test_is_a_valid_choice_and_works_through_engine_decide(self):
        self.assertIn("confident_weighted", COMBINE_MODES)
        cb = ChunkedBackend(CueBackend(CUES), max_chars=3000, overlap=300, combine="confident_weighted")
        req = Request(buried(), {"kind": Q})
        resp = decide(cb, req, n_orders=3)
        self.assertEqual(resp.answers["kind"].value, "scam")


if __name__ == "__main__":
    unittest.main()
