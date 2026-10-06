"""Archive public C RP-1 CLI cases and fixed CEA references; no Python solving."""
from __future__ import annotations

import argparse
from datetime import datetime
import re
import shutil
import subprocess
import sys
import uuid

from adiabatic_study import typed_equal
from cea_reference import parse_output
from combustion_reference import KEROSENE_DATASET, compare_report
from kerosene_reference import BINARY, DATABASE, card, identity, parse
from pipeline import verified_build, verify_test_report
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json, strict_json
from research_tp_reference import run_logged

RATIOS = (2.2, 2.4, 2.6, 2.9, 3.2, 3.6, 4.0)
SCOPE = "Pinned RP-1/O2(L), 10 MPa, O/F=2.2..4.0, nine neutral gases and chamber-frozen nozzle. No batch/EOS/pump/cycle/carbon prediction."


def inputs(ratio=2.6, area=None):
    result = dict(feed_phase="liquid", anchor_dataset_id=KEROSENE_DATASET, fuel_anchor_id="RP-1",
                  oxidizer_anchor_id="O2(L)", pressure_pa=1e7, oxidizer_fuel_mass_ratio=ratio,
                  fuel_temperature_k=298.15, oxidizer_temperature_k=90.170)
    if area is not None:
        result.update(area_ratio=area, ambient_pressure_pa=0.0, throat_area_m2=0.01)
    return result


def arguments(data, mode):
    keys = ["pressure_pa", "oxidizer_fuel_mass_ratio", "fuel_temperature_k", "oxidizer_temperature_k"]
    if mode == "frozen-rp1":
        keys += ["area_ratio", "ambient_pressure_pa", "throat_area_m2"]
    return ["combustion", mode, data["anchor_dataset_id"], data["feed_phase"], data["fuel_anchor_id"],
            data["oxidizer_anchor_id"], *[format(data[key], ".17g") for key in keys]]


def recipes():
    result = []
    for ratio in RATIOS:
        prefix = "of_" + str(ratio).replace(".", "_")
        result.append((prefix + "_hp", arguments(inputs(ratio), "hp-rp1"), 0))
        for area in (10, 40):
            result.append((prefix + "_A" + str(area), arguments(inputs(ratio, area), "frozen-rp1"), 0))
    for name, change in (
        ("dataset", dict(anchor_dataset_id="other")), ("phase", dict(feed_phase="gas")),
        ("fuel", dict(fuel_anchor_id="CH4(L)")), ("oxidizer", dict(oxidizer_anchor_id="O2")),
        ("fuel_temperature", dict(fuel_temperature_k=350)),
        ("oxidizer_temperature", dict(oxidizer_temperature_k=90.171)),
        ("pressure", dict(pressure_pa=1e7+1)), ("ratio_low", dict(oxidizer_fuel_mass_ratio=2.199)),
        ("ratio_high", dict(oxidizer_fuel_mass_ratio=4.001)),
    ):
        result.append(("reject_" + name, arguments(dict(inputs(), **change), "hp-rp1"), 4))
    result += [
        ("reject_nan", arguments(dict(inputs(), fuel_temperature_k=float("nan")), "hp-rp1"), 2),
        ("reject_override", arguments(inputs(), "hp-rp1") + ["-24717.7"], 2),
        ("reject_backpressure", arguments(dict(inputs(area=40), ambient_pressure_pa=1e5), "frozen-rp1"), 4),
    ]
    return result


def cea_recipes():
    result = []
    for ratio in RATIOS:
        prefix = "of_" + str(ratio).replace(".", "_")
        for suffix, mode, products in (("hp", "hp", "nine-gas"),
                                       ("rocket", "rocket frozen nfz=1", "nine-gas"),
                                       ("expanded", "hp", "expanded")):
            result.append(dict(id=prefix + "_" + suffix, ratio=ratio, mode=mode,
                               products=products, fuel_temperature=298.15))
    return result


