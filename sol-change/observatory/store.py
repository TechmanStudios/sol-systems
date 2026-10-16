"""SQLite-backed experiment aggregates. Writes are transactional and histories append-only."""

from __future__ import annotations

import copy
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from .domain import (DECISION_FIELDS, SCHEMA_VERSION, ValidationError, canonical, compare,
                     digest, evidence_keys, now, parse_json, validate_archive,
                     validate_decision, validate_run, validate_setup)


class NotFoundError(ValueError):
    pass


class ConflictError(ValueError):
    pass


def new_id():
    return uuid.uuid4().hex


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS experiments (id TEXT PRIMARY KEY, document TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('storage_schema_version', '1')")
            version = db.execute("SELECT value FROM metadata WHERE key='storage_schema_version'").fetchone()[0]
            if version != "1":
                raise RuntimeError(f"Unsupported database schema: {version}")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self):
        with self.connect() as db:
            docs = [json.loads(row[0]) for row in db.execute("SELECT document FROM experiments")]
        return sorted(docs, key=lambda doc: doc["updated_at"], reverse=True)

    def get(self, experiment_id):
        with self.connect() as db:
            row = db.execute("SELECT document FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
        if row is None:
            raise NotFoundError("Experiment not found.")
        return json.loads(row[0])

    def _insert(self, exp):
        try:
            with self.connect() as db:
                db.execute("INSERT INTO experiments VALUES (?, ?)", (exp["id"], canonical(exp)))
        except sqlite3.IntegrityError as exc:
            raise ConflictError("An experiment with this ID already exists. Existing history was kept intact.") from exc
        return exp

    def _mutate(self, experiment_id, action):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT document FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
            if row is None:
                raise NotFoundError("Experiment not found.")
            exp = json.loads(row[0])
            action(exp)
            exp["updated_at"] = now()
            db.execute("UPDATE experiments SET document = ? WHERE id = ?", (canonical(exp), experiment_id))
        return exp

    @staticmethod
    def _mark_pending(exp):
        exp["review_status"] = "awaiting_review" if all(exp["active_runs"].values()) else "draft"

    def create(self, setup):
        validate_setup(setup)
        stamp = now()
        exp = {"schema_version": SCHEMA_VERSION, "kind": "sol-change/experiment", "id": new_id(),
               "created_at": stamp, "updated_at": stamp, "review_status": "draft", "setup": copy.deepcopy(setup),
               "current_revision": 1, "criteria_revisions": [{"revision": 1, "created_at": stamp, "after_results": False,
                   "criteria": copy.deepcopy(setup["criteria"]), "setup_snapshot": copy.deepcopy(setup)}],
               "runs": [], "active_runs": {"baseline": None, "candidate": None}, "decisions": []}
        return self._insert(exp)

    def update_setup(self, experiment_id, setup):
        validate_setup(setup)

        def action(exp):
            if setup == exp["setup"]:
                return
            if len(exp["criteria_revisions"]) >= 200:
                raise ValidationError("V1 supports up to 200 setup revisions per experiment. Start a new experiment to continue.")
            exp["current_revision"] += 1
            exp["criteria_revisions"].append({"revision": exp["current_revision"], "created_at": now(), "after_results": bool(exp["runs"]),
                "criteria": copy.deepcopy(setup["criteria"]), "setup_snapshot": copy.deepcopy(setup)})
            exp["setup"] = copy.deepcopy(setup)
            self._mark_pending(exp)
        return self._mutate(experiment_id, action)

    def import_run(self, experiment_id, source_text, source_filename="run.json", supersedes_record_id=None, correction_reason=""):
        if not isinstance(source_text, str) or len(source_text.encode("utf-8")) > 5_000_000:
            raise ValidationError("Run file must be UTF-8 JSON smaller than 5 MB.")
        if not isinstance(source_filename, str) or not source_filename.strip() or len(source_filename) > 500:
            raise ValidationError("Source filename must be a non-empty string of at most 500 characters.")
        if not isinstance(correction_reason, str) or len(correction_reason) > 5000:
            raise ValidationError("Correction reason must be a string of at most 5000 characters.")
        if supersedes_record_id is not None and not isinstance(supersedes_record_id, str):
            raise ValidationError("Correction must reference a run record ID.")
        run = parse_json(source_text)
        validate_run(run)

        def action(exp):
            if len(exp["runs"]) >= 200:
                raise ValidationError("V1 supports up to 200 run records per experiment. Start a new experiment to continue.")
            if any(r["run"]["id"] == run["id"] for r in exp["runs"]):
                raise ConflictError("This run ID is already imported. A correction needs a new run ID; the original remains in history.")
            if supersedes_record_id:
                original = next((r for r in exp["runs"] if r["record_id"] == supersedes_record_id), None)
                if original is None or original["run"]["designation"] != run["designation"]:
                    raise ValidationError("A correction must reference an existing run with the same designation.")
                if not correction_reason.strip():
                    raise ValidationError("Explain the correction so the original and revised records remain traceable.")
            record = {"record_id": new_id(), "run": run, "imported_at": now(), "source_filename": source_filename,
                      "source_text": source_text, "sha256": digest(source_text), "supersedes_record_id": supersedes_record_id,
                      "correction_reason": correction_reason}
            exp["runs"].append(record)
            exp["active_runs"][run["designation"]] = record["record_id"]
            self._mark_pending(exp)
        return self._mutate(experiment_id, action)

    def select_runs(self, experiment_id, bindings):
        if not isinstance(bindings, dict) or set(bindings) != {"baseline", "candidate"}:
            raise ValidationError("Select baseline and candidate run record IDs.")

        def action(exp):
            for role, record_id in bindings.items():
                if record_id is not None and (not isinstance(record_id, str) or not any(r["record_id"] == record_id and r["run"]["designation"] == role for r in exp["runs"])):
                    raise ValidationError(f"Invalid {role} record ID.")
            if exp["active_runs"] != bindings:
                exp["active_runs"] = bindings
                self._mark_pending(exp)
        return self._mutate(experiment_id, action)

    def decide(self, experiment_id, data):
        def action(exp):
            if not all(exp["active_runs"].values()):
                raise ValidationError("Import a baseline and a candidate before recording a comparison decision.")
            if len(exp["decisions"]) >= 200:
                raise ValidationError("V1 supports up to 200 decisions per experiment. Start a new experiment to continue.")
            validate_decision(data, evidence_keys(exp))
            decision = {**copy.deepcopy(data), "id": new_id(), "created_at": now(), "criteria_revision": exp["current_revision"],
                        "run_ids": dict(exp["active_runs"]), "comparison_snapshot": compare(exp), "setup_snapshot": copy.deepcopy(exp["setup"])}
            exp["decisions"].append(decision)
            exp["review_status"] = "reviewed"
        return self._mutate(experiment_id, action)

    def import_archive(self, source_text):
        if not isinstance(source_text, str):
            raise ValidationError("Archive source_text must be a UTF-8 JSON string.")
        exp = parse_json(source_text)
        validate_archive(exp)
        return self._insert(exp)

    def seed_demo(self, examples_path):
        with self.connect() as db:
            if db.execute("SELECT value FROM metadata WHERE key='demo_seeded'").fetchone():
                return
        from .fixtures import make_demo
        for incompatible in (True, False):
            exp = self.create(make_demo(incompatible)["setup"])
            names = ("baseline.json", "incompatible-candidate.json" if incompatible else "candidate.json")
            for name in names:
                path = Path(examples_path) / name
                self.import_run(exp["id"], path.read_text(encoding="utf-8"), name)
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('demo_seeded', '1')")
