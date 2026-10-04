"""Same-condition CEA TP checks for actual saved synthetic-cycle states, never a flight/whole-cycle validation."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

from cea_reference import COMMIT, THERMO_SHA, check_reference, parse_output
from combustion_reference import compare_report
from projectlib import (
    ROOT,
    atomic_json,
    atomic_text,
    digest,
    git,
    local_path,
    now,
    read_json,
    strict_json,
    subprocess_env,
)

STUDY = "results/research/prescribed_cycle_scan_v1_20261004"
SCOPE = (
    "Six restricted gas TP states from synthetic cycle; no same-condition nozzle, "
    "full cycle, liquid property or hardware validation."
)
RECIPES = [
    ("main_base", "main_area_ratio", None, "main_nozzle"),
    ("generator_base", "main_area_ratio", None, "turbine"),
    ("main_t_minus", "chamber_temperature_k", 0, "main_nozzle"),
    ("main_t_plus", "chamber_temperature_k", 2, "main_nozzle"),
    ("main_of_minus", "overall_oxidizer_fuel_ratio", 0, "main_nozzle"),
    ("main_of_plus", "overall_oxidizer_fuel_ratio", 2, "main_nozzle"),
]


def conditions(directory, index, part, root=ROOT):
    path = local_path(root, STUDY + "/" + directory + "/result.json")
    report = read_json(path)
    result = report["baseline"] if index is None else report["points"][index]["report"]
    state = result[part]["chamber" if part == "main_nozzle" else "inlet"]
    of = (
        result["flows"]["main_oxidizer_fuel_ratio"]
        if part == "main_nozzle"
        else result["inputs"]["generator_oxidizer_fuel_ratio"]
    )
    return (
        dict(
            feed_phase="gas",
            pressure_pa=state["pressure_pa"],
            temperature_k=state["temperature_k"],
            oxidizer_fuel_mass_ratio=of,
            fuel_temperature_k=298.15,
            oxidizer_temperature_k=298.15,
        ),
        state,
        path,
    )


def case_card(name, inputs):
    return (
        "! Restricted gas TP reference for saved synthetic cycle state, not whole engine.\n"
        f'problem case={name} tp p,bar={inputs["pressure_pa"]/1e5:.17g} t,k={inputs["temperature_k"]:.17g} o/f={inputs["oxidizer_fuel_mass_ratio"]:.17g}\n'
        "reactants\n fuel=CH4 wt%=100 t,k=298.15\n oxid=O2 wt%=100 t,k=298.15\n"
        "only H2 O2 H2O CO CO2 CH4 H O OH\noutput siunits trace=1.e-8\nend\n"
    )


def run_logged(command, cwd, stdout, stderr, timeout):
    """Retain successful output and partial timeout diagnostics, never a PASS on timeout."""
    try:
        run = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            encoding="utf-8",
            errors="strict",
            timeout=timeout,
            env=subprocess_env(),
        )
    except subprocess.TimeoutExpired as exc:
        for path, data in ((stdout, exc.stdout), (stderr, exc.stderr)):
            text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data or ""
            atomic_text(path, text)
        raise
    atomic_text(stdout, run.stdout)
    atomic_text(stderr, run.stderr)
    return run


def checked_case(folder, name, inputs, state):
    summary = parse_output((folder / (name + ".out")).read_bytes())
    report = strict_json((folder / (name + "-c.json")).read_text(encoding="utf-8"))
    comparisons = compare_report(report, {"summary": summary}, "tp", expected_inputs=inputs)
    # Independently recomputed TP must also correspond to the original study
    # state, not just another point that happens to match the reference card.
    for key in (
        "temperature_k",
        "pressure_pa",
        "h_j_per_kg",
        "s_j_per_kg_k",
        "cp_frozen_j_per_kg_k",
    ):
        if not math.isclose(report["chamber"][key], state[key], rel_tol=1e-10, abs_tol=1e-7):
            raise ValueError("Original study state differs: " + key)
    if report["chamber"]["mole_fractions"] != state["mole_fractions"]:
        raise ValueError("Study/reference composition mismatch")
    return comparisons


def archive(destination, root=ROOT):
    from pipeline import verified_build

    target = local_path(root, destination)
    if target.exists():
        raise FileExistsError("Reference destination already exists")
    build_path = verified_build(root, "Release", require_tests=True)
    build = read_json(build_path)
    executable = local_path(root, build["application"]["path"])
    source = root / "build/reference/cea-v3.3.4"
    cea = root / "build/reference/cea-build-v3.3.4/source/cea.exe"
    if (
        git(source, "rev-parse", "HEAD", check=True).stdout.strip() != COMMIT
        or digest(source / "data/thermo.inp") != THERMO_SHA
    ):
        raise ValueError("Local CEA source/database is not the pinned reference")
    if git(source, "status", "--porcelain", "--untracked-files=no", check=True).stdout.strip():
        raise ValueError("Pinned CEA source has uncommitted modifications")
    fixed = check_reference()
    if digest(cea) != fixed["executable_sha256"]:
        raise ValueError("CEA executable differs from the fixed reference")
    folder = root / "build/research-tp-reference" / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    record = {
        "schema_version": 1,
        "kind": "research-tp-reference",
        "status": "RUNNING",
        "started_at": now(),
        "source_head": git(root, "rev-parse", "HEAD", check=True).stdout.strip(),
        "source_dirty": bool(git(root, "status", "--porcelain").stdout.strip()),
        "cea_version": "3.3.4",
        "cea_commit": COMMIT,
        "cea_binary_sha256": digest(cea),
        "thermo_source_sha256": THERMO_SHA,
        "c_binary_sha256": digest(executable),
        "cases": [],
        "scope": SCOPE,
    }
    atomic_json(folder / "manifest.json", record)
    try:
        for name in ("thermo.lib", "trans.lib"):
            shutil.copy2(root / "build/reference/cea-build-v3.3.4" / name, folder / name)
        record["compiled_database_hashes"] = {
            name: digest(folder / name) for name in ("thermo.lib", "trans.lib")
        }
        if record["compiled_database_hashes"] != fixed["compiled_database_hashes"]:
            raise ValueError("CEA compiled databases changed")
        shutil.copy2(build_path, folder / "build-manifest.json")
        shutil.copy2(build_path.parent / "test-report.json", folder / "test-report.json")
        for name, directory, index, part in RECIPES:
            inputs, state, path = conditions(directory, index, part, root)
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
                or "ERROR" in run.stdout
                or "WARNING" in run.stdout
            ):
                raise ValueError("CEA run failed: " + name)
            command = [
                str(executable),
                "combustion",
                "tp",
                *[
                    format(inputs[key], ".17g")
                    for key in (
                        "temperature_k",
                        "pressure_pa",
                        "oxidizer_fuel_mass_ratio",
                        "fuel_temperature_k",
                        "oxidizer_temperature_k",
                    )
                ],
            ]
            actual = run_logged(
                command, root, folder / (name + "-c.json"), folder / (name + "-c-stderr.txt"), 15
            )
            if actual.returncode or actual.stderr:
                raise ValueError("C TP run failed: " + name)
            record["cases"].append(
                {
                    "id": name,
                    "source_directory": directory,
                    "point_index": index,
                    "part": part,
                    "inputs": inputs,
                    "source_result_sha256": digest(path),
                    "c_command": command,
                    "c_exit_code": actual.returncode,
                    "cea_exit_code": run.returncode,
                    "comparisons": checked_case(folder, name, inputs, state),
                }
            )
        record["status"] = "PASS"
        record["files"] = [
            {"path": p.relative_to(folder).as_posix(), "sha256": digest(p)}
            for p in sorted(folder.iterdir())
            if p.is_file() and p.name not in {"manifest.json", "thermo.lib", "trans.lib"}
        ]
        record["build_manifest_sha256"] = digest(folder / "build-manifest.json")
        record["test_report_sha256"] = digest(folder / "test-report.json")
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        raise
    finally:
        record["finished_at"] = now()
        atomic_json(folder / "manifest.json", record)
    # Verify a data-only snapshot before publishing. A rejected snapshot stays
    # below build, not as a new PASS archive in the research directory.
    staged = folder / "archive"
    staged.mkdir()
    try:
        for file in record["files"]:
            shutil.copy2(folder / file["path"], staged / file["path"])
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
    keys = {
        "schema_version",
        "kind",
        "status",
        "started_at",
        "finished_at",
        "source_head",
        "source_dirty",
        "cea_version",
        "cea_commit",
        "cea_binary_sha256",
        "thermo_source_sha256",
        "c_binary_sha256",
        "cases",
        "scope",
        "compiled_database_hashes",
        "files",
        "build_manifest_sha256",
        "test_report_sha256",
    }
    if (
        not isinstance(record, dict)
        or type(record.get("schema_version")) is not int
        or record["schema_version"] != 1
        or set(record) != keys
        or type(record.get("source_dirty")) is not bool
        or not isinstance(record.get("source_head"), str)
        or not re.fullmatch(r"[0-9a-f]{40}", record["source_head"])
        or any(
            not isinstance(record.get(k), str) or not re.fullmatch(r"[0-9a-f]{64}", record[k])
            for k in (
                "cea_binary_sha256",
                "thermo_source_sha256",
                "c_binary_sha256",
                "build_manifest_sha256",
                "test_report_sha256",
            )
        )
        or record.get("kind") != "research-tp-reference"
        or record.get("status") != "PASS"
        or record.get("scope") != SCOPE
        or record.get("cea_commit") != COMMIT
        or record.get("thermo_source_sha256") != THERMO_SHA
        or record.get("cea_version") != "3.3.4"
    ):
        raise ValueError("Invalid TP reference manifest/version")
    if any(not p.is_file() for p in folder.iterdir()):
        raise ValueError("TP archive contains an undeclared directory")
    files = record.get("files")
    actual = {p.name for p in folder.iterdir() if p.name != "manifest.json"}
    required = {"build-manifest.json", "test-report.json"} | {
        name + suffix
        for name, *_ in RECIPES
        for suffix in (
            ".inp",
            ".out",
            "-cea-stdout.txt",
            "-cea-stderr.txt",
            "-c.json",
            "-c-stderr.txt",
        )
    }
    if (
        actual != required
        or not isinstance(files, list)
        or len(files) != len(actual)
        or any(
            not isinstance(f, dict)
            or set(f) != {"path", "sha256"}
            or not isinstance(f["path"], str)
            or not isinstance(f["sha256"], str)
            for f in files
        )
        or {f["path"] for f in files} != actual
    ):
        raise ValueError("TP reference inventory mismatch")
    for file in files:
        if digest(local_path(folder, file["path"])) != file["sha256"]:
            raise ValueError("TP reference hash mismatch")
    from pipeline import verify_test_report

    build = read_json(folder / "build-manifest.json")
    tests = read_json(folder / "test-report.json")
    verify_test_report(tests, build, digest(folder / "build-manifest.json"))
    fixed = check_reference()
    if (
        record["c_binary_sha256"] != build["application"]["sha256"]
        or record["build_manifest_sha256"] != digest(folder / "build-manifest.json")
        or record["test_report_sha256"] != digest(folder / "test-report.json")
        or record["compiled_database_hashes"] != fixed["compiled_database_hashes"]
    ):
        raise ValueError("TP reference solver/build identity mismatch")
    if record["cea_binary_sha256"] != fixed["executable_sha256"]:
        raise ValueError("TP reference CEA binary differs")
    cases = record["cases"]
    if not isinstance(cases, list) or len(cases) != len(RECIPES):
        raise ValueError("TP case count mismatch")
    for case, recipe in zip(cases, RECIPES):
        name, directory, index, part = recipe
        case_keys = {
            "id",
            "source_directory",
            "point_index",
            "part",
            "inputs",
            "source_result_sha256",
            "c_command",
            "c_exit_code",
            "cea_exit_code",
            "comparisons",
        }
        if not isinstance(case, dict) or set(case) != case_keys:
            raise ValueError("Invalid TP case shape")
        if type(case["point_index"]) is not type(index):
            raise ValueError("Invalid TP point index type")
        if (case["id"], case["source_directory"], case["point_index"], case["part"]) != recipe:
            raise ValueError("TP recipe mismatch")
        inputs, state, path = conditions(directory, index, part, root)
        supplied = case["inputs"]
        if (
            not isinstance(supplied, dict)
            or set(supplied) != set(inputs)
            or any(
                type(v) not in (int, float) or not math.isfinite(v)
                for k, v in supplied.items()
                if k != "feed_phase"
            )
            or supplied != inputs
            or case["source_result_sha256"] != digest(path)
        ):
            raise ValueError("TP study input changed")
        if any(
            type(case.get(k)) is not int or case[k] != 0 for k in ("c_exit_code", "cea_exit_code")
        ):
            raise ValueError("TP exit status not zero")
        expected_args = [
            "combustion",
            "tp",
            *[
                format(inputs[key], ".17g")
                for key in (
                    "temperature_k",
                    "pressure_pa",
                    "oxidizer_fuel_mass_ratio",
                    "fuel_temperature_k",
                    "oxidizer_temperature_k",
                )
            ],
        ]
        if (
            not isinstance(case["c_command"], list)
            or any(not isinstance(x, str) for x in case["c_command"])
            or not case["c_command"]
            or not case["c_command"][0]
            or case["c_command"][1:] != expected_args
        ):
            raise ValueError("TP C command/condition mismatch")
        if (folder / (name + ".inp")).read_text(encoding="utf-8") != case_card(name, inputs):
            raise ValueError("TP card differs from conditions")
        if (folder / (name + "-c-stderr.txt")).read_bytes() or (
            folder / (name + "-cea-stderr.txt")
        ).read_bytes():
            raise ValueError("TP run has stderr")
        log = (folder / (name + "-cea-stdout.txt")).read_text(encoding="utf-8")
        if "CEA Version: 3.3.4" not in log or "ERROR" in log or "WARNING" in log:
            raise ValueError("TP CEA diagnostics/version differs")
        comparisons = case["comparisons"]
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
            raise ValueError("Invalid TP comparison shape/types")
        if checked_case(folder, name, inputs, state) != comparisons:
            raise ValueError("TP comparison changed")
    return len(cases)


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
            else "TP reference verified: "
            + str(verify(local_path(ROOT, args.directory)))
            + " states"
        )
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
