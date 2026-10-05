"""Archive explicit gas-inlet HP runs; replay checks do not solve production physics."""

from __future__ import annotations

import argparse
from datetime import datetime
import math
import re
import shutil
import subprocess
import sys
import uuid

from cea_reference import check_reference
from combustion_reference import compare_report
from gas_checks import database, mixture
from pipeline import strict_json, verified_build, verify_test_report
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json
from research_tp_reference import run_logged

SCOPE = "Explicit NASA9-basis CH4/O2 gas HP and fixed-area chamber-frozen single nozzle; not liquid properties, flight performance or full-cycle closure."
BASE = ["10000000", "3.4", "298.15", "298.15"]
REFERENCES = ("ch4_o2_hp", "ch4_o2_rocket_frozen_chamber")
REQUIRED_KEYS = {
    "schema_version", "kind", "status", "scope", "started_at", "finished_at",
    "source_head", "source_dirty", "binary_sha256", "build_manifest_sha256",
    "test_report_sha256", "cea_manifest_sha256", "runs", "comparisons", "files",
}


def recipes(fuel_h, oxidizer_h):
    prefix = ["nasa9-cea-v3.3.4", "gas", *BASE[:2], format(fuel_h, ".17g"), format(oxidizer_h, ".17g")]
    return [
        ("fuel", ["thermo", "CH4", "298.15"], 0),
        ("oxidizer", ["thermo", "O2", "298.15"], 0),
        ("temperature_hp", ["combustion", "hp", *BASE], 0),
        ("temperature_A10", ["combustion", "frozen", *BASE, "10", "0"], 0),
        ("temperature_A40", ["combustion", "frozen", *BASE, "40", "0"], 0),
        ("enthalpy_hp", ["combustion", "hp-h", *prefix], 0),
        ("enthalpy_A10", ["combustion", "frozen-h", *prefix, "10", "0", "0.01"], 0),
        ("enthalpy_A40", ["combustion", "frozen-h", *prefix, "40", "0", "0.01"], 0),
        ("double_area", ["combustion", "frozen-h", *prefix, "10", "0", "0.02"], 0),
        ("ambient_5000", ["combustion", "frozen-h", *prefix, "10", "5000", "0.01"], 0),
        ("reject_basis", ["combustion", "hp-h", "arbitrary-zero", *prefix[1:]], 4),
        ("reject_liquid", ["combustion", "hp-h", prefix[0], "liquid", *prefix[2:]], 4),
        ("reject_h", ["combustion", "hp-h", *prefix[:4], "-1e308", prefix[5]], 4),
        ("reject_backpressure", ["combustion", "frozen-h", *prefix, "40", "100000", "0.01"], 4),
        ("reject_nan", ["combustion", "hp-h", *prefix[:4], "nan", prefix[5]], 2),
    ]


def supplied(fuel_h, oxidizer_h, area=None, ambient=0.0, throat=0.01):
    values = dict(feed_phase="gas", enthalpy_basis="nasa9-cea-v3.3.4",
                  pressure_pa=1e7, oxidizer_fuel_mass_ratio=3.4,
                  fuel_h_j_per_kg=fuel_h, oxidizer_h_j_per_kg=oxidizer_h)
    if area is not None:
        values.update(area_ratio=area, ambient_pressure_pa=ambient, throat_area_m2=throat)
    return values


def read_output(folder, name):
    return strict_json((folder / (name + "-stdout.txt")).read_text(encoding="utf-8"))


def relation(actual, expected, label, absolute=1e-7):
    if (type(actual) not in (int, float) or not math.isfinite(actual)
        or not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=absolute)):
        raise ValueError("Adiabatic archive relation failed: " + label)


