"""Fixed liquid-reactant HP reference archive; all production solving is C17."""
from __future__ import annotations

import argparse
from datetime import datetime
import re
import shutil
import subprocess
import sys
import uuid

from adiabatic_inlet import read_output, relation
from adiabatic_study import typed_equal
from cea_reference import COMMIT, THERMO_SHA, check_reference, parse_output
from combustion_reference import ANCHOR_DATASET, compare_report, liquid_anchors
from pipeline import verified_build, verify_test_report
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json
from research_frozen_reference import SOURCE_HASHES
from research_tp_reference import run_logged

SCOPE = (
    "Pinned CH4(L)111.643 K/O2(L)90.170 K assigned chemical enthalpies, "
    "restricted nine ideal-gas products HP, Q=0 and chamber-frozen fixed-area nozzle. "
    "No liquid EOS, density, pressure correction, phase-stability, pump or flight/full-cycle validation."
)
CONDITIONS = (("base", 3.4), ("of_2_6", 2.6), ("of_4_2", 4.2))
DESIGN = dict(pressure_pa=1e7, throat_area_m2=0.01, area_ratios=[10, 40], ambient_pressure_pa=0.0)
CEA_SUFFIXES = (".inp", ".out", "-cea-stdout.txt", "-cea-stderr.txt")
TRACE = 1e-7  # At O/F=2.6, 1e-8 leaves an empty omission list with NUL bytes in CEA.
KEYS = {
    "schema_version", "kind", "status", "scope", "started_at", "finished_at", "source_head", "source_dirty",
    "design", "conditions", "anchors", "c_binary_sha256", "build_manifest_sha256", "test_report_sha256",
    "cea_commit", "cea_version", "cea_binary_sha256", "thermo_source_sha256", "compiled_database_hashes",
    "rocket_source_hashes", "runs", "cea_runs", "comparisons", "responses", "files",
}


def inputs(of=3.4, area=None, ambient=0.0, throat=0.01):
    data = dict(feed_phase="liquid", anchor_dataset_id=ANCHOR_DATASET,
                fuel_anchor_id="CH4(L)", oxidizer_anchor_id="O2(L)", pressure_pa=1e7,
                oxidizer_fuel_mass_ratio=of, fuel_temperature_k=111.643, oxidizer_temperature_k=90.170)
    if area is not None:
        data.update(area_ratio=area, ambient_pressure_pa=ambient, throat_area_m2=throat)
    return data


def arguments(data, mode):
    keys = ["pressure_pa", "oxidizer_fuel_mass_ratio", "fuel_temperature_k", "oxidizer_temperature_k"]
    if mode == "frozen-liquid":
        keys += ["area_ratio", "ambient_pressure_pa", "throat_area_m2"]
    return ["combustion", mode, data["anchor_dataset_id"], data["feed_phase"],
            data["fuel_anchor_id"], data["oxidizer_anchor_id"], *[format(data[k], ".17g") for k in keys]]


def recipes():
    result = []
    for name, of in CONDITIONS:
        result.append((name + "_hp", arguments(inputs(of), "hp-liquid"), 0))
        result.extend((name + "_A" + str(area), arguments(inputs(of, area), "frozen-liquid"), 0)
                      for area in DESIGN["area_ratios"])
    result += [
        ("double_area", arguments(inputs(area=10, throat=0.02), "frozen-liquid"), 0),
        ("ambient_5000", arguments(inputs(area=10, ambient=5000), "frozen-liquid"), 0),
        ("old_gas", ["combustion", "hp", "10000000", "3.4", "298.15", "298.15"], 0),
    ]
    for name, change in (
        ("reject_dataset", dict(anchor_dataset_id="arbitrary-zero")),
        ("reject_phase", dict(feed_phase="gas")),
        ("reject_fuel", dict(fuel_anchor_id="RP-1")),
        ("reject_temperature", dict(fuel_temperature_k=111.644)),
        ("reject_pressure", dict(pressure_pa=99)),
        ("reject_of", dict(oxidizer_fuel_mass_ratio=20.01)),
    ):
        result.append((name, arguments(dict(inputs(), **change), "hp-liquid"), 4))
    result += [
        ("reject_backpressure", arguments(inputs(area=40, ambient=100000), "frozen-liquid"), 4),
        ("reject_nan", arguments(inputs(), "hp-liquid")[:-2] + ["nan", "90.170"], 2),
        ("reject_h_override", arguments(inputs(), "hp-liquid") + ["-89233"], 2),
    ]
    return result


def cea_recipes():
    return [(name + "_" + mode, of, mode) for name, of in CONDITIONS for mode in ("hp", "rocket")]