def evaluate(folder):
    comparisons, deltas = {}, []
    for ratio in RATIOS:
        prefix = "of_" + str(ratio).replace(".", "_")
        hp_ref = dict(summary=parse_output((folder / (prefix + "_hp.out")).read_bytes(), trace_threshold=1e-7))
        nozzle_ref = dict(summary=parse_output((folder / (prefix + "_rocket.out")).read_bytes(), True, True, 1e-7))
        hp = read_json(folder / (prefix + "_hp-c-stdout.json"))
        comparisons[prefix + "_hp"] = compare_report(hp, hp_ref, "hp-rp1", expected_inputs=inputs(ratio))
        for area in (10, 40):
            report = read_json(folder / (prefix + "_A" + str(area) + "-c-stdout.json"))
            comparisons[prefix + "_A" + str(area)] = compare_report(
                report, nozzle_ref, "frozen-rp1", area, expected_inputs=inputs(ratio, area))
            typed_equal(report["chamber"], hp["chamber"], "unchanged RP-1 chamber")
        expanded = parse((folder / (prefix + "_expanded.out")).read_bytes())
        if expanded["status"] != "COMPLETE" or "C(gr)" in expanded["mole_fractions"]:
            raise ValueError("Expanded RP-1 reference incomplete or printed condensed carbon")
        delta = hp_ref["summary"]["rows"]["temperature_k"][0] - expanded["rows"]["temperature_k"][0]
        if abs(delta) > 1:
            raise ValueError("RP-1 product-set temperature discrepancy exceeds study criterion")
        deltas.append(dict(ratio=ratio, temperature_delta_k=delta))
    return comparisons, deltas


def required_files():
    names = {"build-manifest.json", "test-report.json"}
    names |= {name + suffix for name, *_ in recipes() for suffix in ("-c-stdout.json", "-c-stderr.txt")}
    names |= {case["id"] + suffix for case in cea_recipes()
              for suffix in (".inp", ".out", "-cea-stdout.txt", "-cea-stderr.txt")}
    return names


def verify(folder):
    record = read_json(folder / "manifest.json")
    if (not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != 1
        or record.get("kind") != "kerosene-anchor-validation" or record.get("status") != "PASS" or record.get("scope") != SCOPE):
        raise ValueError("RP-1 validation identity differs")
    if (type(record.get('source_dirty')) is not bool
        or not isinstance(record.get('source_head'), str) or not re.fullmatch('[a-f0-9]{40}', record['source_head'])
        or any(not isinstance(record.get(key), str) for key in ('started_at', 'finished_at'))):
        raise ValueError('RP-1 archive source/time identity differs')
    start, finish = (datetime.fromisoformat(record[key]) for key in ('started_at', 'finished_at'))
    if start.utcoffset() is None or finish.utcoffset() is None or finish < start:
        raise ValueError('RP-1 archive timestamps differ')
    typed_equal(record["cea_identity"], identity(), "RP-1 CEA identity")
    typed_equal(record["recipes"], [dict(id=n, arguments=a, exit_code=c) for n, a, c in recipes()], "RP-1 C runs")
    required = required_files()
    if (any(not p.is_file() for p in folder.iterdir())
        or {p.name for p in folder.iterdir()} != required | {"manifest.json"}
        or not isinstance(record.get('files'), dict) or set(record["files"]) != required):
        raise ValueError("RP-1 archive file inventory differs")
    if any(not isinstance(sha, str) or not re.fullmatch('[a-f0-9]{64}', sha)
           or digest(folder / name) != sha for name, sha in record["files"].items()):
        raise ValueError("RP-1 archive bytes changed")
    build = read_json(folder / "build-manifest.json")
    tests = read_json(folder / "test-report.json")
    verify_test_report(tests, build, digest(folder / "build-manifest.json"))
    if build["application"]["sha256"] != record["c_binary_sha256"]:
        raise ValueError("RP-1 tested binary identity differs")
    for name, _, code in recipes():
        stdout = (folder / (name + "-c-stdout.json")).read_text(encoding="utf-8")
        stderr = (folder / (name + "-c-stderr.txt")).read_text(encoding="utf-8")
        if code == 0:
            if stderr:
                raise ValueError("Successful RP-1 C run has diagnostics")
            strict_json(stdout)
        elif stdout or not stderr.startswith("Usage" if code == 2 else "out_of_domain:"):
            raise ValueError("RP-1 rejection stream protocol differs")
    for case in cea_recipes():
        name = case["id"]
        if (folder / (name + ".inp")).read_text(encoding="utf-8") != card(case):
            raise ValueError("RP-1 CEA card changed")
        log = (folder / (name + "-cea-stdout.txt")).read_text(encoding="utf-8")
        if ("CEA Version: 3.3.4" not in log or any(word in log for word in ("WARNING", "ERROR"))
            or (folder / (name + "-cea-stderr.txt")).read_bytes()):
            raise ValueError("RP-1 CEA diagnostics or version differs")
    comparisons, deltas = evaluate(folder)
    typed_equal(record["comparisons"], comparisons, "RP-1 comparison")
    typed_equal(record["product_set_deltas"], deltas, "RP-1 product-set study")
    return len(recipes()), len(cea_recipes())


