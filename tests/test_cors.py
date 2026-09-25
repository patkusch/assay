import json
import threading
import unittest
import urllib.request

from assay.backends.mock import KeywordBackend
from assay.server import make_server


def start(**kw):
    srv = make_server(KeywordBackend(), port=0, **kw)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


class CorsTests(unittest.TestCase):
    def test_off_by_default_no_headers_and_options_refused(self):
        srv, base = start()
        try:
            with urllib.request.urlopen(base + "/healthz") as r:
                self.assertIsNone(r.headers.get("Access-Control-Allow-Origin"))
            req = urllib.request.Request(base + "/v1/systemone", method="OPTIONS")
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(req)
            self.assertEqual(cm.exception.code, 404)
        finally:
            srv.shutdown()

    def test_opt_in_allows_the_named_origin_and_answers_the_permission_check(self):
        srv, base = start(cors="https://patkusch.github.io")
        try:
            req = urllib.request.Request(base + "/v1/systemone", method="OPTIONS")
            with urllib.request.urlopen(req) as r:
                self.assertEqual(r.status, 204)
                self.assertEqual(r.headers["Access-Control-Allow-Origin"], "https://patkusch.github.io")
                self.assertIn("POST", r.headers["Access-Control-Allow-Methods"])
                self.assertEqual(r.headers["Access-Control-Allow-Private-Network"], "true")
            body = json.dumps({"state": "billing", "questions": {"q": {"type": "noul", "instructions": "x"}}}).encode()
            post = urllib.request.Request(base + "/v1/systemone", data=body, method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(post) as r:
                self.assertEqual(r.headers["Access-Control-Allow-Origin"], "https://patkusch.github.io")
                self.assertIn("answers", json.loads(r.read()))
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
