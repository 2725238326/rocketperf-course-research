"""Pinned CEA assigned-TP frozen nozzle and C fixed-area research evidence."""

from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import sys
import uuid

from cea_reference import COMMIT, THERMO_SHA, check_reference, parse_output
from combustion_reference import compare_report
from pipeline import verified_build, verify_test_report
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json
from research_tp_reference import STUDY, conditions, run_logged

RECIPES = [
    ("main_base", "main_area_ratio", None),
    ("main_t_minus", "chamber_temperature_k", 0),
    ("main_t_plus", "chamber_temperature_k", 2),
    ("main_of_minus", "overall_oxidizer_fuel_ratio", 0),
    ("main_of_plus", "overall_oxidizer_fuel_ratio", 2),
]
SCOPE = "Five assigned-TP chamber-frozen nozzle references; eleven C fixed-area points. Single-nozzle synthetic states, not hardware/full-cycle or flight validation."
SOURCE_HASHES = {
    "main.f90": "d8a1707fc91170112802b2b61c07cce06a3063bbcf59dac77195ed84a78c549b",
    "rocket.f90": "5ae8bdebb5b08b13f2c0166916c4f4bf392ca55aceb9479253def5c8f2c657ca",
}
SUFFIXES = (".inp", ".out", "-cea-stdout.txt", "-cea-stderr.txt")


def points(name):
    return [(10, 0.0), (40, 0.0)] + ([(10, 5000.0)] if name == "main_base" else [])


def point_id(name, area, ambient):
    return name + "_A" + str(area) + ("_pa5000" if ambient else "")


def case_card(name, inputs):
    return (
        "! Assigned TP, infinite-area chamber; nfz=1 freezes at chamber, not throat.\n"
        f'problem case={name} rocket frozen nfz=1 p,bar={inputs["pressure_pa"]/1e5:.17g} '
        f't,k={inputs["temperature_k"]:.17g} o/f={inputs["oxidizer_fuel_mass_ratio"]:.17g} supar=10,40\n'
        "reactants\n fuel=CH4 wt%=100 t,k=298.15\n oxid=O2 wt%=100 t,k=298.15\n"
        "only H2 O2 H2O CO CO2 CH4 H O OH\noutput siunits trace=1.e-8\nend\n"
    )


def fixed_inputs(inputs, area, ambient, root=ROOT):
    base = read_json(local_path(root, STUDY + "/main_area_ratio/result.json"))["baseline"]
    return dict(
        inputs,
        area_ratio=area,
        ambient_pressure_pa=ambient,
        throat_area_m2=base["performance"]["main_throat_area_m2"],
    )


def arguments(inputs):
    return [
        "combustion",
        "frozen-tp",
        *[
            format(inputs[k], ".17g")
            for k in (
                "temperature_k",
                "pressure_pa",
                "oxidizer_fuel_mass_ratio",
                "fuel_temperature_k",
                "oxidizer_temperature_k",
                "area_ratio",
                "ambient_pressure_pa",
                "throat_area_m2",
            )
        ],
    ]


def input_matches(actual, expected):
    return (
        isinstance(actual, dict)
        and set(actual) == set(expected)
        and all(
            type(v) in (int, float) and math.isfinite(v)
            for k, v in actual.items()
            if k != "feed_phase"
        )
        and actual == expected
    )


def checked_point(folder, name, inputs, state):
    report = read_json(
        folder / (point_id(name, inputs["area_ratio"], inputs["ambient_pressure_pa"]) + "-c.json")
    )
    summary = parse_output((folder / (name + ".out")).read_bytes(), rocket=True, frozen=True)
    comparisons = compare_report(
        report, {"summary": summary}, "frozen-tp", inputs["area_ratio"], expected_inputs=inputs
    )
    for key in (
        "temperature_k",
        "pressure_pa",
        "h_j_per_kg",
        "s_j_per_kg_k",
        "cp_frozen_j_per_kg_k",
    ):
        if not math.isclose(report["chamber"][key], state[key], rel_tol=1e-10, abs_tol=1e-7):
            raise ValueError("Saved cycle and TP nozzle state differ: " + key)
    if report["chamber"]["mole_fractions"] != state["mole_fractions"]:
        raise ValueError("Saved cycle and TP nozzle composition differ")
    return comparisons


