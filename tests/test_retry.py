import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from assay import Question
from assay.backends.ollama import BackendTimeout, OllamaBackend
from assay.types import BackendError


def server(delays):
    """A fake Ollama: each request sleeps for the next delay in the list, then answers option 'A'."""
    calls = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            calls.append(time.time())
            time.sleep(delays[min(len(calls) - 1, len(delays) - 1)])
            body = json.dumps({"logprobs": [{"token": "A", "logprob": -0.1, "top_logprobs": [
                {"token": "A", "logprob": -0.1}, {"token": "B", "logprob": -2.0}]}]}).encode()
            try:
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                pass  # the client already gave up on this attempt

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, calls


Q = Question("choice", "which?", options=["x", "y"])


class RetryTests(unittest.TestCase):
    def test_one_slow_call_is_retried_and_then_succeeds(self):
        srv, calls = server([0.6, 0.0])  # first call is slower than the timeout, second is instant
        try:
            b = OllamaBackend("m", f"http://127.0.0.1:{srv.server_address[1]}", timeout=0.25, retries=1)
            scores = b.logprobs("s", Q, ["x", "y"])
            self.assertEqual(len(scores), 2)
            self.assertEqual(len(calls), 2)
        finally:
            srv.shutdown()

    def test_it_gives_up_loudly_after_the_retries(self):
        srv, calls = server([0.6])
        try:
            b = OllamaBackend("m", f"http://127.0.0.1:{srv.server_address[1]}", timeout=0.2, retries=1)
            with self.assertRaises(BackendTimeout):
                b.logprobs("s", Q, ["x", "y"])
            self.assertEqual(len(calls), 2)  # the original try plus one retry, no more
        finally:
            srv.shutdown()

    def test_retries_can_be_switched_off(self):
        srv, calls = server([0.6])
        try:
            b = OllamaBackend("m", f"http://127.0.0.1:{srv.server_address[1]}", timeout=0.2, retries=0)
            with self.assertRaises(BackendError):
                b.logprobs("s", Q, ["x", "y"])
            self.assertEqual(len(calls), 1)
        finally:
            srv.shutdown()

    def test_other_errors_are_not_retried(self):
        b = OllamaBackend("m", "http://127.0.0.1:1", timeout=0.5, retries=3)  # nothing listens on port 1
        with self.assertRaises(BackendError) as cm:
            b.logprobs("s", Q, ["x", "y"])
        self.assertNotIsInstance(cm.exception, BackendTimeout)


if __name__ == "__main__":
    unittest.main()