def archive(target):
    if target.exists():
        raise FileExistsError("Use a new RP-1 validation destination")
    work = ROOT / "build/kerosene-validation" / uuid.uuid4().hex
    work.mkdir(parents=True)
    record = dict(schema_version=1, kind="kerosene-anchor-validation", scope=SCOPE, status="RUNNING", started_at=now())
    atomic_json(work / "manifest.json", record)
    try:
        fixed = identity(check_runtime=True)
        build_path = verified_build(ROOT, "Release", require_tests=True)
        build = read_json(build_path)
        executable = local_path(ROOT, build["application"]["path"])
        record.update(cea_identity=fixed, c_binary_sha256=digest(executable),
                      source_head=git(ROOT, "rev-parse", "HEAD", check=True).stdout.strip(),
                      source_dirty=bool(git(ROOT, "status", "--porcelain", check=True).stdout.strip()),
                      recipes=[dict(id=n, arguments=a, exit_code=c) for n, a, c in recipes()])
        shutil.copy2(build_path, work / "build-manifest.json")
        shutil.copy2(build_path.parent / "test-report.json", work / "test-report.json")
        for name in fixed["databases"]:
            shutil.copy2(DATABASE / name, work / name)
        for name, args, code in recipes():
            run = run_logged([str(executable), *args], ROOT, work / (name + "-c-stdout.json"),
                             work / (name + "-c-stderr.txt"), 15)
            if run.returncode != code:
                raise ValueError("RP-1 C exit differs: " + name)
        for case in cea_recipes():
            name = case["id"]
            atomic_text(work / (name + ".inp"), card(case))
            run = run_logged([str(BINARY), "-v", name], work, work / (name + "-cea-stdout.txt"),
                             work / (name + "-cea-stderr.txt"), 30)
            if run.returncode:
                raise ValueError("RP-1 CEA process failed: " + name)
        record["comparisons"], record["product_set_deltas"] = evaluate(work)
        if digest(executable) != record["c_binary_sha256"] or identity(check_runtime=True) != fixed:
            raise ValueError("RP-1 binary/reference changed during run")
        record["files"] = {name: digest(work / name) for name in sorted(required_files())}
        record["status"] = "PASS"
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        raise
    finally:
        record["finished_at"] = now()
        atomic_json(work / "manifest.json", record)
    saved = work / "archive"
    saved.mkdir()
    for name in required_files() | {"manifest.json"}:
        shutil.copy2(work / name, saved / name)
    try:
        verify(saved)
    except Exception as exc:
        record.update(status='FAIL', error=str(exc))
        atomic_json(work / 'manifest.json', record)
        raise
    target.parent.mkdir(parents=True, exist_ok=True)
    saved.rename(target)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("archive", "verify"))
    parser.add_argument("directory")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        print((archive if args.action == "archive" else verify)(local_path(ROOT, args.directory)))
    except (ValueError, OSError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