def inventory(folder):
    required = {"build-manifest.json", "test-report.json", "main.f90", "rocket.f90"}
    required |= {name + suffix for name, *_ in RECIPES for suffix in SUFFIXES}
    required |= {
        point_id(name, area, pa) + suffix
        for name, *_ in RECIPES
        for area, pa in points(name)
        for suffix in ("-c.json", "-c-stderr.txt")
    }
    actual = {p.name for p in folder.iterdir() if p.name != "manifest.json"}
    if actual != required or any(not p.is_file() for p in folder.iterdir()):
        raise ValueError("Frozen reference inventory mismatch")
    return required


def archive(destination, root=ROOT):
    target = local_path(root, destination)
    if target.exists():
        raise FileExistsError("Reference destination already exists")
    build_path = verified_build(root, "Release", require_tests=True)
    build = read_json(build_path)
    executable = local_path(root, build["application"]["path"])
    source = root / "build/reference/cea-v3.3.4"
    cea = root / "build/reference/cea-build-v3.3.4/source/cea.exe"
    fixed = check_reference()
    if (
        git(source, "rev-parse", "HEAD", check=True).stdout.strip() != COMMIT
        or git(source, "status", "--porcelain", "--untracked-files=no", check=True).stdout.strip()
        or digest(source / "data/thermo.inp") != THERMO_SHA
        or digest(cea) != fixed["executable_sha256"]
        or any(
            digest(source / "source" / name) != identity for name, identity in SOURCE_HASHES.items()
        )
    ):
        raise ValueError("CEA source, binary or assigned-temperature implementation changed")
    folder = root / "build/research-frozen-reference" / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    record = {
        "schema_version": 1,
        "kind": "research-frozen-reference",
        "status": "RUNNING",
        "started_at": now(),
        "source_head": git(root, "rev-parse", "HEAD", check=True).stdout.strip(),
        "source_dirty": bool(git(root, "status", "--porcelain", check=True).stdout.strip()),
        "cea_commit": COMMIT,
        "cea_version": "3.3.4",
        "cea_binary_sha256": digest(cea),
        "thermo_source_sha256": THERMO_SHA,
        "c_binary_sha256": digest(executable),
        "compiled_database_hashes": fixed["compiled_database_hashes"],
        "assigned_tp_source_hashes": SOURCE_HASHES,
        "scope": SCOPE,
        "cases": [],
    }
    atomic_json(folder / "manifest.json", record)
    try:
        for name in ("thermo.lib", "trans.lib"):
            original = root / "build/reference/cea-build-v3.3.4" / name
            if digest(original) != fixed["compiled_database_hashes"][name]:
                raise ValueError("CEA compiled database changed")
            shutil.copy2(original, folder / name)
        for name in SOURCE_HASHES:
            shutil.copy2(source / "source" / name, folder / name)
        shutil.copy2(build_path, folder / "build-manifest.json")
        shutil.copy2(build_path.parent / "test-report.json", folder / "test-report.json")
        for name, directory, index in RECIPES:
            inputs, state, path = conditions(directory, index, "main_nozzle", root)
            atomic_text(folder / (name + ".inp"), case_card(name, inputs))
            run = run_logged(
                [str(cea), "-v", name],
                folder,
                folder / (name + "-cea-stdout.txt"),
                folder / (name + "-cea-stderr.txt"),
                30,
            )
            if (
                run.returncode
                or run.stderr
                or "CEA Version: 3.3.4" not in run.stdout
                or "WARNING" in run.stdout
                or "ERROR" in run.stdout
            ):
                raise ValueError("CEA failed: " + name)
            case = {
                "id": name,
                "source_directory": directory,
                "point_index": index,
                "source_result_sha256": digest(path),
                "inputs": inputs,
                "cea_exit_code": run.returncode,
                "points": [],
            }
            for area, ambient in points(name):
                supplied = fixed_inputs(inputs, area, ambient, root)
                identity = point_id(name, area, ambient)
                command = [str(executable), *arguments(supplied)]
                run = run_logged(
                    command,
                    root,
                    folder / (identity + "-c.json"),
                    folder / (identity + "-c-stderr.txt"),
                    15,
                )
                if run.returncode or run.stderr:
                    raise ValueError("C failed: " + identity)
                case["points"].append(
                    {
                        "id": identity,
                        "inputs": supplied,
                        "c_command": command,
                        "c_exit_code": run.returncode,
                        "comparisons": checked_point(folder, name, supplied, state),
                    }
                )
            record["cases"].append(case)
        record.update(
            status="PASS",
            build_manifest_sha256=digest(folder / "build-manifest.json"),
            test_report_sha256=digest(folder / "test-report.json"),
        )
        record["files"] = [
            {"path": p.name, "sha256": digest(p)}
            for p in sorted(folder.iterdir())
            if p.is_file() and p.name not in {"manifest.json", "thermo.lib", "trans.lib"}
        ]
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
            shutil.copy2(folder / item["path"], staged / item["path"])
        shutil.copy2(folder / "manifest.json", staged / "manifest.json")
        verify(staged, root)
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        atomic_json(folder / "manifest.json", record)
        raise
    target.parent.mkdir(parents=True, exist_ok=True)
    staged.rename(target)
    return target


