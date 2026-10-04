"""Archive C inlet-assumption experiments and recheck saved thermal identities."""

from __future__ import annotations

import argparse
from datetime import datetime
import math
import re
import shutil
import sys
import uuid

from cycle_study import changed_snapshot
from cycle_validation import VALIDATION_VERSION, validate_cycle
from pipeline import run_case, verified_build, verify_test_report
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json

CASE = "cases/benchmarks/prescribed_cycle.ini"
SCOPE = "Synthetic prescribed-state inlet assumptions; no liquid property, adiabatic cycle, wall cooling or flight-engine validation."
RECIPES = {
    "baseline": None,
    "fuel_h_minus": ("fuel_pump_inlet_h_j_per_kg", -4750000.0),
    "fuel_h_plus": ("fuel_pump_inlet_h_j_per_kg", -4550000.0),
    "oxidizer_h_minus": ("oxidizer_pump_inlet_h_j_per_kg", -100000.0),
    "oxidizer_h_plus": ("oxidizer_pump_inlet_h_j_per_kg", 100000.0),
    "fuel_density_minus": ("fuel_pump_density_kg_per_m3", 379.8),
    "oxidizer_density_minus": ("oxidizer_pump_density_kg_per_m3", 1026.9),
}
RUN_FILES = {"input.ini", "result.json", "stdout.txt", "stderr.txt", "run-manifest.json"}
MANIFEST_KEYS = {
    "schema_version", "kind", "status", "started_at", "finished_at", "scope",
    "source_head", "source_dirty", "baseline_sha256", "runs", "files",
}
RUN_KEYS = {
    "schema_version", "kind", "run_id", "status", "started_at", "finished_at",
    "original_case_path", "input_sha256", "executable_sha256",
    "build_manifest_sha256", "test_report_sha256", "command", "exit_code",
    "accounting_checks", "validation_version", "output_file", "output_sha256",
}


def input_text(name, root=ROOT):
    text = (root / CASE).read_text(encoding="utf-8-sig")
    recipe = RECIPES[name]
    return changed_snapshot(text, *recipe) if recipe else text


def relation(actual, expected, label, absolute=1e-6):
    if (
        type(actual) not in (int, float)
        or not math.isfinite(actual)
        or not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=absolute)
    ):
        raise ValueError("Thermal experiment relation: " + label)


def timestamps(record):
    try:
        start = datetime.fromisoformat(record["started_at"])
        finish = datetime.fromisoformat(record["finished_at"])
        if start.utcoffset() is None or finish.utcoffset() is None or finish < start:
            raise ValueError("Timezone or ordering")
    except (TypeError, ValueError) as exc:
        raise ValueError("Thermal archive timestamp mismatch") from exc


def compare_inlet(name, report, base):
    """Check analytical consequences, not solve fluid properties or combustion."""
    if name == "baseline":
        return
    field, value = RECIPES[name]
    expected = dict(base["inputs"], **{field: value})
    if report["inputs"] != expected:
        raise ValueError("Experiment changed more than its declared inlet input")
    side = "fuel" if field.startswith("fuel_") else "oxidizer"
    b, r = base["energy"], report["energy"]
    if "inlet_h" in field:
        delta = value - base["inputs"][field]
        for section in ("flows", "turbine", "main_nozzle", "branch_nozzle", "performance"):
            if report[section] != base[section]:
                raise ValueError("Prescribed-state performance incorrectly depends on inlet enthalpy")
        for section, key in (("generator", "branch"), ("chamber", "main")):
            quantity = section + "_required_heat_w"
            relation(
                r[quantity] - b[quantity],
                -base["flows"][key + "_" + side + "_mass_flow_kg_per_s"] * delta,
                quantity,
            )
        relation(
            r["inlet_enthalpy_rate_w"] - b["inlet_enthalpy_rate_w"],
            base["flows"][side + "_mass_flow_kg_per_s"] * delta,
            "feed enthalpy change",
        )
        relation(r["pump_power_w"], b["pump_power_w"], "inlet h leaves pump work unchanged")
        relation(
            r["generator_required_heat_w"] + r["chamber_required_heat_w"]
            - b["generator_required_heat_w"] - b["chamber_required_heat_w"],
            -base["flows"][side + "_mass_flow_kg_per_s"] * delta,
            "net heat change",
        )
    else:
        factor = base["inputs"][field] / value
        expected_pump = base["pumps"][side]["shaft_power_w"] * factor
        relation(report["pumps"][side]["shaft_power_w"], expected_pump, "inverse-density pump work")
        relation(
            r["pump_power_w"] - b["pump_power_w"],
            expected_pump - base["pumps"][side]["shaft_power_w"],
            "one pump load change",
        )
        relation(
            report["turbine"]["specific_work_j_per_kg"],
            base["turbine"]["specific_work_j_per_kg"],
            "turbine prescribed state unchanged",
        )
        relation(
            report["flows"]["branch_mass_flow_kg_per_s"]
            - base["flows"]["branch_mass_flow_kg_per_s"],
            (r["pump_power_w"] - b["pump_power_w"])
            / base["inputs"]["shaft_efficiency"]
            / base["turbine"]["specific_work_j_per_kg"],
            "shaft-load branch response", 1e-12,
        )


