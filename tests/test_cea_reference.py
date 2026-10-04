"""Archived CEA evidence and raw-output defect guards, without external runtime."""

from pathlib import Path
import copy
import json
import shutil
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import cea_reference
from combustion_reference import check_archive, compare_report
import research_tp_reference
from projectlib import digest

TP_ARCHIVE = ROOT / "results/research/reference-coverage/tp_v1_20261004"


class CeaReferenceTests(unittest.TestCase):
    def test_reference_timeout_preserves_partial_logs_and_raises(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            stdout = folder / "stdout.txt"
            stderr = folder / "stderr.txt"
            timeout = subprocess.TimeoutExpired(
                ["solver"], 1, output=b"partial output", stderr=b"partial diagnostic"
            )
            with mock.patch.object(research_tp_reference.subprocess, "run", side_effect=timeout):
                with self.assertRaises(subprocess.TimeoutExpired):
                    research_tp_reference.run_logged(["solver"], folder, stdout, stderr, 1)
            self.assertEqual(stdout.read_text(encoding="utf-8"), "partial output")
            self.assertEqual(stderr.read_text(encoding="utf-8"), "partial diagnostic")

    def test_existing_archive_cannot_be_overwritten(self):
        with self.assertRaises(FileExistsError):
            research_tp_reference.archive(TP_ARCHIVE.relative_to(ROOT).as_posix())

    def test_actual_study_tp_archive_without_external_runtime(self):
        self.assertEqual(research_tp_reference.verify(TP_ARCHIVE), 6)

    def test_tp_archive_manifest_shape_and_typed_identity(self):
        for defect in (
            "schema",
            "dirty",
            "missing",
            "case_shape",
            "index",
            "exit",
            "input",
            "comparison",
            "duplicate",
            "directory",
            "cea_binary",
            "scope",
        ):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary) / "archive"
                shutil.copytree(TP_ARCHIVE, folder)
                path = folder / "manifest.json"
                record = json.loads(path.read_text(encoding="utf-8"))
                if defect == "schema":
                    record["schema_version"] = True
                if defect == "dirty":
                    record["source_dirty"] = 1
                if defect == "missing":
                    record.pop("c_binary_sha256")
                if defect == "case_shape":
                    record["cases"][0] = []
                if defect == "index":
                    record["cases"][2]["point_index"] = False
                if defect == "exit":
                    record["cases"][0]["c_exit_code"] = False
                if defect == "input":
                    record["cases"][1]["inputs"]["oxidizer_fuel_mass_ratio"] = True
                if defect == "comparison":
                    record["cases"][0]["comparisons"][-1]["reference"] = False
                if defect == "duplicate":
                    record["cases"][1] = copy.deepcopy(record["cases"][0])
                if defect == "directory":
                    (folder / "undeclared").mkdir()
                if defect == "cea_binary":
                    record["cea_binary_sha256"] = "0" * 64
                if defect == "scope":
                    record["scope"] = "Full engine validation"
                path.write_text(json.dumps(record), encoding="utf-8")
                with self.assertRaises(ValueError):
                    research_tp_reference.verify(folder)

    def test_tp_numeric_and_trace_mutations_rejected_even_after_rehash(self):
        for defect in ("enthalpy", "boolean_input", "temperature", "trace"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary) / "archive"
                shutil.copytree(TP_ARCHIVE, folder)
                manifest = folder / "manifest.json"
                record = json.loads(manifest.read_text(encoding="utf-8"))
                filename = (
                    "generator_base-c.json" if defect == "boolean_input" else "main_base-c.json"
                )
                if defect == "trace":
                    filename = "generator_base.out"
                    path = folder / filename
                    text = path.read_text(encoding="ascii")
                    marker = "WERE LESS THAN 1.000000E-08 FOR ALL ASSIGNED CONDITIONS"
                    self.assertIn(marker, text)
                    path.write_text(text.replace(marker, "TRACE LIST OMITTED"), encoding="ascii")
                else:
                    path = folder / filename
                    report = json.loads(path.read_text(encoding="utf-8"))
                    if defect == "enthalpy":
                        report["chamber"]["h_j_per_kg"] += 100
                    if defect == "boolean_input":
                        report["inputs"]["oxidizer_fuel_mass_ratio"] = True
                    if defect == "temperature":
                        report["inputs"]["temperature_k"] += 1
                    path.write_text(json.dumps(report), encoding="utf-8")
                next(f for f in record["files"] if f["path"] == filename)["sha256"] = digest(path)
                manifest.write_text(json.dumps(record), encoding="utf-8")
                with self.assertRaises(ValueError):
                    research_tp_reference.verify(folder)

    def test_current_method_archive_under_extended_checks(self):
        check_archive(ROOT / "results/validation/ana002_method_reference_20261004")

    def test_negative_properties_bool_schema_and_fake_station_rejected(self):
        reference = next(
            r
            for r in cea_reference.check_reference()["cases"]
            if r["id"] == "ch4_o2_rocket_frozen_chamber"
        )
        report = json.loads(
            (
                ROOT / "results/validation/ana002_method_reference_20261004/frozen10-stdout.json"
            ).read_text(encoding="utf-8")
        )
        for defect in ("cp", "R", "schema", "flux", "mach", "residual", "limits", "booliteration"):
            candidate = copy.deepcopy(report)
            if defect == "cp":
                candidate["chamber"]["cp_frozen_j_per_kg_k"] = -1
            if defect == "R":
                candidate["chamber"]["gas_constant_j_per_kg_k"] = -1
            if defect == "schema":
                candidate["schema_version"] = True
            if defect == "flux":
                candidate["nozzle"]["exit"]["mass_flux_kg_per_m2_s"] *= 2
            if defect == "mach":
                candidate["nozzle"]["exit"]["mach"] = -1
            if defect == "residual":
                candidate["diagnostics"]["enthalpy_residual_j_per_kg"] = 0.009
            if defect == "limits":
                candidate["limitations"] = "claimed"
            if defect == "booliteration":
                candidate["diagnostics"]["hp_iterations"] = True
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                compare_report(candidate, reference, "frozen", 10)

    def test_fixed_archive(self):
        manifest = cea_reference.check_reference()
        self.assertEqual(len(manifest["cases"]), 4)
        cases = {case["id"]: case["summary"] for case in manifest["cases"]}
        self.assertEqual(cases["ch4_o2_hp"]["rows"]["temperature_k"], [3673.61])
        self.assertEqual(cases["ch4_o2_rocket_equilibrium"]["rows"]["temperature_k"][0], 3673.61)
        self.assertEqual(cases["ch4_o2_rocket_frozen_chamber"]["rows"]["temperature_k"][0], 3673.61)

    def test_initial_invalid_bytes_not_silently_cleaned(self):
        raw = ROOT / "tests/reference/cea/raw/ch4_o2_hp.out"
        with self.assertRaises((UnicodeDecodeError, ValueError)):
            cea_reference.parse_output(raw.read_bytes())

    def test_bad_output_and_wrong_chemistry_fail(self):
        with self.assertRaises(ValueError):
            cea_reference.parse_output(b"T, K 3000\n")
        path = ROOT / "tests/reference/cea/raw/trace1e8/ch4_o2_rocket_equilibrium.out"
        with self.assertRaises(ValueError):
            cea_reference.parse_output(path.read_bytes(), rocket=True, frozen=True)
        with self.assertRaises(ValueError):
            cea_reference.parse_output(path.read_bytes().replace(b"1.5294", b"NaN"), rocket=True)

    def test_trace_omission_must_be_explicit_and_species_unique(self):
        data = (ROOT / "tests/reference/cea/raw/trace1e8/ch4_o2_hp.out").read_bytes()
        with self.assertRaises(ValueError):
            cea_reference.parse_output(data.replace(b" CH4            ", b" "))
        with self.assertRaises(ValueError):
            cea_reference.parse_output(
                data.replace(
                    b" H2                    0.084502",
                    b" H2                    0.084502\n H2                    0.084502",
                )
            )

    def test_custom_tp_conditions_must_match_report_and_types(self):
        record = cea_reference.check_reference()
        reference = next(c for c in record["cases"] if c["id"] == "ch4_o2_tp")
        report = json.loads(
            (ROOT / "results/validation/ana002_method_reference_20261004/tp-stdout.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(compare_report(report, reference, "tp", expected_inputs=report["inputs"]))
        for defect in ("pressure", "boolean", "missing", "mode"):
            inputs = dict(report["inputs"])
            if defect == "pressure":
                inputs["pressure_pa"] = 5e6
            if defect == "boolean":
                inputs["temperature_k"] = True
            if defect == "missing":
                inputs.pop("feed_phase")
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                compare_report(
                    report, reference, "hp" if defect == "mode" else "tp", expected_inputs=inputs
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
