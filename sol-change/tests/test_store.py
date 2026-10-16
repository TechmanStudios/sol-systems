import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from observatory.domain import ValidationError, compare, digest, markdown_report, validate_archive
from observatory.fixtures import make_demo
from observatory.store import ConflictError, Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "observatory.db"
        self.store = Store(self.path)
        self.demo = make_demo()
        self.exp = self.store.create(self.demo["setup"])
        for role in ("baseline", "candidate"):
            source = "\ufeff" + json.dumps(self.demo[role], indent=2).replace("\n", "\r\n") + "\r\n"
            self.exp = self.store.import_run(self.exp["id"], source, f"{role}.json")

    def decision(self):
        record = self.exp["runs"][1]
        return {"outcome": "mixed", "action": "run_another_experiment", "reviewer": "Synthetic QA reviewer", "rationale": "Better citations, higher cost, and usefulness is unmeasured. Repeat trials and obtain a reader review.",
                "supporting_evidence": [f'{record["record_id"]}:citation-audit'], "unresolved_questions": ["Will usefulness hold across repeated trials?"]}

    def test_new_store_reopens_saved_decision(self):
        expected = self.store.decide(self.exp["id"], self.decision())
        reopened = Store(self.path)
        self.assertEqual(reopened.get(self.exp["id"]), expected)
        self.assertEqual(expected["review_status"], "reviewed")
        self.assertEqual(expected["decisions"][0]["comparison_snapshot"], compare(expected))

    def test_export_import_exact_round_trip(self):
        expected = self.store.decide(self.exp["id"], self.decision())
        target = Store(Path(self.temp.name) / "restored.db")
        restored = target.import_archive(json.dumps(expected, ensure_ascii=False))
        self.assertEqual(expected, restored)
        self.assertEqual(target.get(restored["id"]), expected)
        validate_archive(restored)

    def test_source_text_and_hash_stay_intact(self):
        for record in self.exp["runs"]:
            self.assertTrue(record["source_text"].startswith("\ufeff"))
            self.assertIn("\r\n", record["source_text"])
            self.assertEqual(record["sha256"], digest(record["source_text"]))

    def test_correction_appends_and_preserves_original(self):
        original = copy.deepcopy(self.exp["runs"][1])
        corrected = copy.deepcopy(self.demo["candidate"])
        corrected["id"] += "-correction-1"
        corrected["measurements"][2]["value"] = 0.35
        changed = self.store.import_run(self.exp["id"], json.dumps(corrected), "correction.json", original["record_id"], "Corrected the invented usage ledger.")
        self.assertEqual(changed["runs"][1], original)
        self.assertEqual(changed["runs"][-1]["supersedes_record_id"], original["record_id"])
        self.assertEqual(len(changed["runs"]), 3)
        validate_archive(changed)

    def test_correction_requires_reason(self):
        corrected = copy.deepcopy(self.demo["candidate"])
        corrected["id"] = "new-run"
        with self.assertRaisesRegex(ValidationError, "Explain"):
            self.store.import_run(self.exp["id"], json.dumps(corrected), "new.json", self.exp["runs"][1]["record_id"])
        self.assertEqual(self.store.get(self.exp["id"]), self.exp)

    def test_duplicate_run_id_never_overwrites(self):
        with self.assertRaises(ConflictError):
            self.store.import_run(self.exp["id"], json.dumps(self.demo["candidate"]))
        self.assertEqual(self.store.get(self.exp["id"]), self.exp)

    def test_duplicate_archive_never_overwrites(self):
        with self.assertRaises(ConflictError):
            self.store.import_archive(json.dumps(self.exp))
        self.assertEqual(self.store.get(self.exp["id"]), self.exp)

    def test_criteria_revision_preserves_old_decision(self):
        decided = self.store.decide(self.exp["id"], self.decision())
        before = copy.deepcopy(decided["decisions"][0])
        setup = copy.deepcopy(self.demo["setup"])
        setup["criteria"][2]["threshold"] = 0.30
        changed = self.store.update_setup(self.exp["id"], setup)
        self.assertEqual(changed["current_revision"], 2)
        self.assertTrue(changed["criteria_revisions"][-1]["after_results"])
        self.assertEqual(changed["decisions"][0], before)
        self.assertEqual(changed["review_status"], "awaiting_review")
        self.assertEqual(compare(changed, 1)["metrics"][2]["threshold_status"], "pass")
        self.assertEqual(compare(changed, 2)["metrics"][2]["threshold_status"], "fail")
        target = Store(Path(self.temp.name) / "revisions.db")
        self.assertEqual(target.import_archive(json.dumps(changed)), changed)

    def test_unchanged_setup_does_not_add_revision(self):
        changed = self.store.update_setup(self.exp["id"], self.demo["setup"])
        self.assertEqual(changed["current_revision"], 1)

    def test_run_selection_invalidates_review_without_erasing_it(self):
        decided = self.store.decide(self.exp["id"], self.decision())
        candidate = copy.deepcopy(self.demo["candidate"])
        candidate["id"] = "another-candidate"
        changed = self.store.import_run(self.exp["id"], json.dumps(candidate))
        changed = self.store.select_runs(self.exp["id"], decided["active_runs"])
        self.assertEqual(changed["decisions"], decided["decisions"])
        self.assertEqual(changed["active_runs"], decided["active_runs"])
        self.assertEqual(changed["review_status"], "awaiting_review")

    def test_invalid_run_selection_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.select_runs(self.exp["id"], {"baseline": self.exp["active_runs"]["candidate"], "candidate": None})

    def test_decisions_append(self):
        self.store.decide(self.exp["id"], self.decision())
        changed = self.store.decide(self.exp["id"], {**self.decision(), "outcome": "inconclusive"})
        self.assertEqual(len(changed["decisions"]), 2)
        validate_archive(changed)

    def test_outcome_and_review_status_are_separate(self):
        self.assertEqual(self.exp["review_status"], "awaiting_review")
        self.assertEqual(self.exp["decisions"], [])
        changed = self.store.decide(self.exp["id"], {**self.decision(), "outcome": "inconclusive"})
        self.assertEqual(changed["review_status"], "reviewed")
        self.assertEqual(changed["decisions"][-1]["outcome"], "inconclusive")

    def test_decision_evidence_must_belong_to_pair(self):
        with self.assertRaises(ValidationError):
            self.store.decide(self.exp["id"], {**self.decision(), "supporting_evidence": ["unknown:source"]})

    def test_archive_source_tampering_detected(self):
        self.exp["runs"][0]["source_text"] += " "
        with self.assertRaisesRegex(ValidationError, "SHA-256"):
            validate_archive(self.exp)

    def test_archive_snapshot_tampering_detected(self):
        exp = self.store.decide(self.exp["id"], self.decision())
        exp["decisions"][0]["comparison_snapshot"]["metrics"][0]["delta"] = 100
        with self.assertRaisesRegex(ValidationError, "snapshot"):
            validate_archive(exp)

    def test_archive_unknown_revision_detected(self):
        self.exp["current_revision"] = 99
        with self.assertRaises(ValidationError):
            validate_archive(self.exp)

    def test_malformed_archive_records_are_clear_validation_errors(self):
        for name in ("record_id", "supersedes_record_id", "source_text", "run"):
            broken = copy.deepcopy(self.exp)
            broken["runs"][0][name] = []
            with self.subTest(name=name), self.assertRaises(ValidationError):
                validate_archive(broken)

    def test_concurrent_imports_do_not_lose_history(self):
        def add(index):
            run = copy.deepcopy(self.demo["candidate"])
            run["id"] = f"concurrent-{index}"
            self.store.import_run(self.exp["id"], json.dumps(run))
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(add, range(8)))
        changed = self.store.get(self.exp["id"])
        self.assertEqual(len(changed["runs"]), 10)
        validate_archive(changed)

    def test_report_contains_saved_decision(self):
        exp = self.store.decide(self.exp["id"], self.decision())
        report = markdown_report(exp)
        for value in (self.decision()["rationale"], "Synthetic QA reviewer", "run another experiment", self.exp["active_runs"]["candidate"]):
            self.assertIn(value, report)

    def test_demo_seeds_once_across_restart(self):
        examples = Path(__file__).resolve().parents[1] / "examples"
        fresh_path = Path(self.temp.name) / "demo.db"
        store = Store(fresh_path)
        store.seed_demo(examples)
        expected = store.list()
        reopened = Store(fresh_path)
        reopened.seed_demo(examples)
        self.assertEqual(len(expected), 2)
        self.assertEqual(reopened.list(), expected)

    def test_decision_with_malformed_bindings_rejected(self):
        exp = self.store.decide(self.exp["id"], self.decision())
        exp["decisions"][0]["run_ids"]["baseline"] = []
        with self.assertRaises(ValidationError):
            validate_archive(exp)


if __name__ == "__main__":
    unittest.main()
