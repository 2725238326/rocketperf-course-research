"""Compare pinned RP-1 product sets with CEA; no production solving in Python."""
from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import sys
import uuid

from cea_reference import COMMIT, SPECIES, THERMO_SHA, check_reference
from feed_candidates import parse_anchors
from adiabatic_study import typed_equal
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json, strict_json
from research_tp_reference import run_logged

SOURCE = ROOT / "build/reference/cea-v3.3.4"
BINARY = ROOT / "build/reference/cea-build-v3.3.4/source/cea.exe"
DATABASE = ROOT / "build/reference/cea-build-v3.3.4"
RATIOS = (0.5, 1.0, 2.2, 2.6, 3.2, 4.0)
SCOPE = "Fixed CEA RP-1/O2(L), assigned enthalpies, product-set comparison; not Chinese kerosene or hardware performance."


def recipes():
    cases = []
    for ratio in RATIOS:
        for products in ("nine-gas", "expanded"):
            name = f"of_{str(ratio).replace('.', '_')}_{products}"
            cases.append(dict(id=name, ratio=ratio, products=products, mode="hp", fuel_temperature=298.15))
    for products in ("nine-gas", "expanded"):
        cases.append(dict(id="rocket_" + products, ratio=2.6, products=products,
                          mode="rocket frozen nfz=1", fuel_temperature=298.15))
    cases.append(dict(id="probe_anchor_temperature", ratio=2.6, products="expanded",
                      mode="hp", fuel_temperature=350.0))
    return cases


def card(case):
    selection = "only " + " ".join(SPECIES) + "\n" if case["products"] == "nine-gas" else ""
    areas = " supar=10,40" if case["mode"].startswith("rocket") else ""
    return (f'problem case={case["id"]} {case["mode"]} p,bar=100 o/f={case["ratio"]}{areas}\n'
            f'reactants\n fuel=RP-1 wt%=100 t,k={case["fuel_temperature"]}\n'
            " oxid=O2(L) wt%=100 t,k=90.170\n" + selection + "output siunits trace=1.e-7\nend\n")


def cea_number(token):
    if "e" not in token.lower():
        token = re.sub(r"(?<=\d)([+-]\d+)$", r"e\1", token)
    value = float(token)
    if not math.isfinite(value):
        raise ValueError("Non-finite CEA number")
    return value


def parse(data):
    text = data.decode("ascii", errors="strict")
    diagnostics = [line.strip() for line in text.splitlines()
                   if any(word in line for word in ("WARNING", "ERROR", "FATAL"))]
    if "\x00" in text:
        diagnostics.append("NUL byte in output")
    rows, fractions = {}, {}
    names = {"P, bar": "pressure_bar", "T, K": "temperature_k", "H, kJ/kg": "h_kj_per_kg",
             "M, (1/n)": "molar_mass_kg_per_kmol", "C*, m/s": "cstar_m_per_s",
             "Ivac, m/s": "vacuum_velocity_m_per_s", "Ae/At": "area_ratio"}
    in_species = False
    for line in text.splitlines():
        stripped = line.strip()
        for prefix, key in names.items():
            if stripped.startswith(prefix + " "):
                if key in rows:
                    raise ValueError("Repeated CEA result row")
                rows[key] = [cea_number(x) for x in stripped[len(prefix):].split()]
        if stripped == "MOLE FRACTIONS":
            in_species = True
        elif stripped.startswith(("PRODUCTS WHICH", "* THERMODYNAMIC", "NOTE.")):
            in_species = False
        elif in_species and stripped:
            parts = stripped.split()
            if len(parts) < 2 or parts[0] in fractions:
                raise ValueError("Invalid CEA species row")
            fractions[parts[0]] = [cea_number(x) for x in parts[1:]]
    if not diagnostics:
        columns = len(rows.get("temperature_k", []))
        if columns not in (1, 4):
            diagnostics.append("Incomplete thermodynamic state table")
        if not fractions:
            diagnostics.append("No product mole fractions printed")
        if diagnostics:
            return dict(status="REJECTED", diagnostics=diagnostics,
                        rows=rows, mole_fractions=fractions)
        if any(len(rows.get(key, [])) != columns for key in
               ("pressure_bar", "h_kj_per_kg", "molar_mass_kg_per_kmol")):
            raise ValueError("CEA thermodynamic columns differ")
        if any(not values or len(values) not in (1, columns) or any(x < 0 for x in values)
               for values in fractions.values()):
            diagnostics.append("Invalid CEA fraction columns")
        if abs(sum(x[0] for x in fractions.values()) - 1) > 5e-5:
            diagnostics.append("CEA printed composition does not sum to one")
    if diagnostics:
        return dict(status="REJECTED", diagnostics=diagnostics,
                    rows=rows, mole_fractions=fractions)
    return dict(status="REJECTED" if diagnostics else "COMPLETE", diagnostics=diagnostics,
                rows=rows, mole_fractions=fractions)


