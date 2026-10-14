"""Precompute the defense demo page data with the tested release rocketperf.exe.

Every number shown by deliverables/demo/index.html comes from a C run made here;
the page only looks values up. Rejected points keep the C status and message.

    python tools/demo_data.py            # run grid, inject data into the page
    python tools/demo_data.py --check    # verify the embedded data matches the build
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
import subprocess
import sys

from pipeline import verified_build
from projectlib import ROOT, atomic_text, digest, git, local_path, now, read_json, subprocess_env

PAGE = ROOT / "deliverables" / "demo" / "index.html"
MARK = re.compile(r"(<script id=\"rp-data\" type=\"application/json\">)(.*?)(</script>)", re.S)

PC_PA = 1e7
THROAT_M2 = 0.01
AREA_RATIOS = (2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60)
AMBIENTS_PA = (0, 5000, 50000, 101325)
CH4_OF = tuple(round(2.4 + 0.1 * i, 1) for i in range(17))   # 2.4 .. 4.0
RP1_OF = tuple(round(2.2 + 0.1 * i, 1) for i in range(19))   # 2.2 .. 4.0 (method domain)
CH4_ARGS = ("coolprop710-cea334-liquid-molar-v1", "heos710-cea334-ideal-zero-298.15-v1", "liquid",
            "120", "1e7", "100", "1e7")
RP1_ARGS = ("cea-v3.3.4-rp1-o2l-assigned-v1", "liquid", "RP-1", "O2(L)", "10000000")
CYCLES = ("zq3_y1_stage1", "cz10b_first_stage1")


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
    return None, {"status": status, "message": message}


def chamber_point(exe, fuel, ratio, area, ambient):
    if fuel == "ch4":
        arguments = ("combustion", "frozen-liquid-state", *CH4_ARGS, f"{PC_PA:g}", f"{ratio}",
                     f"{area}", f"{ambient}", f"{THROAT_M2}")
    else:
        arguments = ("combustion", "frozen-rp1", *RP1_ARGS, f"{ratio}", "298.15", "90.170",
                     f"{area}", f"{ambient}", f"{THROAT_M2}")
    data, failure = run(exe, arguments)
    if failure:
        return failure
    nozzle, geometry = data["nozzle"], data["geometry"]
    return {"status": "ok", "isp": number(geometry["specific_impulse_s"]), "f": number(geometry["thrust_n"]),
            "mdot": number(geometry["mass_flow_kg_per_s"]), "cstar": number(nozzle["cstar_m_per_s"]),
            "cf": number(nozzle["thrust_coefficient"]), "tc": number(data["chamber"]["temperature_k"]),
            "pe": number(nozzle["exit"]["gas"]["pressure_pa"]), "me": number(nozzle["exit"]["mach"]),
            "ae": number(geometry["exit_area_m2"])}


def matched_area(exe, ratio, ambient):
    arguments = ("combustion", "regime-liquid-state", *CH4_ARGS, f"{PC_PA:g}", f"{ratio}", "40",
                 f"{ambient}", f"{THROAT_M2}")
    data, failure = run(exe, arguments)
    if failure or not data["regime"]["matched_area_ratio"]["available"]:
        return None
    return number(data["regime"]["matched_area_ratio"]["area_ratio"])


def cycle(exe, name):
    data, failure = run(exe, ("cycle", "adiabatic", f"cases/vehicles/{name}.ini"))
    if failure:
        raise ValueError(f"Cycle case {name} failed: {failure}")
    b, t = data["balance"], data["turbine"]
    keys = ("fuel_mass_flow_kg_per_s", "oxidizer_mass_flow_kg_per_s", "branch_mass_flow_kg_per_s",
            "branch_fuel_mass_flow_kg_per_s", "branch_oxidizer_mass_flow_kg_per_s", "returned_mass_flow_kg_per_s",
            "external_mass_flow_kg_per_s", "main_mass_flow_kg_per_s", "main_fuel_mass_flow_kg_per_s",
            "main_oxidizer_mass_flow_kg_per_s", "pump_power_w", "turbine_power_w", "mechanical_loss_w", "main_thrust_n", "branch_thrust_n",
            "total_thrust_n", "engine_specific_impulse_s", "main_throat_area_m2",
            "inlet_enthalpy_rate_w", "exit_total_enthalpy_rate_w",
            "mass_relative_residual", "shaft_residual_w", "energy_residual_w")
    return {"case": name, "staged": data["inputs"]["staged_combustion"], "of": data["inputs"]["overall_oxidizer_fuel_ratio"],
            "preburner_of": data["inputs"]["preburner_oxidizer_fuel_ratio"], "feed": data["inputs"]["feed_model"],
            "chamber_pa": data["inputs"]["chamber_pressure_pa"], "preburner_pa": data["inputs"]["preburner_pressure_pa"],
            "total_kg_s": data["inputs"]["total_mass_flow_kg_per_s"], "aux_w": data["inputs"]["auxiliary_power_w"],
            "shaft_eff": data["inputs"]["shaft_efficiency"], "main_area_ratio": data["inputs"]["main_area_ratio"],
            "fuel_pump_w": number(data["pumps"]["fuel"]["shaft_power_w"]),
            "ox_pump_w": number(data["pumps"]["oxidizer"]["shaft_power_w"]),
            "preburner_t": number(data["preburner"]["gas"]["temperature_k"]),
            "chamber_t": number(data["chamber"]["gas"]["temperature_k"]),
            "turbine_in_pa": number(t["inlet"]["pressure_pa"]), "turbine_out_pa": number(t["outlet"]["pressure_pa"]),
            "turbine_out_t": number(t["outlet"]["temperature_k"]),
            "return_floor_pa": data["inputs"]["chamber_pressure_pa"] + data["inputs"]["return_pressure_drop_pa"],
            "element_residual": [number(x) for x in data["diagnostics"]["exit_element_relative_residual"]],
            **{k: number(b[k]) for k in keys}}


def generate(exe):
    jobs = [("ch4", r, a, p) for r in CH4_OF for a in AREA_RATIOS for p in AMBIENTS_PA]
    jobs += [("rp1", r, a, p) for r in RP1_OF for a in AREA_RATIOS for p in AMBIENTS_PA]
    with ThreadPoolExecutor(max_workers=8) as pool:
        points = list(pool.map(lambda job: chamber_point(exe, *job), jobs))
        matched = list(pool.map(lambda job: matched_area(exe, *job), [(r, p) for r in CH4_OF for p in AMBIENTS_PA[1:]]))
    grid = {"ch4": {}, "rp1": {}}
    for (fuel, ratio, area, ambient), point in zip(jobs, points):
        grid[fuel][f"{ratio}|{area}|{ambient}"] = point
    match = {f"{r}|{p}": m for (r, p), m in zip([(r, p) for r in CH4_OF for p in AMBIENTS_PA[1:]], matched)}
    return grid, match, len(jobs) + len(matched)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Recompute and compare against the embedded data.")
    args = parser.parse_args()
    manifest_path = verified_build(ROOT, "Release", require_tests=True)
    manifest = read_json(manifest_path)
    exe = local_path(ROOT, manifest["application"]["path"])
    grid, match, runs = generate(exe)
    cycles = [cycle(exe, name) for name in CYCLES]
    payload = {"axes": {"pc_pa": PC_PA, "throat_m2": THROAT_M2, "area_ratios": AREA_RATIOS,
                        "ambients_pa": AMBIENTS_PA, "ch4_of": CH4_OF, "rp1_of": RP1_OF},
               "grid": grid, "matched_area_ratio": match, "cycles": cycles,
               "provenance": {"binary_sha256": manifest["application"]["sha256"],
                              "build_manifest": manifest_path.relative_to(ROOT).as_posix(),
                              "build_manifest_sha256": digest(manifest_path),
                              "git_head": git(ROOT, "rev-parse", "--short", "HEAD").stdout.strip(),
                              "c_runs": runs + len(cycles),
                              "inlets": {"ch4": "CoolProp 7.1.0 单相表 CH4 120 K/10 MPa, O2 100 K/10 MPa",
                                         "rp1": "CEA指定RP-1 298.15 K, O2(L) 90.170 K"}}}
    page = PAGE.read_text(encoding="utf-8")
    if not MARK.search(page):
        raise SystemExit(f"Data marker not found in {PAGE}")
    if args.check:
        # Physics fields must match exactly; build identity changes with every rebuild and is reported only.
        embedded = json.loads(MARK.search(page).group(2))
        fresh = json.loads(json.dumps(payload))
        for field in ("axes", "grid", "matched_area_ratio", "cycles"):
            if embedded.get(field) != fresh[field]:
                raise SystemExit(f"Embedded demo data field '{field}' differs from a fresh run of the tested build.")
        same = embedded["provenance"].get("binary_sha256") == fresh["provenance"]["binary_sha256"]
        print(f"PASS: {runs + len(cycles)} C runs reproduce the embedded data"
              f" ({'same binary' if same else 'binary rebuilt since generation'})")
        return
    payload["provenance"]["generated_at"] = now()
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    atomic_text(PAGE, MARK.sub(lambda m: m.group(1) + text + m.group(3), page, count=1))
    failed = sum(1 for fuel in grid.values() for point in fuel.values() if point["status"] != "ok")
    print(f"Wrote {PAGE.relative_to(ROOT)}: {runs + len(cycles)} C runs, {failed} rejected by C")


if __name__ == "__main__":
    sys.exit(main())