def inlet_value(folder, name, species, temperature=298.15):
    report = read_output(folder, name)
    keys = {"schema_version", "model", "dataset_id", "species", "temperature_k",
            "reference_pressure_pa", "molar_mass_kg_per_kmol", "cp_j_per_kg_k",
            "h_j_per_kg", "s_j_per_kg_k", "limitations"}
    fits = database()
    if (not isinstance(report, dict) or set(report) != keys
        or type(report["schema_version"]) is not int or report["schema_version"] != 1
        or report["model"] != "nasa9_species_v1" or report["dataset_id"] != fits["dataset_id"]
        or report["species"] != species or type(report["temperature_k"]) not in (int, float)
        or report["temperature_k"] != temperature
        or report["reference_pressure_pa"] != fits["reference_pressure_pa"]
        or not isinstance(report["limitations"], list) or not report["limitations"]
        or any(not isinstance(s, str) or not s.strip() for s in report["limitations"])):
        raise ValueError("Inlet property query identity mismatch")
    expected = mixture({species: 1.0}, temperature, fits["reference_pressure_pa"], fits)
    for key in ("cp_j_per_kg_k", "h_j_per_kg", "s_j_per_kg_k"):
        target_key = "cp_frozen_j_per_kg_k" if key == "cp_j_per_kg_k" else key
        relation(report[key], expected[target_key], name + "." + key)
    mw = next(s["molar_mass_kg_per_kmol"] for s in fits["species"] if s["id"] == species)
    relation(report["molar_mass_kg_per_kmol"], mw, name + ".mass")
    return report["h_j_per_kg"]


def comparisons(folder):
    fixed = check_reference()
    refs = {case["id"]: case for case in fixed["cases"]}
    fuel_h = inlet_value(folder, "fuel", "CH4")
    oxidizer_h = inlet_value(folder, "oxidizer", "O2")
    result = {}
    for name, mode, area, ref_id, inputs in [
        ("temperature_hp", "hp", None, REFERENCES[0], None),
        ("temperature_A10", "frozen", 10, REFERENCES[1], None),
        ("temperature_A40", "frozen", 40, REFERENCES[1], None),
        ("enthalpy_hp", "hp-h", None, REFERENCES[0], supplied(fuel_h, oxidizer_h)),
        ("enthalpy_A10", "frozen-h", 10, REFERENCES[1], supplied(fuel_h, oxidizer_h, 10)),
        ("enthalpy_A40", "frozen-h", 40, REFERENCES[1], supplied(fuel_h, oxidizer_h, 40)),
        ("double_area", "frozen-h", 10, REFERENCES[1], supplied(fuel_h, oxidizer_h, 10, throat=0.02)),
        ("ambient_5000", "frozen-h", 10, REFERENCES[1], supplied(fuel_h, oxidizer_h, 10, ambient=5000)),
    ]:
        result[name] = compare_report(read_output(folder, name), refs[ref_id], mode, area, expected_inputs=inputs)
    hp = read_output(folder, "enthalpy_hp")
    for new, old in [("enthalpy_hp", "temperature_hp"), ("enthalpy_A10", "temperature_A10"),
                     ("enthalpy_A40", "temperature_A40")]:
        a, b = read_output(folder, new), read_output(folder, old)
        for key in ("chamber", "diagnostics"):
            if a[key] != b[key]:
                raise ValueError("Temperature/enthalpy entry equivalence failed: " + key)
        if "nozzle" in a and a["nozzle"] != b["nozzle"]:
            raise ValueError("Equivalent inlet nozzle differs")
        if a["chamber"] != hp["chamber"]:
            raise ValueError("Nozzle geometry changed HP chamber")
    base, doubled, ambient = [read_output(folder, n) for n in ("enthalpy_A10", "double_area", "ambient_5000")]
    for key in ("mass_flow_kg_per_s", "thrust_n", "exit_area_m2"):
        relation(doubled["geometry"][key], 2 * base["geometry"][key], "double." + key)
    relation(doubled["geometry"]["specific_impulse_s"], base["geometry"]["specific_impulse_s"], "double.Isp")
    relation(ambient["geometry"]["mass_flow_kg_per_s"], base["geometry"]["mass_flow_kg_per_s"], "ambient.flow")
    relation(base["geometry"]["thrust_n"] - ambient["geometry"]["thrust_n"],
             5000 * base["geometry"]["exit_area_m2"], "ambient.pressure-thrust")
    return result