def identity(check_runtime=False):
    reference = check_reference()
    raw = ROOT / "调研/原始来源/20261003_cea_v3.3.4/thermo.inp"
    if digest(raw) != THERMO_SHA:
        raise ValueError("Pinned RP-1 source differs")
    if check_runtime and (digest(BINARY) != reference["executable_sha256"]
        or git(SOURCE, "rev-parse", "HEAD", check=True).stdout.strip() != COMMIT
        or digest(SOURCE / "data/thermo.inp") != THERMO_SHA):
        raise ValueError("Pinned CEA binary/source differs")
    for name, sha in reference["compiled_database_hashes"].items():
        if check_runtime and digest(DATABASE / name) != sha:
            raise ValueError("CEA compiled database differs")
    return dict(cea_commit=COMMIT, cea_binary_sha256=reference["executable_sha256"], thermo_sha256=THERMO_SHA,
                databases=reference["compiled_database_hashes"],
                anchors=parse_anchors(raw.read_text(encoding="ascii"))[1:])


def evaluate(folder):
    summaries = {}
    for case in recipes():
        name = case["id"]
        if (folder / (name + ".inp")).read_text(encoding="utf-8") != card(case):
            raise ValueError("Kerosene input differs from recipe")
        summaries[name] = parse((folder / (name + ".out")).read_bytes())
        log = (folder / (name + "-stdout.txt")).read_text(encoding="utf-8")
        if "CEA Version: 3.3.4" not in log or (folder / (name + "-stderr.txt")).read_bytes():
            raise ValueError("CEA version or stream protocol differs")
        warnings = [line.strip() for line in log.splitlines() if "WARNING" in line or "ERROR" in line]
        if warnings:
            summaries[name]["status"] = "REJECTED"
            summaries[name]["diagnostics"].extend(warnings)
    comparisons = []
    for ratio in RATIOS:
        prefix = f"of_{str(ratio).replace('.', '_')}_"
        restricted, expanded = [summaries[prefix + name] for name in ("nine-gas", "expanded")]
        if restricted["status"] == expanded["status"] == "COMPLETE":
            t9, te = [s["rows"]["temperature_k"][0] for s in (restricted, expanded)]
            extra = {name: values[0] for name, values in expanded["mole_fractions"].items()
                     if name.lstrip("*") not in SPECIES}
            comparisons.append(dict(ratio=ratio, restricted_temperature_k=t9,
                                     expanded_temperature_k=te, delta_temperature_k=t9-te,
                                     expanded_extra_mole_fractions=extra))
    return summaries, comparisons


def probe(folder):
    manifest = read_json(ROOT / "project/modules.json")
    sources = [source for module in manifest["modules"] if module["id"] in {"core", "thermo", "nozzle"}
               for source in module["sources"]]
    compiler = read_json(local_path(ROOT, read_json(ROOT / "build/release/latest.json")["manifest"]))["compiler"]
    executable = folder / "probe.exe"
    command = [compiler, "-std=c17", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
               "-Wconversion", "-Wshadow", "-Wstrict-prototypes", "-Wmissing-prototypes", "-fno-common",
               "-Iinclude", "tools/kerosene_probe.c", *sources, "-lm", "-o", str(executable)]
    identities = {name: digest(ROOT / name) for name in sources + ["tools/kerosene_probe.c"]}
    identities.update({p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT / "include").rglob("*.h")})
    identities.update({p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT / "src/thermo").glob("*.h")})
    build = run_logged(command, ROOT, folder / "c-build-stdout.txt", folder / "c-build-stderr.txt", 60)
    if build.returncode or build.stdout or build.stderr:
        raise ValueError("Research C driver strict build failed")
    run = run_logged([str(executable)], ROOT, folder / "c-stdout.json", folder / "c-stderr.txt", 30)
    if run.returncode or run.stderr:
        raise ValueError("Research C driver execution failed")
    if any(digest(ROOT / name) != sha for name, sha in identities.items()):
        raise ValueError("Research C inputs changed during build/run")
    atomic_json(folder / "c-build.json", dict(compiler=compiler, command=command, sources=identities,
                                              binary_sha256=digest(executable)))


