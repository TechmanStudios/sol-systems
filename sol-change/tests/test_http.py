import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import ROOT, handler_for
from observatory.fixtures import make_demo
from observatory.store import Store
from tests.test_continuum import sample_packet


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "api.db")
        handler = handler_for(self.store)
        handler.log_message = lambda *args: None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def request(self, path, method="GET", data=None, headers=None):
        payload = json.dumps(data).encode() if data is not None else None
        request = Request(self.base + path, data=payload, method=method, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, response.read(), response.headers
        except HTTPError as error:
            return error.code, error.read(), error.headers

    def test_complete_api_journey(self):
        demo = make_demo()
        status, body, _ = self.request("/api/experiments", "POST", demo["setup"])
        self.assertEqual(status, 201)
        exp = json.loads(body)
        root = f'/api/experiments/{exp["id"]}'
        for role in ("baseline", "candidate"):
            status, _, _ = self.request(root + "/runs", "POST", {"source_text": json.dumps(demo[role]), "source_filename": role + ".json"})
            self.assertEqual(status, 201)
        status, body, _ = self.request(root)
        comparison = json.loads(body)
        self.assertEqual(comparison["comparison"]["counts"]["unknown"], 1)
        decision = {"outcome": "mixed", "action": "run_another_experiment", "reviewer": "API QA reviewer", "rationale": "Obtain the missing reader evaluation before adoption.", "supporting_evidence": [], "unresolved_questions": ["Reader usefulness?"]}
        self.assertEqual(self.request(root + "/decisions", "POST", decision)[0], 201)
        status, exported, headers = self.request(root + "/export.json")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        target = Store(Path(self.temp.name) / "roundtrip.db")
        self.assertEqual(target.import_archive(exported.decode()), json.loads(exported))
        status, report, _ = self.request(root + "/report.md")
        self.assertEqual(status, 200)
        self.assertIn(b"API QA reviewer", report)
        self.assertIn(b"SYNTHETIC", report)

    def test_cross_origin_writes_rejected(self):
        self.assertEqual(self.request("/api/experiments", "POST", make_demo()["setup"], {"Origin": "https://unrelated.example"})[0], 403)

    def test_native_continuum_intake_is_atomic_and_review_pending(self):
        packet = json.dumps(sample_packet())
        data = {"title": "Native intake QA", "proposed_change": "Synthetic interoperability test", "baseline_source_text": packet, "candidate_source_text": packet}
        status, body, _ = self.request("/api/continuum/experiments", "POST", data)
        self.assertEqual(status, 201)
        exp = json.loads(body)
        self.assertEqual(len(exp["runs"]), 2)
        self.assertEqual(exp["decisions"], [])
        self.assertEqual(exp["review_status"], "awaiting_review")
        self.assertEqual(self.request("/api/continuum/experiments", "POST", data)[0], 409)
        self.assertEqual(len(self.store.list()), 1)

    def test_invalid_second_packet_does_not_create_partial_experiment(self):
        data = {"title": "Invalid intake QA", "proposed_change": "Test", "baseline_source_text": json.dumps(sample_packet()), "candidate_source_text": "malformed"}
        status, _, _ = self.request("/api/continuum/experiments", "POST", data)
        self.assertEqual(status, 422)
        self.assertEqual(self.store.list(), [])

    def test_native_intake_rejects_cross_origin_write(self):
        self.assertEqual(self.request("/api/continuum/experiments", "POST", {}, {"Origin": "https://unrelated.example"})[0], 403)

    def test_nonlocal_host_rejected(self):
        self.assertEqual(self.request("/api/health", headers={"Host": "unrelated.example"})[0], 403)

    def test_malformed_run_returns_clear_error(self):
        exp = self.store.create(make_demo()["setup"])
        status, body, _ = self.request(f'/api/experiments/{exp["id"]}/runs', "POST", {"source_text": "broken JSON"})
        self.assertEqual(status, 422)
        self.assertIn("Invalid JSON", json.loads(body)["errors"][0])

    def test_html_and_script_are_served_with_local_csp(self):
        status, body, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Change Observatory", body)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertNotIn("unsafe-inline", headers["Content-Security-Policy"])
        self.assertIn("javascript", self.request("/static/app.js")[2]["Content-Type"])

    def test_arbitrary_local_files_not_served(self):
        for path in ("/app.py", "/data/observatory.sqlite3", "/static/../app.py", "/schemas/../../requirements.txt"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_examples_and_schemas_download(self):
        for path in ("/examples/baseline.json", "/examples/candidate.json", "/examples/incompatible-candidate.json", "/schemas/run.schema.json", "/schemas/experiment.schema.json"):
            with self.subTest(path=path):
                status, body, _ = self.request(path)
                self.assertEqual(status, 200)
                self.assertIsInstance(json.loads(body), dict)

    def test_real_process_restart_preserves_experiment_and_decision(self):
        demo = make_demo()
        exp = self.store.create(demo["setup"])
        for role in ("baseline", "candidate"):
            exp = self.store.import_run(exp["id"], json.dumps(demo[role]))
        expected = self.store.decide(exp["id"], {"outcome": "inconclusive", "action": "run_another_experiment", "reviewer": "Restart QA reviewer", "rationale": "Verify disk persistence after a complete process restart.", "supporting_evidence": [], "unresolved_questions": []})
        def launch_and_read():
            process = subprocess.Popen([sys.executable, "-u", str(ROOT / "app.py"), "--db", str(self.store.path), "--no-demo", "--port", "0"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(), "SOL Change Observatory")
                url = process.stdout.readline().strip().removeprefix("Local: ")
                with urlopen(url + f'/api/experiments/{exp["id"]}/export.json', timeout=10) as response:
                    return json.load(response)
            finally:
                process.terminate()
                process.communicate(timeout=10)
        self.assertEqual(launch_and_read(), expected)
        self.assertEqual(launch_and_read(), expected)


if __name__ == "__main__":
    unittest.main()
