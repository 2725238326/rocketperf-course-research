"""Precompute the defense demo page data with the tested release rocketperf.exe.

Every physical number on deliverables/demo/index.html comes from a C run made
here (or from a saved validation/engineering archive); the page only looks
values up. Rejected points keep the C status and message.

    python tools/demo_data.py            # run C, assemble the page from deliverables/demo/src
    python tools/demo_data.py --check    # rerun C; embedded data and page sources must match
    python tools/demo_data.py --assemble # page sources changed only: rebuild with the embedded data
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
import subprocess
import sys

import demo_page
from pipeline import verified_build
from projectlib import ROOT, digest, git, local_path, now, read_json, subprocess_env

PC_PA, THROAT_M2 = 1e7, 0.01
AREA_RATIOS = (2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60)
AMBIENTS_PA = (0, 5000, 50000, 101325)
CH4_OF = tuple(round(2.0 + 0.1 * i, 1) for i in range(21))      # 2.0 .. 4.0
RP1_OF = tuple(round(2.2 + 0.1 * i, 1) for i in range(19))      # 2.2 .. 4.0, C method domain
CHAMBER_OF = tuple(round(0.5 + 0.1 * i, 1) for i in range(36))  # 0.5 .. 4.0, carbon guard visible
CH4_ARGS = ("coolprop710-cea334-liquid-molar-v1", "heos710-cea334-ideal-zero-298.15-v1", "liquid", "120", "1e7", "100", "1e7")
RP1_ARGS = ("cea-v3.3.4-rp1-o2l-assigned-v1", "liquid", "RP-1", "O2(L)", "10000000")
CYCLES = ("zq3_y1_stage1", "cz10b_first_stage1")
SPECIES = ("H2", "O2", "H2O", "CO", "CO2", "CH4", "H", "O", "OH")
GRAPHITE = re.compile(r"graphite activity ([0-9.eE+-]+)")
COMMANDS = {"ch4": "./build/release/rocketperf.exe combustion frozen-liquid-state " + " ".join(CH4_ARGS) + " 1e7 {of} {ar} {pa} 0.01",
            "rp1": "./build/release/rocketperf.exe combustion frozen-rp1 " + " ".join(RP1_ARGS) + " {of} 298.15 90.170 {ar} {pa} 0.01",
            "regime": "./build/release/rocketperf.exe combustion regime-liquid-state " + " ".join(CH4_ARGS) + " 1e7 {of} {ar} {pa} 0.01 --text",
            "cycle": "./build/release/rocketperf.exe cycle adiabatic cases/vehicles/{case}.ini --text"}


def number(value):
    return float(f"{value:.6g}")


def run(exe, arguments):
    completed = subprocess.run([str(exe), *arguments], cwd=ROOT, capture_output=True, encoding="utf-8",
                               errors="replace", timeout=60, check=False, env=subprocess_env())
    if completed.returncode == 0:
        return json.loads(completed.stdout), None
    status, _, message = completed.stderr.strip().partition(": ")
    if completed.returncode != 4 or not status:
        raise ValueError(f"Unexpected exit {completed.returncode}: {' '.join(arguments)}\n{completed.stderr}")
    found = GRAPHITE.search(message)
    return None, {"status": status, "message": message, "ac": number(float(found.group(1))) if found else None}


def diagnostics(data):
    """[HP outer iterations, final TP Newton iterations, max |element residual|, h residual J/kg, continuity]."""
    d = data["diagnostics"]
    return [d["hp_iterations"], d["equilibrium_iterations"], number(max(abs(x) for x in d["element_relative_residual"])),
            number(d["enthalpy_residual_j_per_kg"]), number(data["nozzle"]["continuity_relative_residual"])]


def chamber_point(exe, fuel, ratio, area, ambient):
    head = ("combustion", "frozen-liquid-state", *CH4_ARGS, f"{PC_PA:g}", f"{ratio}") if fuel == "ch4" else \
        ("combustion", "frozen-rp1", *RP1_ARGS, f"{ratio}", "298.15", "90.170")
    data, failure = run(exe, (*head, f"{area}", f"{ambient}", f"{THROAT_M2}"))
    if failure:
        return failure
    nozzle, geometry, gas = data["nozzle"], data["geometry"], data["chamber"]
    return {"status": "ok", "isp": number(geometry["specific_impulse_s"]), "f": number(geometry["thrust_n"]),
            "mdot": number(geometry["mass_flow_kg_per_s"]), "cstar": number(nozzle["cstar_m_per_s"]),
            "cf": number(nozzle["thrust_coefficient"]), "tc": number(gas["temperature_k"]),
            "pe": number(nozzle["exit"]["gas"]["pressure_pa"]), "me": number(nozzle["exit"]["mach"]),
            "ae": number(geometry["exit_area_m2"]), "ac": number(data["diagnostics"]["graphite_activity"]),
            "d": diagnostics(data)}


def chamber_sweep(exe, ratio):
    """Liquid CH4/O2 chamber at Pc 10 MPa with frozen A10 vacuum nozzle; refusals keep a_C."""
    data, failure = run(exe, ("combustion", "frozen-liquid-state", *CH4_ARGS, f"{PC_PA:g}", f"{ratio}", "10", "0", f"{THROAT_M2}"))
    if failure:
        return failure
    gas = data["chamber"]
    cp, gas_r = gas["cp_frozen_j_per_kg_k"], gas["gas_constant_j_per_kg_k"]
    return {"status": "ok", "tc": number(gas["temperature_k"]), "cstar": number(data["nozzle"]["cstar_m_per_s"]),
            "isp": number(data["geometry"]["specific_impulse_s"]), "mw": number(gas["molar_mass_kg_per_kmol"]),
            "gamma": number(cp / (cp - gas_r)), "ac": number(data["diagnostics"]["graphite_activity"]),
            "h": number(data["boundary"]["inlet_mixture_h_j_per_kg"]),
            "x": [number(gas["mole_fractions"][s]) for s in SPECIES], "d": diagnostics(data)}


def matched_area(exe, ratio, ambient):
    data, failure = run(exe, ("combustion", "regime-liquid-state", *CH4_ARGS, f"{PC_PA:g}", f"{ratio}", "40", f"{ambient}", f"{THROAT_M2}"))
    if failure or not data["regime"]["matched_area_ratio"]["available"]:
        return None
    return number(data["regime"]["matched_area_ratio"]["area_ratio"])


def cycle(exe, name):
    data, failure = run(exe, ("cycle", "adiabatic", f"cases/vehicles/{name}.ini"))
    if failure:
        raise ValueError(f"Cycle case {name} failed: {failure}")
    i, b, t, pumps = data["inputs"], data["balance"], data["turbine"], data["pumps"]
    main, branch = data["main_nozzle"]["nozzle"], (data["branch_nozzle"] or {}).get("nozzle")
    keep = {k: number(v) for k, v in b.items() if isinstance(v, (int, float))}
    return {"case": name, "object_ref": data["case"]["object_ref"], "evidence": data["case"]["cycle_evidence"],
            "inputs": {k: v for k, v in i.items() if isinstance(v, (int, float, bool))}, "feed": i["feed_model"],
            "density": {k: number(data["feed_states"][k]["density_kg_per_m3"]) for k in ("fuel", "oxidizer")},
            "pump_w": {k: number(pumps[k]["shaft_power_w"]) for k in ("fuel", "oxidizer")},
            "preburner": {"t": number(data["preburner"]["gas"]["temperature_k"]), "ac": number(data["preburner"]["diagnostics"]["graphite_activity"])},
            "chamber": {"t": number(data["chamber"]["gas"]["temperature_k"]), "ac": number(data["chamber"]["diagnostics"]["graphite_activity"])},
            "turbine": {"in_t": number(t["inlet"]["temperature_k"]), "in_pa": number(t["inlet"]["pressure_pa"]),
                        "out_t": number(t["outlet"]["temperature_k"]), "out_pa": number(t["outlet"]["pressure_pa"]),
                        "work_j_kg": number(t["specific_work_j_per_kg"])},
            "nozzle": {"cf": number(main["thrust_coefficient"]), "cstar": number(main["cstar_m_per_s"]),
                       "pe": number(main["exit"]["gas"]["pressure_pa"]), "me": number(main["exit"]["mach"])},
            "branch": None if branch is None else {"pe": number(branch["exit"]["gas"]["pressure_pa"]), "me": number(branch["exit"]["mach"])},
            "element_residual": [number(x) for x in data["diagnostics"]["exit_element_relative_residual"]],
            "turbine_pressure_iterations": data["diagnostics"]["turbine_pressure_iterations"], "balance": keep}


def generate(exe):
    jobs = [("ch4", r, a, p) for r in CH4_OF for a in AREA_RATIOS for p in AMBIENTS_PA]
    jobs += [("rp1", r, a, p) for r in RP1_OF for a in AREA_RATIOS for p in AMBIENTS_PA]
    matches = [(r, p) for r in CH4_OF for p in AMBIENTS_PA[1:]]
    with ThreadPoolExecutor(max_workers=8) as pool:
        points = list(pool.map(lambda job: chamber_point(exe, *job), jobs))
        matched = list(pool.map(lambda job: matched_area(exe, *job), matches))
        chamber = list(pool.map(lambda ratio: chamber_sweep(exe, ratio), CHAMBER_OF))
    grid = {"ch4": {}, "rp1": {}}
    for (fuel, ratio, area, ambient), point in zip(jobs, points):
        grid[fuel][f"{ratio}|{area}|{ambient}"] = point
    return {"grid": grid, "matched_area_ratio": {f"{r}|{p}": m for (r, p), m in zip(matches, matched)},
            "chamber": dict(zip(map(str, CHAMBER_OF), chamber)), "cycles": [cycle(exe, name) for name in CYCLES],
            "runs": len(jobs) + len(matches) + len(chamber) + len(CYCLES)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Rerun C and compare against the embedded data.")
    parser.add_argument("--assemble", action="store_true", help="Rebuild the page from its sources without rerunning C.")
    args = parser.parse_args()
    if args.assemble:
        demo_page.reassemble()
        print(f"Reassembled {demo_page.PAGE.relative_to(ROOT)} from deliverables/demo/src")
        return
    manifest_path = verified_build(ROOT, "Release", require_tests=True)
    manifest = read_json(manifest_path)
    result = generate(local_path(ROOT, manifest["application"]["path"]))
    payload = {"axes": {"pc_pa": PC_PA, "throat_m2": THROAT_M2, "area_ratios": AREA_RATIOS, "ambients_pa": AMBIENTS_PA,
                        "ch4_of": CH4_OF, "rp1_of": RP1_OF, "chamber_of": CHAMBER_OF, "species": SPECIES},
               **{k: result[k] for k in ("grid", "matched_area_ratio", "chamber", "cycles")},
               "commands": COMMANDS, "validation": demo_page.validation_summary(),
               "engineering": demo_page.engineering(manifest_path, manifest),
               "provenance": {"binary_sha256": manifest["application"]["sha256"],
                              "build_manifest": manifest_path.relative_to(ROOT).as_posix(),
                              "build_manifest_sha256": digest(manifest_path), "c_runs": result["runs"],
                              "git_head": git(ROOT, "rev-parse", "--short", "HEAD").stdout.strip(),
                              "inlets": {"ch4": "CoolProp 7.1.0 单相表 CH₄ 120 K / O₂ 100 K，入口 10 MPa",
                                         "rp1": "CEA 指定 RP-1 298.15 K / O₂(L) 90.170 K"}}}
    if args.check:
        demo_page.check(payload, demo_page.PHYSICS_FIELDS)
        print(f"PASS: {result['runs']} C runs reproduce the embedded data; page matches its sources")
        return
    payload["provenance"]["generated_at"] = now()
    demo_page.write(payload)
    failed = sum(1 for fuel in result["grid"].values() for point in fuel.values() if point["status"] != "ok")
    print(f"Wrote {demo_page.PAGE.relative_to(ROOT)}: {result['runs']} C runs, {failed} grid points rejected by C")


if __name__ == "__main__":
    sys.exit(main())