def verify(folder, root=ROOT):
    record = read_json(folder / "manifest.json")
    fixed = check_reference()
    keys = {
        "schema_version",
        "kind",
        "status",
        "started_at",
        "finished_at",
        "source_head",
        "source_dirty",
        "cea_commit",
        "cea_version",
        "cea_binary_sha256",
        "thermo_source_sha256",
        "c_binary_sha256",
        "compiled_database_hashes",
        "assigned_tp_source_hashes",
        "scope",
        "cases",
        "build_manifest_sha256",
        "test_report_sha256",
        "files",
    }
    if (
        not isinstance(record, dict)
        or set(record) != keys
        or type(record.get("schema_version")) is not int
        or record["schema_version"] != 1
        or record["kind"] != "research-frozen-reference"
        or record["status"] != "PASS"
        or record["scope"] != SCOPE
        or type(record["source_dirty"]) is not bool
        or record["cea_commit"] != COMMIT
        or record["cea_version"] != "3.3.4"
        or record["thermo_source_sha256"] != THERMO_SHA
        or record["cea_binary_sha256"] != fixed["executable_sha256"]
        or record["compiled_database_hashes"] != fixed["compiled_database_hashes"]
        or record["assigned_tp_source_hashes"] != SOURCE_HASHES
    ):
        raise ValueError("Frozen reference manifest identity/scope mismatch")
    if not isinstance(record["source_head"], str) or not re.fullmatch(
        "[0-9a-f]{40}", record["source_head"]
    ):
        raise ValueError("Frozen source identity invalid")
    actual = inventory(folder)
    files = record["files"]
    if (
        not isinstance(files, list)
        or len(files) != len(actual)
        or any(
            not isinstance(f, dict)
            or set(f) != {"path", "sha256"}
            or not isinstance(f["path"], str)
            or not isinstance(f["sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", f["sha256"])
            for f in files
        )
        or {f["path"] for f in files} != actual
    ):
        raise ValueError("Frozen file list mismatch")
    for item in files:
        if digest(local_path(folder, item["path"])) != item["sha256"]:
            raise ValueError("Frozen reference hash mismatch")
    for name, identity in SOURCE_HASHES.items():
        if digest(folder / name) != identity:
            raise ValueError("Assigned TP source snapshot mismatch")
    build = read_json(folder / "build-manifest.json")
    tests = read_json(folder / "test-report.json")
    verify_test_report(tests, build, digest(folder / "build-manifest.json"))
    if (
        record["build_manifest_sha256"] != digest(folder / "build-manifest.json")
        or record["test_report_sha256"] != digest(folder / "test-report.json")
        or record["c_binary_sha256"] != build["application"]["sha256"]
    ):
        raise ValueError("Frozen C build/test identity mismatch")
    cases = record["cases"]
    count = 0
    if not isinstance(cases, list) or len(cases) != len(RECIPES):
        raise ValueError("Frozen case count mismatch")
    for case, recipe in zip(cases, RECIPES):
        name, directory, index = recipe
        inputs, state, path = conditions(directory, index, "main_nozzle", root)
        if (
            not isinstance(case, dict)
            or set(case)
            != {
                "id",
                "source_directory",
                "point_index",
                "source_result_sha256",
                "inputs",
                "cea_exit_code",
                "points",
            }
            or (case["id"], case["source_directory"], case["point_index"]) != recipe
            or type(case["point_index"]) is not type(index)
            or not input_matches(case["inputs"], inputs)
            or case["source_result_sha256"] != digest(path)
            or type(case["cea_exit_code"]) is not int
            or case["cea_exit_code"] != 0
        ):
            raise ValueError("Frozen recipe mismatch")
        if (folder / (name + ".inp")).read_text(encoding="utf-8") != case_card(name, inputs):
            raise ValueError("Frozen input card changed")
        if (folder / (name + "-cea-stderr.txt")).read_bytes():
            raise ValueError("Frozen CEA stderr present")
        log = (folder / (name + "-cea-stdout.txt")).read_text(encoding="utf-8")
        if "CEA Version: 3.3.4" not in log or "ERROR" in log or "WARNING" in log:
            raise ValueError("Frozen CEA diagnostics/version")
        saved = case["points"]
        recipes = points(name)
        if not isinstance(saved, list) or len(saved) != len(recipes):
            raise ValueError("Frozen point count mismatch")
        for point, (area, ambient) in zip(saved, recipes):
            supplied = fixed_inputs(inputs, area, ambient, root)
            identity = point_id(name, area, ambient)
            if (
                not isinstance(point, dict)
                or set(point) != {"id", "inputs", "c_command", "c_exit_code", "comparisons"}
                or point["id"] != identity
                or not input_matches(point["inputs"], supplied)
                or type(point["c_exit_code"]) is not int
                or point["c_exit_code"] != 0
                or not isinstance(point["c_command"], list)
                or any(not isinstance(s, str) for s in point["c_command"])
                or len(point["c_command"]) < 2
                or not point["c_command"][0]
                or point["c_command"][1:] != arguments(supplied)
            ):
                raise ValueError("Frozen C point/command mismatch")
            if (folder / (identity + "-c-stderr.txt")).read_bytes():
                raise ValueError("Frozen C stderr present")
            comparisons = point["comparisons"]
            comparison_keys = {"field", "actual", "reference", "difference", "absolute_tolerance"}
            if not isinstance(comparisons, list) or any(
                not isinstance(c, dict)
                or set(c) != comparison_keys
                or not isinstance(c["field"], str)
                or any(
                    type(c[k]) not in (int, float) or not math.isfinite(c[k])
                    for k in comparison_keys - {"field"}
                )
                for c in comparisons
            ):
                raise ValueError("Frozen comparison shape/types invalid")
            if checked_point(folder, name, supplied, state) != comparisons:
                raise ValueError("Frozen comparison changed")
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["archive", "verify"])
    parser.add_argument("directory")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        print(
            archive(args.directory)
            if args.action == "archive"
            else "Frozen reference verified: "
            + str(verify(local_path(ROOT, args.directory)))
            + " points"
        )
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