def case_card(name, of, mode):
    problem = "hp" if mode == "hp" else "rocket frozen nfz=1"
    areas = "" if mode == "hp" else " supar=10,40"
    return (
        "! Fixed liquid assigned enthalpies; no density or pressure correction.\n"
        f"problem case={name} {problem} p,bar=100 o/f={of:.17g}{areas}\n"
        "reactants\n fuel=CH4(L) wt%=100 t,k=111.643\n oxid=O2(L) wt%=100 t,k=90.170\n"
        "only H2 O2 H2O CO CO2 CH4 H O OH\noutput siunits trace=1.e-7\nend\n"
    )


def evaluate(folder):
    comparisons, responses = {}, []
    for name, of in CONDITIONS:
        hp_ref = dict(summary=parse_output((folder / (name + "_hp.out")).read_bytes(), trace_threshold=TRACE))
        rocket_ref = dict(summary=parse_output((folder / (name + "_rocket.out")).read_bytes(), True, True, TRACE))
        hp = read_output(folder, name + "_hp")
        comparisons[name + "_hp"] = compare_report(hp, hp_ref, "hp-liquid", expected_inputs=inputs(of))
        comparisons[name + "_hp_rocket"] = compare_report(hp, rocket_ref, "hp-liquid", expected_inputs=inputs(of))
        points = [(name + "_A" + str(area), area, 0.0, 0.01) for area in (10, 40)]
        if name == "base":
            points += [("double_area", 10, 0.0, 0.02), ("ambient_5000", 10, 5000.0, 0.01)]
        for point, area, ambient, throat in points:
            report = read_output(folder, point)
            comparisons[point] = compare_report(
                report, rocket_ref, "frozen-liquid", area,
                expected_inputs=inputs(of, area, ambient, throat))
            if report["chamber"] != hp["chamber"] or report["diagnostics"] != hp["diagnostics"]:
                raise ValueError("Nozzle changed anchor HP chamber")
            responses.append(dict(id=point, **report["geometry"],
                                  area_ratio=area, ambient_pressure_pa=ambient, oxidizer_fuel_mass_ratio=of,
                                  chamber_temperature_k=hp["chamber"]["temperature_k"],
                                  cstar_m_per_s=report["nozzle"]["cstar_m_per_s"]))
    old_ref = next(case for case in check_reference()["cases"] if case["id"] == "ch4_o2_hp")
    comparisons["old_gas"] = compare_report(read_output(folder, "old_gas"), old_ref, "hp")
    if read_output(folder, "base_hp")["chamber"]["temperature_k"] >= read_output(folder, "old_gas")["chamber"]["temperature_k"]:
        raise ValueError("Fixed liquid vs 298 K gas inlet trend mismatch")
    base, doubled, ambient = [read_output(folder, name) for name in ("base_A10", "double_area", "ambient_5000")]
    for key in ("mass_flow_kg_per_s", "thrust_n", "exit_area_m2"):
        relation(doubled["geometry"][key], 2*base["geometry"][key], "anchor double "+key)
    relation(doubled["geometry"]["specific_impulse_s"], base["geometry"]["specific_impulse_s"], "anchor double Isp")
    relation(ambient["geometry"]["mass_flow_kg_per_s"], base["geometry"]["mass_flow_kg_per_s"], "anchor ambient flow")
    relation(base["geometry"]["thrust_n"]-ambient["geometry"]["thrust_n"], 5000*base["geometry"]["exit_area_m2"], "anchor ambient thrust")
    return comparisons, responses


def required_files():
    files = {"build-manifest.json", "test-report.json", "cea-manifest.json"} | set(SOURCE_HASHES)
    files |= {name + suffix for name, *_ in recipes() for suffix in ("-stdout.txt", "-stderr.txt")}
    files |= {name + suffix for name, *_ in cea_recipes() for suffix in CEA_SUFFIXES}
    return files