def inventory_data():
    return {"build-manifest.json", "test-report.json"} | {
        name + "/" + filename for name in RECIPES for filename in RUN_FILES
    }


def inventory(folder):
    expected = inventory_data()
    actual = {
        p.relative_to(folder).as_posix()
        for p in folder.rglob("*")
        if p.is_file() and p != folder / "manifest.json"
    }
    directories = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_dir()}
    if (
        actual != expected or directories != set(RECIPES)
        or any(p.is_symlink() for p in folder.rglob("*"))
    ):
        raise ValueError("Thermal study inventory mismatch")
    return expected


def archive(destination, root=ROOT):
    target = local_path(root, destination)
    if target.exists():
        raise FileExistsError("Thermal study destination already exists")
    build_path = verified_build(root, "Release", require_tests=True)
    folder = root / "build/thermal-study-draft" / uuid.uuid4().hex
    folder.mkdir(parents=True)
    record = {
        "schema_version": 1, "kind": "thermal-boundary-study", "status": "RUNNING",
        "started_at": now(), "scope": SCOPE,
        "source_head": git(root, "rev-parse", "HEAD", check=True).stdout.strip(),
        "source_dirty": bool(git(root, "status", "--porcelain", check=True).stdout.strip()),
        "baseline_sha256": digest(root / CASE), "runs": [],
    }
    atomic_json(folder / "manifest.json", record)
    try:
        shutil.copy2(build_path, folder / "build-manifest.json")
        shutil.copy2(build_path.parent / "test-report.json", folder / "test-report.json")
        for name in RECIPES:
            case = folder / "generated-inputs" / (name + ".ini")
            atomic_text(case, input_text(name, root))
            run = run_case(root, case, no_build=True, model="prescribed-cycle")
            point = folder / name
            point.mkdir()
            for filename in RUN_FILES:
                shutil.copy2(run / filename, point / filename)
            if (
                digest(run / "build-manifest.json") != digest(folder / "build-manifest.json")
                or digest(run / "test-report.json") != digest(folder / "test-report.json")
            ):
                raise ValueError("Build/test changed between thermal experiments")
            count = len(validate_cycle(read_json(point / "result.json"), input_text(name, root), root))
            record["runs"].append({"id": name, "state_checks": count})
        record.update(
            status="PASS",
            files=[{"path": p, "sha256": digest(folder / p)} for p in sorted(inventory_data())],
        )
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        raise
    finally:
        record["finished_at"] = now()
        atomic_json(folder / "manifest.json", record)
    staged = folder / "archive"
    staged.mkdir()
    try:
        for item in record["files"]:
            dest = staged / item["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(folder / item["path"], dest)
        shutil.copy2(folder / "manifest.json", staged / "manifest.json")
        verify(staged, root)
        target.parent.mkdir(parents=True, exist_ok=True)
        staged.rename(target)
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        atomic_json(folder / "manifest.json", record)
        raise
    return target


def verify(folder, root=ROOT):
    record = read_json(folder / "manifest.json")
    if (
        not isinstance(record, dict) or set(record) != MANIFEST_KEYS
        or type(record["schema_version"]) is not int or record["schema_version"] != 1
        or record["kind"] != "thermal-boundary-study" or record["status"] != "PASS"
        or record["scope"] != SCOPE or type(record["source_dirty"]) is not bool
        or not isinstance(record["source_head"], str)
        or not re.fullmatch("[a-f0-9]{40}", record["source_head"])
        or record["baseline_sha256"] != digest(root / CASE)
    ):
        raise ValueError("Thermal study identity/scope mismatch")
    timestamps(record)
    expected = inventory(folder)
    files = record["files"]
    if (
        not isinstance(files, list) or len(files) != len(expected)
        or any(
            not isinstance(f, dict) or set(f) != {"path", "sha256"}
            or not isinstance(f["path"], str) or not isinstance(f["sha256"], str)
            or not re.fullmatch("[a-f0-9]{64}", f["sha256"]) for f in files
        )
        or {f["path"] for f in files} != expected
    ):
        raise ValueError("Thermal study file list mismatch")
    for item in files:
        if digest(local_path(folder, item["path"])) != item["sha256"]:
            raise ValueError("Thermal study hash mismatch")
    build = read_json(folder / "build-manifest.json")
    tests = read_json(folder / "test-report.json")
    verify_test_report(tests, build, digest(folder / "build-manifest.json"))
    runs = record["runs"]
    if not isinstance(runs, list) or len(runs) != len(RECIPES):
        raise ValueError("Thermal study run count mismatch")
    base = read_json(folder / "baseline/result.json")
    for recipe, name in zip(runs, RECIPES):
        if (
            not isinstance(recipe, dict) or set(recipe) != {"id", "state_checks"}
            or recipe["id"] != name or type(recipe["state_checks"]) is not int
            or recipe["state_checks"] <= 0
        ):
            raise ValueError("Thermal study recipe/count mismatch")
        point = folder / name
        text = (point / "input.ini").read_text(encoding="utf-8-sig")
        if text != input_text(name, root):
            raise ValueError("Thermal study input changed")
        report = read_json(point / "result.json")
        run = read_json(point / "run-manifest.json")
        if (
            not isinstance(run, dict) or set(run) != RUN_KEYS
            or type(run["schema_version"]) is not int or run["schema_version"] != 2
            or run["kind"] != "run" or run["status"] != "SUCCESS"
            or not isinstance(run["run_id"], str) or not run["run_id"].strip()
            or not isinstance(run["original_case_path"], str)
            or not run["original_case_path"].strip()
            or type(run["exit_code"]) is not int or run["exit_code"] != 0
            or run["command"] != ["rocketperf.exe", "cycle", "prescribed", "input.ini"]
            or type(run["validation_version"]) is not int
            or run["validation_version"] != VALIDATION_VERSION
            or type(run["accounting_checks"]) is not int
            or run["accounting_checks"] != recipe["state_checks"]
            or run["executable_sha256"] != build["application"]["sha256"]
            or run["output_file"] != "result.json"
        ):
            raise ValueError("Thermal run identity/protocol mismatch")
        timestamps(run)
        for key, path in (
            ("input_sha256", point / "input.ini"),
            ("output_sha256", point / "result.json"),
            ("build_manifest_sha256", folder / "build-manifest.json"),
            ("test_report_sha256", folder / "test-report.json"),
        ):
            if run[key] != digest(path):
                raise ValueError("Thermal run snapshot mismatch")
        if (
            (point / "stdout.txt").read_bytes() != (point / "result.json").read_bytes()
            or (point / "stderr.txt").read_bytes()
            or len(validate_cycle(report, text, root)) != recipe["state_checks"]
        ):
            raise ValueError("Thermal run state/equation mismatch")
        compare_inlet(name, report, base)
    return len(runs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["archive", "verify"])
    parser.add_argument("directory")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        if args.action == "archive":
            print(archive(args.directory))
        else:
            print("Thermal study verified: " + str(verify(local_path(ROOT, args.directory))) + " runs")
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