def compare_c(folder, summaries):
    report = strict_json((folder / "c-stdout.json").read_text(encoding="utf-8"))
    if report.get("scope") != "fixed-rp1-nine-gas-research" or len(report.get("points", [])) != len(RATIOS):
        raise ValueError("C research scope or grid differs")
    differences = []
    for point, ratio in zip(report["points"], RATIOS):
        if type(point["ratio"]) not in (float, int) or point["ratio"] != ratio:
            raise ValueError("C research ratio differs")
        expected_status = "numeric_error" if ratio == 0.5 else "ok"
        if point["status"] != expected_status:
            raise ValueError("C research observed status differs")
        fuel, oxidizer = identity()["anchors"][1], identity()["anchors"][0]
        f = 1 / (1 + ratio)
        h = f * fuel["assigned_enthalpy_j_per_mol"] * 1000 / fuel["molar_mass_kg_per_kmol"]
        h += (1-f) * oxidizer["assigned_enthalpy_j_per_mol"] * 1000 / oxidizer["molar_mass_kg_per_kmol"]
        if not math.isclose(point["h_feed_j_per_kg"], h, abs_tol=1e-8, rel_tol=1e-12):
            raise ValueError("C research feed enthalpy differs")
        if point["status"] != "ok":
            if set(point) != {"ratio", "status", "h_feed_j_per_kg"}:
                raise ValueError("Failed C point contains success data")
            differences.append(dict(ratio=ratio, status=point["status"]))
            continue
        reference = summaries[f"of_{str(ratio).replace('.', '_')}_nine-gas"]
        if reference["status"] != "COMPLETE":
            raise ValueError("No valid restricted CEA reference for successful C point")
        delta = point["temperature_k"] - reference["rows"]["temperature_k"][0]
        if abs(delta) > 0.02 or abs(point["h_residual_j_per_kg"]) > 0.01:
            raise ValueError("C/CEA restricted HP discrepancy")
        if (len(point["fractions"]) != len(SPECIES)
            or any(type(x) not in (int, float) or x < 0 for x in point["fractions"])
            or abs(sum(point["fractions"]) - 1) > 1e-10):
            raise ValueError("C research fractions do not sum to one")
        for species, fraction in zip(SPECIES, point["fractions"]):
            expected = reference["mole_fractions"].get(species, [0])[0]
            if abs(fraction - expected) > 2e-6:
                raise ValueError("C/CEA restricted composition discrepancy")
        differences.append(dict(ratio=ratio, status="ok", temperature_delta_k=delta))
        nozzles = point.get("nozzles", [])
        if ([n["area_ratio"] for n in nozzles] != ([10, 40] if ratio == 2.6 else [])):
            raise ValueError("C nozzle grid differs")
        for nozzle in nozzles:
            index = 1 if nozzle["area_ratio"] == 10 else 2
            rows = summaries["rocket_nine-gas"]["rows"]
            if nozzle["status"] != "ok" or abs(nozzle["cstar_m_per_s"]-rows["cstar_m_per_s"][index]) > 0.03:
                raise ValueError("C/CEA frozen cstar discrepancy")
            if abs(nozzle["vacuum_velocity_m_per_s"]-rows["vacuum_velocity_m_per_s"][index]) > 0.03:
                raise ValueError("C/CEA frozen velocity discrepancy")
            velocity, flow = nozzle["vacuum_velocity_m_per_s"], nozzle["mass_flow_kg_per_s"]
            for value, expected in ((flow, 1e7*0.01/nozzle["cstar_m_per_s"]),
                                    (nozzle["thrust_n"], flow*velocity), (nozzle["isp_s"], velocity/9.80665)):
                if not math.isclose(value, expected, rel_tol=1e-10, abs_tol=1e-8):
                    raise ValueError("C nozzle performance relation differs")
    return differences