def verify(folder):
    record = read_json(folder / "manifest.json")
    fixed = check_reference()
    if (not isinstance(record, dict) or set(record) != KEYS
        or type(record["schema_version"]) is not int or record["schema_version"] != 1
        or record["kind"] != "liquid-anchor-validation" or record["status"] != "PASS"
        or record["scope"] != SCOPE or type(record["source_dirty"]) is not bool
        or not isinstance(record["source_head"], str) or not re.fullmatch("[0-9a-f]{40}", record["source_head"])):
        raise ValueError("Liquid anchor archive identity mismatch")
    if any(not isinstance(record[k], str) for k in ("started_at", "finished_at")):
        raise ValueError("Liquid anchor timestamp type mismatch")
    start, finish = [datetime.fromisoformat(record[k]) for k in ("started_at", "finished_at")]
    if start.utcoffset() is None or finish.utcoffset() is None or finish < start:
        raise ValueError("Liquid anchor timestamp order/timezone mismatch")
    expected_identity = dict(
        design=DESIGN, conditions=[dict(id=n, oxidizer_fuel_mass_ratio=of) for n, of in CONDITIONS],
        anchors=liquid_anchors(), cea_commit=COMMIT, cea_version="3.3.4",
        cea_binary_sha256=fixed["executable_sha256"], thermo_source_sha256=THERMO_SHA,
        compiled_database_hashes=fixed["compiled_database_hashes"], rocket_source_hashes=SOURCE_HASHES,
    )
    for key, value in expected_identity.items():
        typed_equal(record[key], value, "anchor "+key)
    required = required_files()
    if ({p.name for p in folder.iterdir()} != required | {"manifest.json"}
        or any(not p.is_file() for p in folder.iterdir())
        or not isinstance(record["files"], list) or len(record["files"]) != len(required)):
        raise ValueError("Liquid anchor archive inventory mismatch")
    entries = record["files"]
    if (any(not isinstance(f, dict) or set(f) != {"path", "sha256"}
            or not isinstance(f["path"], str) or not isinstance(f["sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", f["sha256"]) for f in entries)
        or {f["path"] for f in entries} != required):
        raise ValueError("Liquid anchor file declaration mismatch")
    for item in entries:
        if digest(folder / item["path"]) != item["sha256"]:
            raise ValueError("Liquid anchor archive bytes changed")
    for name, identity in SOURCE_HASHES.items():
        if digest(folder / name) != identity:
            raise ValueError("Pinned rocket source changed")
    if digest(folder / "cea-manifest.json") != digest(ROOT / "tests/reference/cea/manifest.json"):
        raise ValueError("Pinned CEA identity snapshot differs")
    build = read_json(folder / "build-manifest.json")
    tests = read_json(folder / "test-report.json")
    verify_test_report(tests, build, digest(folder / "build-manifest.json"))
    for key, identity in dict(c_binary_sha256=build["application"]["sha256"],
                              build_manifest_sha256=digest(folder / "build-manifest.json"),
                              test_report_sha256=digest(folder / "test-report.json")).items():
        if record[key] != identity:
            raise ValueError("Liquid anchor C build/test mismatch")
    if not isinstance(record["runs"], list) or len(record["runs"]) != len(recipes()):
        raise ValueError("Liquid anchor C run count mismatch")
    for run, (name, args, code) in zip(record["runs"], recipes()):
        if (not isinstance(run, dict) or set(run) != {"id", "arguments", "exit_code"}
            or type(run["exit_code"]) is not int):
            raise ValueError("Liquid anchor C run schema/exit type mismatch")
        typed_equal(run, dict(id=name, arguments=args, exit_code=code), "anchor C recipe")
        stdout = (folder / (name + "-stdout.txt")).read_text(encoding="utf-8")
        stderr = (folder / (name + "-stderr.txt")).read_text(encoding="utf-8")
        if (code == 0 and stderr) or (code != 0 and
            (stdout or not stderr.startswith("Usage" if code == 2 else "out_of_domain:"))):
            raise ValueError("Liquid anchor stream protocol mismatch")
    if not isinstance(record["cea_runs"], list) or len(record["cea_runs"]) != len(cea_recipes()):
        raise ValueError("Liquid anchor CEA run count mismatch")
    for run, (name, of, mode) in zip(record["cea_runs"], cea_recipes()):
        if (not isinstance(run, dict) or set(run) != {"id", "arguments", "exit_code"}
            or type(run["exit_code"]) is not int):
            raise ValueError("Liquid anchor CEA run schema/exit type mismatch")
        typed_equal(run, dict(id=name, arguments=["-v", name], exit_code=0), "anchor CEA recipe")
        if (folder / (name + ".inp")).read_text(encoding="utf-8") != case_card(name, of, mode):
            raise ValueError("Liquid anchor CEA input card mismatch")
        log = (folder / (name + "-cea-stdout.txt")).read_text(encoding="utf-8")
        if ("CEA Version: 3.3.4" not in log or "WARNING" in log or "ERROR" in log
            or (folder / (name + "-cea-stderr.txt")).read_bytes()):
            raise ValueError("Liquid anchor CEA version/diagnostics mismatch")
    comparisons, responses = evaluate(folder)
    typed_equal(record["comparisons"], comparisons, "anchor comparisons")
    typed_equal(record["responses"], responses, "anchor responses")
    return len(record["runs"]), len(record["cea_runs"])


def archive(destination):
    target = local_path(ROOT, destination)
    if target.exists():
        raise FileExistsError("Liquid anchor destination already exists")
    folder = ROOT / "build/liquid-anchor" / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    record = dict(schema_version=1, kind="liquid-anchor-validation", status="RUNNING",
                  scope=SCOPE, started_at=now(), runs=[], cea_runs=[])
    atomic_json(folder / "manifest.json", record)
    try:
        build_path = verified_build(ROOT, "Release", require_tests=True)
        build = read_json(build_path)
        executable = local_path(ROOT, build["application"]["path"])
        fixed = check_reference()
        source = ROOT / "build/reference/cea-v3.3.4"
        cea = ROOT / "build/reference/cea-build-v3.3.4/source/cea.exe"
        if (git(source, "rev-parse", "HEAD", check=True).stdout.strip() != COMMIT
            or git(source, "status", "--porcelain", "--untracked-files=no", check=True).stdout.strip()
            or digest(source / "data/thermo.inp") != THERMO_SHA
            or digest(cea) != fixed["executable_sha256"]
            or any(digest(source / "source" / n) != identity for n, identity in SOURCE_HASHES.items())):
            raise ValueError("Pinned CEA source/database/binary changed")
        record.update(
            source_head=git(ROOT, "rev-parse", "HEAD", check=True).stdout.strip(),
            source_dirty=bool(git(ROOT, "status", "--porcelain", check=True).stdout.strip()),
            design=DESIGN, conditions=[dict(id=n, oxidizer_fuel_mass_ratio=of) for n, of in CONDITIONS],
            anchors=liquid_anchors(), c_binary_sha256=digest(executable), cea_commit=COMMIT,
            cea_version="3.3.4", cea_binary_sha256=digest(cea), thermo_source_sha256=THERMO_SHA,
            compiled_database_hashes=fixed["compiled_database_hashes"], rocket_source_hashes=SOURCE_HASHES,
        )
        shutil.copy2(build_path, folder / "build-manifest.json")
        shutil.copy2(build_path.parent / "test-report.json", folder / "test-report.json")
        shutil.copy2(ROOT / "tests/reference/cea/manifest.json", folder / "cea-manifest.json")
        for name in SOURCE_HASHES:
            shutil.copy2(source / "source" / name, folder / name)
        for name in ("thermo.lib", "trans.lib"):
            original = ROOT / "build/reference/cea-build-v3.3.4" / name
            if digest(original) != fixed["compiled_database_hashes"][name]:
                raise ValueError("Compiled CEA database changed")
            shutil.copy2(original, folder / name)
        for name, args, code in recipes():
            run = run_logged([str(executable), *args], ROOT, folder / (name + "-stdout.txt"),
                             folder / (name + "-stderr.txt"), 15)
            if run.returncode != code:
                raise ValueError("Unexpected liquid anchor C exit: " + name)
            record["runs"].append(dict(id=name, arguments=args, exit_code=run.returncode))
        for name, of, mode in cea_recipes():
            atomic_text(folder / (name + ".inp"), case_card(name, of, mode))
            run = run_logged([str(cea), "-v", name], folder,
                             folder / (name + "-cea-stdout.txt"), folder / (name + "-cea-stderr.txt"), 30)
            if run.returncode:
                raise ValueError("Unexpected liquid anchor CEA exit: " + name)
            record["cea_runs"].append(dict(id=name, arguments=["-v", name], exit_code=run.returncode))
        verified_build(ROOT, "Release", require_tests=True)
        if digest(executable) != record["c_binary_sha256"] or digest(cea) != record["cea_binary_sha256"]:
            raise ValueError("Liquid anchor executable changed during run")
        record["comparisons"], record["responses"] = evaluate(folder)
        record.update(status="PASS", build_manifest_sha256=digest(folder / "build-manifest.json"),
                      test_report_sha256=digest(folder / "test-report.json"))
        record["files"] = [{"path": n, "sha256": digest(folder / n)} for n in sorted(required_files())]
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        raise
    finally:
        record["finished_at"] = now()
        atomic_json(folder / "manifest.json", record)
    try:
        staged = folder.with_name(folder.name + "-archive")
        staged.mkdir()
        for name in required_files() | {"manifest.json"}:
            shutil.copy2(folder / name, staged / name)
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
              else f"Liquid anchors verified: {verify(local_path(ROOT, args.directory))} C/CEA runs")
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
