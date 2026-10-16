"""Local entry point. Python 3.11+; no third-party packages or paid services."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from observatory import DEFAULT_PORT, __version__
from observatory.continuum import build_comparison, packet_to_run
from observatory.domain import ValidationError, compare, markdown_report, parse_json
from observatory.store import ConflictError, NotFoundError, Store

ROOT = Path(__file__).resolve().parent
MAX_BODY = 10_000_000


def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SOLChange/0.2"

        def send(self, status, payload, content_type="application/json; charset=utf-8", filename=None):
            if isinstance(payload, (dict, list)):
                payload = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            elif isinstance(payload, str):
                payload = payload.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(payload)

        def handle_request(self):
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if host not in allowed:
                self.send(403, {"errors": ["This application only accepts local loopback hosts."]})
                return
            parsed = urlparse(self.path)
            parts = parsed.path.strip("/").split("/")
            method = self.command
            data = None
            if method in ("POST", "PATCH"):
                origin = self.headers.get("Origin")
                if origin and origin not in {f"http://{item}" for item in allowed}:
                    self.send(403, {"errors": ["Cross-origin writes are not allowed."]})
                    return
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    self.send(415, {"errors": ["Use Content-Type: application/json."]})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    raise ValidationError("Content-Length must be an integer.")
                if not 0 < length <= MAX_BODY:
                    self.send(413, {"errors": ["Request must contain JSON smaller than 10 MB."]})
                    return
                try:
                    data = parse_json(self.rfile.read(length).decode("utf-8-sig"))
                except UnicodeDecodeError as exc:
                    raise ValidationError("Upload must be UTF-8 encoded JSON.") from exc
            if parsed.path == "/api/health" and method == "GET":
                self.send(200, {"status": "ok", "version": __version__, "schema_version": "1.0"})
            elif parts == ["api", "continuum", "experiments"] and method == "POST":
                baseline = packet_to_run(data.get("baseline_source_text"), "baseline", data.get("baseline_label", "baseline-packet.json"), data.get("baseline_context"))
                candidate = packet_to_run(data.get("candidate_source_text"), "candidate", data.get("candidate_label", "candidate-packet.json"), data.get("candidate_context"))
                exp = build_comparison(baseline, candidate, data.get("title"), data.get("proposed_change"))
                self.send(201, store.import_archive(json.dumps(exp, ensure_ascii=False)))
            elif parts == ["api", "experiments"] and method == "GET":
                self.send(200, store.list())
            elif parts == ["api", "experiments"] and method == "POST":
                self.send(201, store.create(data))
            elif parts == ["api", "import-experiment"] and method == "POST":
                self.send(201, store.import_archive(data.get("source_text")))
            elif len(parts) >= 3 and parts[:2] == ["api", "experiments"]:
                experiment_id = parts[2]
                tail = parts[3:]
                if not tail and method == "GET":
                    exp = store.get(experiment_id)
                    self.send(200, {"experiment": exp, "comparison": compare(exp)})
                elif not tail and method == "PATCH":
                    self.send(200, store.update_setup(experiment_id, data))
                elif tail == ["runs"] and method == "POST":
                    self.send(201, store.import_run(experiment_id, data.get("source_text"), data.get("source_filename", "run.json"), data.get("supersedes_record_id"), data.get("correction_reason", "")))
                elif tail == ["selections"] and method == "POST":
                    self.send(200, store.select_runs(experiment_id, data))
                elif tail == ["decisions"] and method == "POST":
                    self.send(201, store.decide(experiment_id, data))
                elif tail == ["comparison"] and method == "GET":
                    revision = parse_qs(parsed.query).get("revision", [None])[0]
                    try:
                        revision = int(revision) if revision else None
                    except ValueError as exc:
                        raise ValidationError("Criteria revision must be an integer.") from exc
                    self.send(200, compare(store.get(experiment_id), revision))
                elif tail == ["export.json"] and method == "GET":
                    self.send(200, json.dumps(store.get(experiment_id), ensure_ascii=False, indent=2), filename=f"sol-change-{experiment_id}.json")
                elif tail == ["report.md"] and method == "GET":
                    self.send(200, markdown_report(store.get(experiment_id)), "text/markdown; charset=utf-8", filename=f"sol-change-{experiment_id}.md")
                else:
                    raise NotFoundError("API endpoint not found.")
            elif method == "GET":
                path = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
                if path.startswith("static/") or path == "index.html":
                    target = (ROOT / (path if path.startswith("static/") else "static/index.html")).resolve()
                    base = ROOT / "static"
                elif path.startswith("examples/") or path.startswith("schemas/"):
                    target = (ROOT / path).resolve()
                    base = ROOT / path.split("/")[0]
                else:
                    raise NotFoundError("File not found.")
                if not target.is_relative_to(base) or not target.is_file():
                    raise NotFoundError("File not found.")
                content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                if target.suffix == ".js":
                    content_type = "text/javascript"
                self.send(200, target.read_bytes(), content_type + "; charset=utf-8")
            else:
                raise NotFoundError("Endpoint not found.")

        def dispatch(self):
            try:
                self.handle_request()
            except ValidationError as exc:
                self.send(422, {"errors": exc.errors})
            except ConflictError as exc:
                self.send(409, {"errors": [str(exc)]})
            except NotFoundError as exc:
                self.send(404, {"errors": [str(exc)]})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                traceback.print_exc()
                self.send(500, {"errors": ["An unexpected local server error occurred. See the server terminal for details."]})

        do_GET = dispatch
        do_POST = dispatch
        do_PATCH = dispatch

    return Handler


def main():
    parser = argparse.ArgumentParser(description="SOL Change Observatory — local evidence and human decisions")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "observatory.sqlite3")
    parser.add_argument("--no-demo", action="store_true", help="Do not seed the synthetic examples")
    parser.add_argument("--open", action="store_true", help="Open in your default browser")
    args = parser.parse_args()
    store = Store(args.db)
    if not args.no_demo:
        store.seed_demo(ROOT / "examples")
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(store))
    except OSError as exc:
        parser.exit(1, f"Could not start the local server: {exc}\nTry --port 8771. The SOL live server keeps port 8765.\n")
    server.daemon_threads = True
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"SOL Change Observatory\nLocal: {url}\nData: {args.db.resolve()}\nPress Ctrl+C to stop.", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nObservatory stopped. Your data is saved.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