def verify(folder):
    record = read_json(folder / "manifest.json")
    if type(record.get("schema_version")) is not int or record.get("schema_version") != 1 or record.get("scope") != SCOPE or record.get("status") != "PASS":
        raise ValueError("Kerosene archive identity differs")
    typed_equal(record["identity"], identity(), "kerosene identity")
    typed_equal(record["recipes"], recipes(), "kerosene recipes")
    expected = {case["id"] + suffix for case in recipes()
                for suffix in (".inp", ".out", "-stdout.txt", "-stderr.txt")}
    expected |= {"c-build.json", "c-build-stdout.txt", "c-build-stderr.txt", "c-stdout.json", "c-stderr.txt"}
    if {p.name for p in folder.iterdir()} != expected | {"manifest.json"}:
        raise ValueError("Kerosene archive inventory differs")
    if set(record["files"]) != expected or any(digest(folder / name) != sha for name, sha in record["files"].items()):
        raise ValueError("Kerosene archive bytes differ")
    summaries, comparisons = evaluate(folder)
    typed_equal(record["summaries"], summaries, "kerosene summary")
    typed_equal(record["comparisons"], comparisons, "kerosene comparisons")
    typed_equal(record["c_comparisons"], compare_c(folder, summaries), "C kerosene comparisons")
    if any((folder / name).stat().st_size for name in ("c-build-stdout.txt", "c-build-stderr.txt", "c-stderr.txt")):
        raise ValueError("C kerosene diagnostics present")
    if summaries["of_0_5_nine-gas"]["status"] != "REJECTED":
        raise ValueError("Low-ratio invalid reference state was not recorded")
    return len(summaries)


def archive(folder):
    if folder.exists():
        raise FileExistsError("Use a new kerosene archive version")
    fixed = identity(check_runtime=True)
    folder.mkdir(parents=True)
    record = dict(schema_version=1, scope=SCOPE, status="RUNNING", started_at=now(), identity=fixed,
                  source_head=git(ROOT, "rev-parse", "HEAD", check=True).stdout.strip(), recipes=recipes())
    atomic_json(folder / "manifest.json", record)
    try:
        work = ROOT / "build/kerosene-reference" / uuid.uuid4().hex
        work.mkdir(parents=True, exist_ok=False)
        for name in fixed["databases"]:
            shutil.copy2(DATABASE / name, work / name)
        for case in recipes():
            name = case["id"]
            atomic_text(work / (name + ".inp"), card(case))
            run = run_logged([str(BINARY), "-v", name], work, work / (name + "-stdout.txt"),
                             work / (name + "-stderr.txt"), 30)
            if run.returncode:
                raise ValueError("CEA process failed: " + name)
            for suffix in (".inp", ".out", "-stdout.txt", "-stderr.txt"):
                shutil.copy2(work / (name + suffix), folder / (name + suffix))
        probe(work)
        for name in ("c-build.json", "c-build-stdout.txt", "c-build-stderr.txt", "c-stdout.json", "c-stderr.txt"):
            shutil.copy2(work / name, folder / name)
        record["summaries"], record["comparisons"] = evaluate(folder)
        record["c_comparisons"] = compare_c(folder, record["summaries"])
        if identity(check_runtime=True) != fixed:
            raise ValueError("CEA inputs changed during computation")
        record["files"] = {p.name: digest(p) for p in sorted(folder.iterdir()) if p.name != "manifest.json"}
        record["status"] = "PASS"
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        raise
    finally:
        record["finished_at"] = now()
        atomic_json(folder / "manifest.json", record)
    return verify(folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("archive", "verify"))
    parser.add_argument("directory")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        folder = local_path(ROOT, args.directory)
        print(f"Kerosene CEA cases: {(archive if args.action == 'archive' else verify)(folder)}")
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
