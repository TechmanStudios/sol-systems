import copy
import json
import unittest

from observatory.domain import (ValidationError, compare, digest, markdown_report, parse_json,
                                validate_archive, validate_run, validate_setup)
from observatory.fixtures import make_demo
from observatory.store import Store
import tempfile
from pathlib import Path


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.demo = make_demo()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "test.db")
        self.exp = self.store.create(self.demo["setup"])
        for role in ("baseline", "candidate"):
            self.exp = self.store.import_run(self.exp["id"], json.dumps(self.demo[role]), role + ".json")

    def row(self, index=0):
        return compare(self.exp)["metrics"][index]

    def value(self, role, value, index=0):
        next(r for r in self.exp["runs"] if r["run"]["designation"] == role)["run"]["measurements"][index]["value"] = value

    def test_demo_tradeoffs(self):
        result = compare(self.exp)
        self.assertEqual(result["counts"], {"improved": 1, "regressed": 2, "unchanged": 0, "unknown": 1, "incompatible": 0})
        self.assertEqual(result["comparability"], "compatible")
        self.assertEqual(self.row()["delta"], 24)
        self.assertIn("SYNTHETIC", result["limitations"][0])

    def test_higher_direction(self):
        self.value("candidate", 60)
        self.assertEqual(self.row()["status"], "regressed")

    def test_lower_direction(self):
        self.value("candidate", 60, 1)
        self.assertEqual(self.row(1)["status"], "improved")
        self.assertLess(self.row(1)["percent_change"], 0)

    def test_equal_values(self):
        self.value("candidate", 68)
        self.assertEqual(self.row()["status"], "unchanged")

    def test_higher_threshold_is_inclusive(self):
        self.value("candidate", 85)
        self.assertEqual(self.row()["threshold_status"], "pass")
        self.value("candidate", 84.99)
        self.assertEqual(self.row()["threshold_status"], "fail")

    def test_lower_threshold_is_inclusive(self):
        self.value("candidate", 120, 1)
        self.assertEqual(self.row(1)["threshold_status"], "pass")
        self.value("candidate", 120.01, 1)
        self.assertEqual(self.row(1)["threshold_status"], "fail")

    def test_guardrails_are_individual(self):
        self.assertEqual(self.row(1)["guardrail_status"], "pass")
        self.assertEqual(self.row(2)["guardrail_status"], "fail")
        self.assertEqual(self.row(2)["threshold_status"], "pass")

    def test_guardrail_boundary_is_inclusive(self):
        self.value("baseline", 100, 1)
        self.value("candidate", 160, 1)
        self.assertEqual(self.row(1)["guardrail_status"], "pass")
        self.value("candidate", 160.001, 1)
        self.assertEqual(self.row(1)["guardrail_status"], "fail")

    def test_zero_revision_is_not_current_revision(self):
        with self.assertRaises(ValidationError):
            compare(self.exp, 0)

    def test_report_preserves_incompatible_measurement_unit(self):
        self.exp["runs"][1]["run"]["measurements"][0]["unit"] = "fraction"
        self.assertIn("92 fraction", markdown_report(self.exp))

    def test_null_stays_unknown(self):
        row = self.row(3)
        self.assertEqual(row["status"], "unknown")
        self.assertIsNone(row["delta"])
        self.assertEqual(row["threshold_status"], "unknown")
        self.assertEqual(row["guardrail_status"], "unknown")

    def test_omitted_measurement_stays_unknown(self):
        self.exp["runs"][1]["run"]["measurements"] = []
        self.assertEqual(self.row()["status"], "unknown")
        self.assertIsNone(self.row()["delta"])

    def test_missing_baseline_can_check_candidate_target(self):
        self.value("baseline", None)
        self.assertEqual(self.row()["threshold_status"], "pass")
        self.assertEqual(self.row()["guardrail_status"], "unknown")

    def test_zero_baseline_has_no_relative_change(self):
        self.value("baseline", 0)
        row = self.row()
        self.assertEqual(row["delta"], 92)
        self.assertIsNone(row["percent_change"])
        self.assertTrue(any("Zero baseline" in n for n in row["notes"]))

    def test_zero_baseline_regression_zero_tolerance(self):
        self.value("baseline", 0)
        self.value("candidate", -1)
        self.assertEqual(self.row()["guardrail_status"], "fail")

    def test_zero_baseline_positive_relative_tolerance_is_unknown(self):
        self.value("baseline", 0, 1)
        self.assertEqual(self.row(1)["guardrail_status"], "unknown")

    def test_negative_baseline_uses_magnitude(self):
        self.value("baseline", -20)
        self.value("candidate", -10)
        self.assertEqual(self.row()["percent_change"], 50)
        self.assertEqual(self.row()["status"], "improved")

    def test_tiny_baseline_does_not_emit_infinity(self):
        self.value("baseline", 5e-324)
        self.assertIsNone(self.row()["percent_change"])
        json.dumps(compare(self.exp), allow_nan=False)

    def test_incompatible_units(self):
        self.exp["runs"][1]["run"]["measurements"][0]["unit"] = "fraction"
        self.assertEqual(self.row()["status"], "incompatible")
        self.assertIsNone(self.row()["delta"])
        self.assertEqual(self.row()["threshold_status"], "unknown")

    def test_incompatible_method_version(self):
        self.exp["runs"][1]["run"]["measurements"][0]["method"]["version"] = "audit/2"
        self.assertEqual(self.row()["status"], "incompatible")

    def test_human_rating_is_not_a_measurement(self):
        self.exp["runs"][1]["run"]["measurements"][0]["method"]["kind"] = "human_rating"
        self.assertEqual(self.row()["status"], "incompatible")

    def test_input_mismatch_blocks_differences(self):
        self.exp["runs"][1]["run"]["input"] += " extra task"
        result = compare(self.exp)
        self.assertEqual(result["comparability"], "incompatible")
        self.assertTrue(all(row["delta"] is None for row in result["metrics"]))

    def test_conditions_mismatch(self):
        self.exp["runs"][1]["run"]["conditions"]["seed"] = 9
        self.assertEqual(compare(self.exp)["comparability"], "incompatible")

    def test_json_boolean_condition_is_not_integer(self):
        self.exp["runs"][0]["run"]["conditions"] = {"seed": 1}
        self.exp["runs"][1]["run"]["conditions"] = {"seed": True}
        self.assertEqual(compare(self.exp)["comparability"], "incompatible")

    def test_unknown_conditions_stay_visible(self):
        for record in self.exp["runs"]:
            record["run"]["conditions"] = {}
        self.assertEqual(compare(self.exp)["comparability"], "limited")

    def test_synthetic_cannot_be_compared_to_real_origin(self):
        self.exp["runs"][1]["run"]["data_type"] = "manual"
        self.assertEqual(compare(self.exp)["comparability"], "incompatible")

    def test_configuration_change_is_allowed(self):
        self.exp["runs"][1]["run"]["configuration"]["verification_pass"] = "a different implementation"
        self.assertEqual(compare(self.exp)["comparability"], "compatible")

    def test_unlinked_measurement_is_self_reported(self):
        self.exp["runs"][1]["run"]["measurements"][0]["evidence_ids"] = []
        self.assertIn("self-reported", " ".join(self.row()["notes"]))

    def test_output_diff_has_additions_and_removals(self):
        diff = compare(self.exp)["output_diff"]
        self.assertIn("+Evidence: 46", diff)
        self.assertIn("-Evidence: 34", diff)

    def test_complete_archive_validates(self):
        validate_archive(self.exp)

    def test_no_pair_is_incomplete(self):
        self.exp["active_runs"]["candidate"] = None
        self.assertEqual(compare(self.exp)["comparability"], "incomplete")
        self.assertEqual(compare(self.exp)["output_diff"], "")

    def test_output_diff_final_lines_stay_separate(self):
        diff = compare(self.exp)["output_diff"]
        self.assertIn("\n+Pilot:", diff)

    def test_report_has_decision_boundary_and_evidence(self):
        report = markdown_report(self.exp)
        for expected in ("SYNTHETIC", "unknown", "synthetic://", "No statistical significance", "Awaiting human review", "Criteria revision history"):
            self.assertIn(expected, report)

    def test_report_metric_table_is_contiguous(self):
        report = markdown_report(self.exp)
        table = report.split("| Criterion |")[1].split("### Measurement methods")[0]
        self.assertEqual(len([line for line in table.splitlines() if line.startswith("|")]), 5)

    def test_report_does_not_embed_imported_images(self):
        self.exp["runs"][0]["run"]["evidence"][0]["reference"] = "![tracker](https://example.invalid/tracker)"
        report = markdown_report(self.exp)
        self.assertNotIn("![tracker]", report)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.run = make_demo()["baseline"]

    def test_valid_example(self):
        validate_run(self.run)

    def test_malformed_json(self):
        with self.assertRaises(ValidationError):
            parse_json('{"id":')

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValidationError):
            parse_json('{"id":"one","id":"two"}')

    def test_nonfinite_json_rejected(self):
        for text in ('{"n":NaN}', '{"n":Infinity}', '{"n":1e999}', '{"n":-Infinity}'):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                parse_json(text)

    def test_arrays_are_not_documents(self):
        with self.assertRaises(ValidationError):
            parse_json('[]')

    def test_future_schema_not_silently_accepted(self):
        self.run["schema_version"] = "2.0"
        with self.assertRaisesRegex(ValidationError, "schema_version"):
            validate_run(self.run)

    def test_unknown_fields_not_silently_dropped(self):
        self.run["unexpected"] = True
        with self.assertRaisesRegex(ValidationError, "unexpected"):
            validate_run(self.run)

    def test_unknown_evidence_id(self):
        self.run["measurements"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(ValidationError, "unknown evidence"):
            validate_run(self.run)

    def test_boolean_not_a_measurement(self):
        self.run["measurements"][0]["value"] = True
        with self.assertRaises(ValidationError):
            validate_run(self.run)

    def test_timestamp_requires_timezone(self):
        self.run["executed_at"] = "2026-10-15T14:00:00"
        with self.assertRaisesRegex(ValidationError, "timezone"):
            validate_run(self.run)

    def test_duplicate_measurement_ids(self):
        self.run["measurements"].append(copy.deepcopy(self.run["measurements"][0]))
        with self.assertRaisesRegex(ValidationError, "unique"):
            validate_run(self.run)

    def test_duplicate_evidence_ids(self):
        self.run["evidence"].append(copy.deepcopy(self.run["evidence"][0]))
        with self.assertRaisesRegex(ValidationError, "unique"):
            validate_run(self.run)

    def test_invalid_shapes_give_validation_errors(self):
        for field in self.run:
            for value in (None, [], {"bad": True}, True, 42):
                if field in ("conditions", "configuration") and isinstance(value, dict):
                    continue
                if field == "workflow_version" and value is None:
                    continue
                if field == "measurements" and value == []:
                    continue
                with self.subTest(field=field, value=value):
                    broken = copy.deepcopy(self.run)
                    broken[field] = value
                    with self.assertRaises(ValidationError):
                        validate_run(broken)

    def test_nested_shapes_give_validation_errors(self):
        for field in self.run["measurements"][0]:
            broken = copy.deepcopy(self.run)
            broken["measurements"][0][field] = {"bad": "shape"}
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_run(broken)

    def test_negative_regression_tolerance_rejected(self):
        setup = make_demo()["setup"]
        setup["criteria"][0]["max_regression_percent"] = -1
        with self.assertRaises(ValidationError):
            validate_setup(setup)

    def test_reference_is_preserved_as_text(self):
        self.run["evidence"][0]["reference"] = "javascript:alert('not executed')"
        validate_run(self.run)
        self.assertTrue(self.run["evidence"][0]["reference"].startswith("javascript:"))


if __name__ == "__main__":
    unittest.main()