def expected_files():
    files = {"build-manifest.json", "test-report.json", "cea-manifest.json"}
    files |= {n + suffix for n, *_ in recipes(0, 0) for suffix in ("-stdout.txt", "-stderr.txt")}
    files |= {n + suffix for n in REFERENCES for suffix in (".inp", ".out", ".log")}
    return files


def verify(folder):
    record = read_json(folder / "manifest.json")
    fixed = check_reference()
    if (not isinstance(record, dict) or set(record) != REQUIRED_KEYS
        or type(record["schema_version"]) is not int or record["schema_version"] != 1
        or record["kind"] != "adiabatic-inlet-validation" or record["status"] != "PASS"
        or record["scope"] != SCOPE or type(record["source_dirty"]) is not bool
        or not isinstance(record["source_head"], str) or not re.fullmatch("[0-9a-f]{40}", record["source_head"])):
        raise ValueError("Adiabatic manifest identity mismatch")
    try:
        start, finish = [datetime.fromisoformat(record[k]) for k in ("started_at", "finished_at")]
        if start.utcoffset() is None or finish.utcoffset() is None or finish < start:
            raise ValueError("Timestamp order/timezone")
    except (ValueError, TypeError) as exc:
        raise ValueError("Adiabatic timestamp mismatch") from exc
    files = expected_files()
    if ({p.name for p in folder.iterdir()} != files | {"manifest.json"}
        or any(not p.is_file() for p in folder.iterdir())
        or not isinstance(record["files"], list) or len(record["files"]) != len(files)):
        raise ValueError("Adiabatic archive inventory mismatch")
    entries = record["files"]
    if (any(not isinstance(f, dict) or set(f) != {"path", "sha256"}
            or not isinstance(f["path"], str) or not isinstance(f["sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", f["sha256"]) for f in entries)
        or {f["path"] for f in entries} != files):
        raise ValueError("Adiabatic file list mismatch")
    for entry in entries:
        if digest(folder / entry["path"]) != entry["sha256"]:
            raise ValueError("Adiabatic file bytes changed")
    if (record["cea_manifest_sha256"] != digest(ROOT / "tests/reference/cea/manifest.json")
        or digest(folder / "cea-manifest.json") != record["cea_manifest_sha256"]):
        raise ValueError("Pinned CEA manifest mismatch")
    for name in REFERENCES:
        ref = next(c for c in fixed["cases"] if c["id"] == name)
        for suffix, original in [(".inp", ROOT / ref["input"]), (".out", ROOT / ref["output"]),
                                 (".log", (ROOT / ref["output"]).with_suffix(".log"))]:
            if digest(folder / (name + suffix)) != digest(original):
                raise ValueError("Pinned raw CEA reference differs")
    build = read_json(folder / "build-manifest.json")
    tests = read_json(folder / "test-report.json")
    verify_test_report(tests, build, digest(folder / "build-manifest.json"))
    if (record["build_manifest_sha256"] != digest(folder / "build-manifest.json")
        or record["test_report_sha256"] != digest(folder / "test-report.json")
        or record["binary_sha256"] != build["application"]["sha256"]):
        raise ValueError("Adiabatic build/test/binary mismatch")
    fuel_h = inlet_value(folder, "fuel", "CH4")
    oxidizer_h = inlet_value(folder, "oxidizer", "O2")
    expected = recipes(fuel_h, oxidizer_h)
    runs = record["runs"]
    if not isinstance(runs, list) or len(runs) != len(expected):
        raise ValueError("Adiabatic run count mismatch")
    for run, (name, args, code) in zip(runs, expected):
        if (not isinstance(run, dict) or set(run) != {"id", "arguments", "exit_code"}
            or run["id"] != name or run["arguments"] != args
            or type(run["exit_code"]) is not int or run["exit_code"] != code):
            raise ValueError("Adiabatic run recipe/exit mismatch")
        stdout = (folder / (name + "-stdout.txt")).read_text(encoding="utf-8")
        stderr = (folder / (name + "-stderr.txt")).read_text(encoding="utf-8")
        if (code == 0 and stderr) or (code != 0 and (stdout or not stderr.strip())):
            raise ValueError("Adiabatic success/failure stream protocol mismatch")
        if code == 4 and not stderr.startswith("out_of_domain:"):
            raise ValueError("Expected explicit domain rejection")
        if code == 2 and not stderr.startswith("Usage"):
            raise ValueError("Expected explicit CLI syntax rejection")
    saved = record["comparisons"]
    checked = comparisons(folder)
    keys = {"field", "actual", "reference", "difference", "absolute_tolerance"}
    if (not isinstance(saved, dict) or set(saved) != set(checked)
        or any(not isinstance(rows, list) or any(
            not isinstance(c, dict) or set(c) != keys or not isinstance(c["field"], str)
            or any(type(c[k]) not in (int, float) or not math.isfinite(c[k]) for k in keys - {"field"})
            or c["absolute_tolerance"] <= 0 for c in rows) for rows in saved.values())
        or checked != saved):
        raise ValueError("Adiabatic saved comparisons changed")
    return len(runs)


def archive(destination):
    target = local_path(ROOT, destination)
    if target.exists():
        raise FileExistsError("Adiabatic archive destination already exists")
    build_path = verified_build(ROOT, "Release", require_tests=True)
    build = read_json(build_path)
    executable = local_path(ROOT, build["application"]["path"])
    fixed = check_reference()
    folder = ROOT / "build/adiabatic-inlet" / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    record = dict(schema_version=1, kind="adiabatic-inlet-validation", status="RUNNING",
                  scope=SCOPE, started_at=now(), source_head=git(ROOT, "rev-parse", "HEAD", check=True).stdout.strip(),
                  source_dirty=bool(git(ROOT, "status", "--porcelain", check=True).stdout.strip()),
                  binary_sha256=digest(executable), runs=[], comparisons={})
    atomic_json(folder / "manifest.json", record)
    try:
        shutil.copy2(build_path, folder / "build-manifest.json")
        shutil.copy2(build_path.parent / "test-report.json", folder / "test-report.json")
        shutil.copy2(ROOT / "tests/reference/cea/manifest.json", folder / "cea-manifest.json")
        for name in REFERENCES:
            ref = next(c for c in fixed["cases"] if c["id"] == name)
            for suffix, original in [(".inp", ROOT / ref["input"]), (".out", ROOT / ref["output"]),
                                     (".log", (ROOT / ref["output"]).with_suffix(".log"))]:
                shutil.copy2(original, folder / (name + suffix))
        def run(name, args, code):
            completed = run_logged([str(executable), *args], ROOT, folder / (name + "-stdout.txt"),
                                   folder / (name + "-stderr.txt"), 15)
            if completed.returncode != code:
                raise ValueError("Unexpected C exit: " + name)
            record["runs"].append(dict(id=name, arguments=args, exit_code=completed.returncode))
        for name, args, code in recipes(0, 0)[:2]:
            run(name, args, code)
        fuel_h = inlet_value(folder, "fuel", "CH4")
        oxidizer_h = inlet_value(folder, "oxidizer", "O2")
        for name, args, code in recipes(fuel_h, oxidizer_h)[2:]:
            run(name, args, code)
        if digest(executable) != record["binary_sha256"]:
            raise ValueError("C executable changed during run")
        record["comparisons"] = comparisons(folder)
        record.update(status="PASS", build_manifest_sha256=digest(folder / "build-manifest.json"),
                      test_report_sha256=digest(folder / "test-report.json"),
                      cea_manifest_sha256=digest(folder / "cea-manifest.json"))
        record["files"] = [{"path": p.name, "sha256": digest(p)}
                           for p in sorted(folder.iterdir()) if p.name != "manifest.json"]
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        raise
    finally:
        record["finished_at"] = now()
        atomic_json(folder / "manifest.json", record)
    try:
        verify(folder)
        staged = folder.with_name(folder.name + "-archive")
        shutil.copytree(folder, staged)
        verify(staged)
        target.parent.mkdir(parents=True, exist_ok=True)
        staged.rename(target)
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        atomic_json(folder / "manifest.json", record)
        raise
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["archive", "verify"])
    parser.add_argument("directory")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        print(archive(args.directory) if args.action == "archive"
              else f"Adiabatic inlet verified: {verify(local_path(ROOT, args.directory))} runs")
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
