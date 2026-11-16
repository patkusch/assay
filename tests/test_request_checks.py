import copy
import unittest
from types import SimpleNamespace

from assay.server import BadRequest, backend_for, parse_request, state_to_text


def body(**over):
    base = {"state": "The build failed.", "questions": {"q": {"type": "noul", "instructions": "Is it urgent?"}}}
    base.update(over)
    return base


def refused(b):
    with unittest.TestCase().assertRaises(BadRequest) as cm:
        parse_request(b)
    return str(cm.exception)


class State(unittest.TestCase):
    def test_text_stays_as_it_is_lists_become_lines_and_anything_else_becomes_json(self):
        self.assertEqual(state_to_text("plain"), "plain")
        self.assertEqual(state_to_text(["one", "two"]), "one\ntwo")
        self.assertEqual(state_to_text(["a", {"k": 1}, 3]), 'a\n{"k": 1}\n3')
        self.assertEqual(state_to_text({"cmd": "rm -rf /tmp/x"}), '{"cmd": "rm -rf /tmp/x"}')
        self.assertEqual(state_to_text(42), "42")

    def test_accents_are_kept_readable_not_escaped(self):
        self.assertEqual(state_to_text({"nom": "café"}), '{"nom": "café"}')


class Refusals(unittest.TestCase):
    def test_every_way_a_request_can_be_wrong_gets_a_plain_message(self):
        cases = [
            ([], "body must be a JSON object"),
            ("text", "body must be a JSON object"),
            (body(state=None), "missing 'state'"),
            ({"questions": body()["questions"]}, "missing 'state'"),
            (body(questions={}), "'questions' must be a non-empty object of id -> question"),
            (body(questions=[1]), "'questions' must be a non-empty object of id -> question"),
            (body(model=5), "'model' must be a string"),
            (body(questions={"q": "just text"}), "question 'q' must be an object"),
            (body(questions={"q": {"type": "noul", "instructions": "  "}}), "question 'q' needs non-empty 'instructions'"),
            (body(questions={"q": {"type": "noul"}}), "question 'q' needs non-empty 'instructions'"),
            (body(questions={"q": {"type": "choice", "instructions": "x", "options": "a,b"}}), "question 'q': 'options' must be a list of strings"),
            (body(questions={"q": {"type": "choice", "instructions": "x", "options": ["a", 2]}}), "question 'q': 'options' must be a list of strings"),
            (body(questions={"q": {"type": "score", "instructions": "x", "levels": "5"}}), "question 'q': 'levels' must be an integer"),
            (body(questions={"q": {"type": "score", "instructions": "x", "levels": True}}), "question 'q': 'levels' must be an integer"),
            (body(questions={"q": {"type": "noul", "instructions": "x", "alternates": "other"}}), "question 'q': 'alternates' must be a list of strings"),
        ]
        for request, want in cases:
            self.assertIn(want, refused(request), request)

    def test_the_questions_own_rules_are_reported_with_the_question_name(self):
        self.assertIn("question 'q': type must be one of", refused(body(questions={"q": {"type": "guess", "instructions": "x"}})))
        self.assertIn("question 'q': choice needs 2..255 options", refused(body(questions={"q": {"type": "choice", "instructions": "x", "options": ["only"]}})))
        self.assertIn("question 'q': choice options must be unique", refused(body(questions={"q": {"type": "choice", "instructions": "x", "options": ["a", "a"]}})))
        self.assertIn("question 'q': score levels must be 2..10", refused(body(questions={"q": {"type": "score", "instructions": "x", "levels": 11}})))


class Accepted(unittest.TestCase):
    def test_a_good_request_becomes_typed_questions_with_defaults_filled_in(self):
        request, model = parse_request(body(model="gemma3:4b", questions={
            "urgent": {"type": "noul", "instructions": "Is it urgent?"},
            "size": {"type": "score", "instructions": "How big?"},
            "kind": {"type": "choice", "instructions": "Which?", "options": ["a", "b"], "alternates": ["What kind?"]},
        }))
        self.assertEqual(model, "gemma3:4b")
        self.assertEqual(request.state, "The build failed.")
        self.assertEqual(request.questions["size"].levels, 5, "five levels unless told otherwise")
        self.assertEqual(request.questions["kind"].alternates, ["What kind?"])
        self.assertEqual(list(request.questions), ["urgent", "size", "kind"], "order is kept")

    def test_no_model_means_the_servers_own(self):
        self.assertIsNone(parse_request(body())[1])


class Backends(unittest.TestCase):
    def test_the_servers_backend_is_used_unless_a_different_model_is_asked_for(self):
        server = SimpleNamespace(model="gemma3:4b", name="ollama:gemma3:4b")
        self.assertIs(backend_for(server, None), server)
        self.assertIs(backend_for(server, ""), server)
        self.assertIs(backend_for(server, "gemma3:4b"), server)

    def test_a_different_model_gets_a_copy_so_the_server_is_not_changed(self):
        server = SimpleNamespace(model="gemma3:4b", name="ollama:gemma3:4b")
        before = copy.copy(server)
        other = backend_for(server, "gemma3:12b")
        self.assertIsNot(other, server)
        self.assertEqual((other.model, other.name), ("gemma3:12b", "ollama:gemma3:12b"))
        self.assertEqual((server.model, server.name), (before.model, before.name))

    def test_a_backend_with_no_model_to_change_is_left_alone(self):
        fixed = SimpleNamespace(name="scripted")
        self.assertIs(backend_for(fixed, "anything"), fixed)


if __name__ == "__main__":
    unittest.main()
