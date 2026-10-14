"""Archive/check C17 adiabatic cycles and pinned CEA chemical references.

Python recomputes published-state relations; it supplies no production solver.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

from cea_reference import SPECIES, COMMIT, THERMO_SHA, check_reference
from feed_candidates import parse_anchors
from gas_checks import database, mixture
from kerosene_reference import parse as parse_cea
from liquid_table import expected_report, reference as liquid_reference
from pipeline import verified_build, snapshot_values
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json, strict_json, subprocess_env

MODEL = "adiabatic_single_shaft_cycle_v1"
CASES = ("zq3_y1_stage1", "zq3_y1_stage2", "cz10b_first_stage1", "cz10b_first_stage2", "cz10b_first_stage2_orsc")
NUMBERS = {
    "total_mass_flow_kg_per_s", "overall_oxidizer_fuel_ratio", "fuel_temperature_k", "oxidizer_temperature_k", "fuel_density_override_kg_per_m3",
    "chamber_pressure_pa", "main_area_ratio", "preburner_pressure_pa", "preburner_oxidizer_fuel_ratio", "turbine_outlet_pressure_pa",
    "turbine_efficiency", "shaft_efficiency", "auxiliary_power_w", "maximum_branch_fraction", "pump_to_chamber_drop_pa",
    "pump_to_preburner_drop_pa", "return_pressure_drop_pa", "branch_area_ratio", "branch_axial_projection", "ambient_pressure_pa",
    *(f"{p}_pump_{key}" for p in ("fuel", "oxidizer") for key in ("inlet_pressure_pa", "outlet_pressure_pa", "efficiency")),
}
BALANCE = {
    "fuel_mass_flow_kg_per_s", "oxidizer_mass_flow_kg_per_s", "branch_mass_flow_kg_per_s", "branch_fuel_mass_flow_kg_per_s",
    "branch_oxidizer_mass_flow_kg_per_s", "returned_mass_flow_kg_per_s", "external_mass_flow_kg_per_s", "main_mass_flow_kg_per_s",
    "main_fuel_mass_flow_kg_per_s", "main_oxidizer_mass_flow_kg_per_s", "main_oxidizer_fuel_ratio", "turbine_power_w", "pump_power_w",
    "mechanical_loss_w", "generator_heat_w", "chamber_heat_w", "inlet_enthalpy_rate_w", "exit_total_enthalpy_rate_w", "main_throat_area_m2",
    "branch_throat_area_m2", "main_thrust_n", "branch_thrust_n", "total_thrust_n", "main_effective_velocity_m_per_s", "engine_effective_velocity_m_per_s",
    "engine_specific_impulse_s", "mass_residual_kg_per_s", "shaft_residual_w", "energy_residual_w", "mass_relative_residual", "shaft_relative_residual", "energy_relative_residual",
}


@lru_cache(maxsize=1)
def feed_reference():
    return liquid_reference()[0], parse_anchors((ROOT / "调研/原始来源/20261003_cea_v3.3.4/thermo.inp").read_text(encoding="ascii"))


def validate(report, input_text):
    required = {"schema_version", "program_version", "model", "dataset_id", "architecture", "case", "inputs", "feed_states", "pumps",
                "preburner", "chamber", "turbine", "main_nozzle", "branch_nozzle", "balance", "mixing", "diagnostics", "limitations"}
    if not isinstance(report, dict) or set(report) != required or type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ValueError("Invalid adiabatic-cycle report schema")
    values = snapshot_values(input_text)
    metadata = {"schema_version", "case_id", "case_kind", "model", "object_ref", "source_ref", "cycle_evidence", "feed_model", "staged_combustion"}
    if set(values) != NUMBERS | metadata or values["model"] != MODEL or values["schema_version"] != "1" or values["case_kind"] != "research_scenario":
        raise ValueError("Invalid adiabatic input snapshot")
    if values["staged_combustion"] not in ("true", "false"):
        raise ValueError("Invalid topology boolean")
    staged = values["staged_combustion"] == "true"
    if (report["model"] != MODEL or report["dataset_id"] != database()["dataset_id"] or
        not re.fullmatch(r"\d+\.\d+\.\d+", report["program_version"]) or
        report["architecture"] != ("all_oxidizer_staged_combustion" if staged else "gas_generator_external")):
        raise ValueError("Model/topology/version mismatch")
    expected_case = dict(id=values["case_id"], kind=values["case_kind"], object_ref=values["object_ref"],
                         source_ref=values["source_ref"], cycle_evidence=values["cycle_evidence"])
    if report["case"] != expected_case or values["cycle_evidence"] not in ("family_supported", "unresolved_scenario", "method_only"):
        raise ValueError("Cycle provenance mismatch")
    i, b = report["inputs"], report["balance"]
    if set(i) != NUMBERS | {"feed_model", "staged_combustion"} or type(i["staged_combustion"]) is not bool or i["staged_combustion"] != staged or i["feed_model"] != values["feed_model"]:
        raise ValueError("Incomplete/mismatched cycle inputs")
    def numeric(obj, keys, label):
        if not isinstance(obj, dict) or set(obj) != keys or any(type(x) not in (int, float) or not math.isfinite(x) for x in obj.values()):
            raise ValueError("Invalid numeric fields: " + label)
    numeric({k: i[k] for k in NUMBERS}, NUMBERS, "input")
    numeric(b, BALANCE, "balance")
    for key in NUMBERS:
        if i[key] != float(values[key]): raise ValueError("Input mismatch: " + key)
    equations = []
    def same(label, actual, expected, absolute=1e-6, relative=1e-9):
        if type(actual) not in (int, float) or not math.isfinite(actual) or not math.isfinite(expected) or not math.isclose(actual, expected, abs_tol=absolute, rel_tol=relative):
            raise ValueError("Cycle relation failed: " + label)
        equations.append(label)
    fits = database(); species = {s["id"]: s for s in fits["species"]}
    def elements(gas):
        mass = sum(y * species[s]["molar_mass_kg_per_kmol"] for s, y in gas["mole_fractions"].items())
        return [sum(y * species[s]["elements"].get(e, 0) for s, y in gas["mole_fractions"].items()) / mass for e in ("C", "H", "O")]
    def gas(state):
        keys = {"temperature_k", "pressure_pa", "molar_mass_kg_per_kmol", "gas_constant_j_per_kg_k", "cp_frozen_j_per_kg_k", "h_j_per_kg", "s_j_per_kg_k", "mole_fractions"}
        if not isinstance(state, dict) or set(state) != keys: raise ValueError("Invalid gas state schema")
        numeric({k: state[k] for k in keys - {"mole_fractions"}}, keys - {"mole_fractions"}, "gas")
        y = state["mole_fractions"]
        if set(y) != set(SPECIES) or any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in y.values()):
            raise ValueError("Invalid gas fractions")
        same("fractions sum", sum(y.values()), 1, 1e-12, 0)
        evaluated = mixture(y, state["temperature_k"], state["pressure_pa"], fits)
        for key, x in evaluated.items(): same("NASA9 " + key, state[key], x, 1e-6, 2e-11)
        same("mixture mass", state["molar_mass_kg_per_kmol"], fits["gas_constant_j_kmol_k"] / state["gas_constant_j_per_kg_k"], 1e-10)
        return state
    if i["total_mass_flow_kg_per_s"] <= 0 or i["overall_oxidizer_fuel_ratio"] <= 0 or not 0 < i["shaft_efficiency"] <= 1 or not 0 < i["turbine_efficiency"] <= 1:
        raise ValueError("Invalid flow/efficiency domain")
    tables, anchors = feed_reference(); anchor = {a["name"]: a for a in anchors}
    feeds = report["feed_states"]
    if set(feeds) != {"fuel", "oxidizer"}: raise ValueError("Invalid feed-state keys")
    for propellant in ("fuel", "oxidizer"):
        f = feeds[propellant]
        if set(f) != {"density_kg_per_m3", "inlet_h_j_per_kg", "basis", "elements_kmol_per_kg"} or f["basis"] != "NASA9_CEA_v334":
            raise ValueError("Invalid cycle-feed basis/schema")
        fluid = "Methane" if propellant == "fuel" else "Oxygen"
        expected = expected_report(fluid, i[propellant + "_temperature_k"], i[propellant + "_pump_inlet_pressure_pa"], tables)["results"] if i["feed_model"] == "methane_liquid_table" or propellant == "oxidizer" else None
        if i["feed_model"] == "methane_liquid_table":
            same("feed density", f["density_kg_per_m3"], expected["density_kg_per_m3"])
            same("feed h", f["inlet_h_j_per_kg"], expected["h_j_per_kg"])
            name = "CH4" if propellant == "fuel" else "O2"
            inventory = [species[name]["elements"].get(e, 0) / species[name]["molar_mass_kg_per_kmol"] for e in ("C", "H", "O")]
        elif i["feed_model"] == "rp1_assigned":
            a = anchor["RP-1" if propellant == "fuel" else "O2(L)"]
            if i[propellant + "_temperature_k"] != a["assigned_temperature_k"]: raise ValueError("RP-1 anchor temperature mismatch")
            same("assigned h", f["inlet_h_j_per_kg"], a["assigned_enthalpy_j_per_mol"] * 1000 / a["molar_mass_kg_per_kmol"])
            same("assumed RP1/table O2 density", f["density_kg_per_m3"], i["fuel_density_override_kg_per_m3"] if propellant == "fuel" else expected["density_kg_per_m3"])
            inventory = [a["elements"].get(e, 0) / a["molar_mass_kg_per_kmol"] for e in ("C", "H", "O")]
        else: raise ValueError("Unknown feed model")
        if not isinstance(f["elements_kmol_per_kg"], list) or len(f["elements_kmol_per_kg"]) != 3: raise ValueError("Invalid feed elements")
        for actual, expected_amount in zip(f["elements_kmol_per_kg"], inventory): same("feed element inventory", actual, expected_amount, 1e-12)
    mf = i["total_mass_flow_kg_per_s"] / (1 + i["overall_oxidizer_fuel_ratio"]); mo = i["total_mass_flow_kg_per_s"] - mf
    same("fuel flow", b["fuel_mass_flow_kg_per_s"], mf); same("oxidizer flow", b["oxidizer_mass_flow_kg_per_s"], mo)
    if set(report["pumps"]) != {"fuel", "oxidizer"}: raise ValueError("Invalid pumps")
    hpump = {}; power = 0.0
    for name, flow in (("fuel", mf), ("oxidizer", mo)):
        p = report["pumps"][name]; f = feeds[name]
        numeric(p, {"specific_work_j_per_kg", "shaft_power_w", "outlet_h_j_per_kg", "energy_residual_w"}, "pump")
        prefix = name + "_pump_"
        if f["density_kg_per_m3"] <= 0 or not 0 < i[prefix + "efficiency"] <= 1 or not 0 < i[prefix + "inlet_pressure_pa"] <= i[prefix + "outlet_pressure_pa"]:
            raise ValueError("Invalid pump domain")
        work = (i[prefix + "outlet_pressure_pa"] - i[prefix + "inlet_pressure_pa"]) / f["density_kg_per_m3"] / i[prefix + "efficiency"]
        hpump[name] = f["inlet_h_j_per_kg"] + work; power += flow * work
        same("pump work", p["specific_work_j_per_kg"], work); same("pump power", p["shaft_power_w"], flow * work)
        same("pump outlet h", p["outlet_h_j_per_kg"], hpump[name])
        same("pump residual identity", p["energy_residual_w"], flow * (p["outlet_h_j_per_kg"] - f["inlet_h_j_per_kg"]) - p["shaft_power_w"], 1e-7)
        if i[prefix + "outlet_pressure_pa"] - i["preburner_pressure_pa"] < i["pump_to_preburner_drop_pa"]:
            raise ValueError("Unreachable preburner pressure")
    for name in (("fuel",) if staged else ("fuel", "oxidizer")):
        if i[name + "_pump_outlet_pressure_pa"] - i["chamber_pressure_pa"] < i["pump_to_chamber_drop_pa"]: raise ValueError("Unreachable fresh chamber pressure")
    same("pump total", b["pump_power_w"], power)
    same("shaft demand", b["turbine_power_w"], (power + i["auxiliary_power_w"]) / i["shaft_efficiency"])
    t = report["turbine"]
    if set(t) != {"inlet", "isentropic_outlet", "outlet", "specific_work_j_per_kg", "efficiency_residual_j_per_kg", "entropy_generation_j_per_kg_k"}: raise ValueError("Invalid turbine schema")
    for station in ("inlet", "isentropic_outlet", "outlet"): gas(t[station])
    work = t["inlet"]["h_j_per_kg"] - t["outlet"]["h_j_per_kg"]
    same("turbine work", t["specific_work_j_per_kg"], work)
    same("turbine efficiency", work, i["turbine_efficiency"] * (t["inlet"]["h_j_per_kg"] - t["isentropic_outlet"]["h_j_per_kg"]), .01, 0)
    same("turbine isentropic s", t["isentropic_outlet"]["s_j_per_kg_k"], t["inlet"]["s_j_per_kg_k"], 1e-7, 0)
    same("turbine efficiency residual", t["efficiency_residual_j_per_kg"], work - i["turbine_efficiency"] * (t["inlet"]["h_j_per_kg"] - t["isentropic_outlet"]["h_j_per_kg"]), 1e-7, 0)
    same("turbine entropy generation", t["entropy_generation_j_per_kg_k"], t["outlet"]["s_j_per_kg_k"] - t["inlet"]["s_j_per_kg_k"], 1e-7, 0)
    if t["entropy_generation_j_per_kg_k"] < -1e-7: raise ValueError("Negative turbine entropy generation")
    for station in ("isentropic_outlet", "outlet"):
        if t[station]["mole_fractions"] != t["inlet"]["mole_fractions"]: raise ValueError("Unfrozen turbine")
        same("outlet pressure", t[station]["pressure_pa"], t["outlet"]["pressure_pa"])
    if staged:
        if i["turbine_outlet_pressure_pa"] != 0 or i["branch_area_ratio"] != 1 or i["branch_axial_projection"] != 0: raise ValueError("Inactive ORSC exhaust input")
        if not i["chamber_pressure_pa"] + i["return_pressure_drop_pa"] <= t["outlet"]["pressure_pa"] <= i["preburner_pressure_pa"]: raise ValueError("Unreachable return pressure")
        bf, bo = mo / i["preburner_oxidizer_fuel_ratio"], mo
    else:
        if i["return_pressure_drop_pa"] != 0: raise ValueError("GG return drop")
        same("GG outlet pressure", t["outlet"]["pressure_pa"], i["turbine_outlet_pressure_pa"])
        branch = (power + i["auxiliary_power_w"]) / i["shaft_efficiency"] / work if power + i["auxiliary_power_w"] else 0
        bf = branch / (1 + i["preburner_oxidizer_fuel_ratio"]); bo = branch - bf
    branch = bf + bo; returned = branch if staged else 0; external = 0 if staged else branch
    main = i["total_mass_flow_kg_per_s"] - external; fresh_fuel = mf - bf; fresh_oxidizer = mo - bo
    if branch > i["maximum_branch_fraction"] * i["total_mass_flow_kg_per_s"] or fresh_fuel <= 0 or (not staged and fresh_oxidizer <= 0): raise ValueError("Branch starvation/envelope violation")
    for key, expected in {"branch_mass_flow_kg_per_s": branch, "branch_fuel_mass_flow_kg_per_s": bf, "branch_oxidizer_mass_flow_kg_per_s": bo,
                          "returned_mass_flow_kg_per_s": returned, "external_mass_flow_kg_per_s": external, "main_mass_flow_kg_per_s": main,
                          "main_fuel_mass_flow_kg_per_s": fresh_fuel, "main_oxidizer_mass_flow_kg_per_s": fresh_oxidizer,
                          "main_oxidizer_fuel_ratio": i["overall_oxidizer_fuel_ratio"] if staged else fresh_oxidizer / fresh_fuel}.items(): same(key, b[key], expected)
    main_h = (fresh_fuel * hpump["fuel"] + fresh_oxidizer * hpump["oxidizer"] + returned * t["outlet"]["h_j_per_kg"]) / main
    ret_elements = elements(t["outlet"])
    main_inventory = [(fresh_fuel * feeds["fuel"]["elements_kmol_per_kg"][e] + fresh_oxidizer * feeds["oxidizer"]["elements_kmol_per_kg"][e] + returned * ret_elements[e]) / main for e in range(3)]
    pb_inventory = [(feeds["fuel"]["elements_kmol_per_kg"][e] + i["preburner_oxidizer_fuel_ratio"] * feeds["oxidizer"]["elements_kmol_per_kg"][e]) / (1 + i["preburner_oxidizer_fuel_ratio"]) for e in range(3)]
    if staged and pb_inventory[2] <= 2 * pb_inventory[0] + pb_inventory[1] / 2: raise ValueError("Not oxygen rich")
    pb_h = (hpump["fuel"] + i["preburner_oxidizer_fuel_ratio"] * hpump["oxidizer"]) / (1 + i["preburner_oxidizer_fuel_ratio"])
    for name, inventory, h, pressure in (("preburner", pb_inventory, pb_h, i["preburner_pressure_pa"]), ("chamber", main_inventory, main_h, i["chamber_pressure_pa"])):
        hp = report[name]
        if set(hp) != {"gas", "diagnostics"}: raise ValueError("Invalid HP schema")
        gas(hp["gas"]); same("HP pressure", hp["gas"]["pressure_pa"], pressure)
        if not 1000 <= hp["gas"]["temperature_k"] <= 6000: raise ValueError("HP temperature out of domain")
        same("HP Q=0", hp["gas"]["h_j_per_kg"], h, .01, 0)
        diagnostics = hp["diagnostics"]
        base_keys = {"element_relative_residual", "equilibrium_residual", "enthalpy_residual_j_per_kg", "equilibrium_iterations", "hp_iterations"}
        if set(diagnostics) not in (base_keys, base_keys | {"graphite_activity"}): raise ValueError("Invalid HP diagnostics")
        if "graphite_activity" in diagnostics and not 0 <= diagnostics["graphite_activity"] <= 1: raise ValueError("HP graphite activity outside gas-only domain")
        same("HP h residual identity", diagnostics["enthalpy_residual_j_per_kg"], hp["gas"]["h_j_per_kg"] - h, 1e-7, 0)
        if not 0 <= diagnostics["equilibrium_residual"] <= 1e-10 or any(abs(x) > 2e-10 for x in diagnostics["element_relative_residual"]): raise ValueError("HP chemical residual limit")
        if len(diagnostics["element_relative_residual"]) != 3 or any(type(diagnostics[k]) is not int or not 0 <= diagnostics[k] <= 10000 for k in ("hp_iterations", "equilibrium_iterations")): raise ValueError("HP diagnostics types")
        for e, actual in enumerate(elements(hp["gas"])): same("HP elements", actual, inventory[e], 1e-11)
    if report["preburner"]["gas"] != t["inlet"]: raise ValueError("Preburner/turbine mismatch")
    if set(report["mixing"]) != {"h_j_per_kg", "elements_kmol_per_kg"} or len(report["mixing"]["elements_kmol_per_kg"]) != 3: raise ValueError("Invalid mixing schema")
    same("return-mixing h", report["mixing"]["h_j_per_kg"], main_h)
    for actual, expected in zip(report["mixing"]["elements_kmol_per_kg"], main_inventory): same("return-mixing elements", actual, expected, 1e-12)
    exit_h = 0.0
    for label, flow, area, chamber, projection in (("main_nozzle", main, i["main_area_ratio"], report["chamber"]["gas"], 1),
                                                  ("branch_nozzle", external, i["branch_area_ratio"], t["outlet"], i["branch_axial_projection"])):
        n = report[label]
        prefix = "main" if label == "main_nozzle" else "branch"
        if flow == 0:
            if n is not None: raise ValueError("Inactive branch has a nozzle")
            same("inactive thrust", b["branch_thrust_n"], 0, 0, 0); same("inactive area", b["branch_throat_area_m2"], 0, 0, 0); continue
        if set(n) != {"chamber", "nozzle"} or n["chamber"] != chamber: raise ValueError("Nozzle chamber mismatch")
        n = n["nozzle"]
        if set(n) != {"freeze_location", "throat", "exit", "cstar_m_per_s", "vacuum_effective_velocity_m_per_s", "effective_velocity_m_per_s", "thrust_coefficient", "continuity_relative_residual", "sonic_relative_residual"} or n["freeze_location"] != "chamber": raise ValueError("Invalid frozen nozzle schema")
        for station in ("throat", "exit"):
            s = n[station]; gas(s["gas"])
            numeric({k: v for k, v in s.items() if k != "gas"}, {"velocity_m_per_s", "mach", "mass_flux_kg_per_m2_s", "energy_residual_j_per_kg", "entropy_residual_j_per_kg_k"}, "station")
            if s["gas"]["mole_fractions"] != chamber["mole_fractions"]: raise ValueError("Unfrozen nozzle")
            h_res = s["gas"]["h_j_per_kg"] + .5 * s["velocity_m_per_s"]**2 - chamber["h_j_per_kg"]
            same("nozzle total h", h_res, 0, 1e-4, 0); same("nozzle h residual", s["energy_residual_j_per_kg"], h_res, 1e-7, 0)
            s_res = s["gas"]["s_j_per_kg_k"] - chamber["s_j_per_kg_k"]
            same("nozzle total s", s_res, 0, 1e-7, 0); same("nozzle s residual", s["entropy_residual_j_per_kg_k"], s_res, 1e-7, 0)
            rho = s["gas"]["pressure_pa"] / (s["gas"]["gas_constant_j_per_kg_k"] * s["gas"]["temperature_k"])
            same("nozzle flux", s["mass_flux_kg_per_m2_s"], rho * s["velocity_m_per_s"])
            cp, r = s["gas"]["cp_frozen_j_per_kg_k"], s["gas"]["gas_constant_j_per_kg_k"]
            same("nozzle Mach", s["mach"], s["velocity_m_per_s"] / math.sqrt(cp / (cp - r) * r * s["gas"]["temperature_k"]), 1e-10)
        throat, exit_ = n["throat"], n["exit"]
        if i["ambient_pressure_pa"] > exit_["gas"]["pressure_pa"] * (1 + 1e-10): raise ValueError("Unsupported nozzle back pressure")
        same("sonic throat", throat["mach"], 1, 1e-8)
        continuity = exit_["mass_flux_kg_per_m2_s"] * area / throat["mass_flux_kg_per_m2_s"] - 1
        same("area/flux", continuity, 0, 1e-8, 0); same("continuity residual", n["continuity_relative_residual"], continuity, 1e-12, 0)
        same("sonic residual", n["sonic_relative_residual"], throat["mach"] - 1, 1e-8, 0)
        velocity = exit_["velocity_m_per_s"] + (exit_["gas"]["pressure_pa"] - i["ambient_pressure_pa"]) * area / throat["mass_flux_kg_per_m2_s"]
        same("effective velocity", n["effective_velocity_m_per_s"], velocity)
        same("vacuum velocity", n["vacuum_effective_velocity_m_per_s"], velocity + i["ambient_pressure_pa"] * area / throat["mass_flux_kg_per_m2_s"])
        same("cstar", n["cstar_m_per_s"], chamber["pressure_pa"] / throat["mass_flux_kg_per_m2_s"])
        same("thrust coefficient", n["thrust_coefficient"], velocity / n["cstar_m_per_s"])
        same("throat area", b[prefix + "_throat_area_m2"], flow / throat["mass_flux_kg_per_m2_s"])
        same("nozzle thrust", b[prefix + "_thrust_n"], flow * velocity * projection)
        exit_h += flow * (exit_["gas"]["h_j_per_kg"] + .5 * exit_["velocity_m_per_s"]**2)
    same("total thrust", b["total_thrust_n"], b["main_thrust_n"] + b["branch_thrust_n"])
    same("main effective velocity", b["main_effective_velocity_m_per_s"], b["main_thrust_n"] / main)
    same("engine effective velocity", b["engine_effective_velocity_m_per_s"], b["total_thrust_n"] / i["total_mass_flow_kg_per_s"])
    same("engine Isp total feed", b["engine_specific_impulse_s"], b["total_thrust_n"] / i["total_mass_flow_kg_per_s"] / 9.80665)
    hin = mf * feeds["fuel"]["inlet_h_j_per_kg"] + mo * feeds["oxidizer"]["inlet_h_j_per_kg"]
    loss = (1 - i["shaft_efficiency"]) * branch * work
    same("mechanical loss", b["mechanical_loss_w"], loss); same("inlet H", b["inlet_enthalpy_rate_w"], hin); same("exit H", b["exit_total_enthalpy_rate_w"], exit_h)
    same("zero preburner heat", b["generator_heat_w"], 0, 0, 0); same("zero chamber heat", b["chamber_heat_w"], 0, 0, 0)
    for key, residual, scale in (("mass", i["total_mass_flow_kg_per_s"] - main - external, i["total_mass_flow_kg_per_s"]),
                                 ("shaft", i["shaft_efficiency"] * branch * work - power - i["auxiliary_power_w"], max(1, power + i["auxiliary_power_w"])),
                                 ("energy", hin - exit_h - i["auxiliary_power_w"] - loss, max(1, abs(hin) + abs(exit_h) + i["auxiliary_power_w"] + loss))):
        name = key + ("_residual_kg_per_s" if key == "mass" else "_residual_w")
        same("residual identity " + key, b[name], residual, 1e-6)
        same("scaled residual " + key, b[key + "_relative_residual"], residual / scale, 1e-12)
    if abs(b["mass_relative_residual"]) > 1e-12 or abs(b["shaft_relative_residual"]) > 2e-8 or abs(b["energy_residual_w"]) > .1 + .025 * i["total_mass_flow_kg_per_s"] + 2e-8 * (power + i["auxiliary_power_w"]): raise ValueError("Conservation limit exceeded")
    d = report["diagnostics"]
    if set(d) != {"preburner_enthalpy_residual_w", "chamber_enthalpy_residual_w", "exit_element_relative_residual", "turbine_pressure_iterations"}: raise ValueError("Invalid cycle diagnostics")
    same("preburner h residual W", d["preburner_enthalpy_residual_w"], branch * report["preburner"]["diagnostics"]["enthalpy_residual_j_per_kg"], 1e-6)
    same("chamber h residual W", d["chamber_enthalpy_residual_w"], main * report["chamber"]["diagnostics"]["enthalpy_residual_j_per_kg"], 1e-6)
    if type(d["turbine_pressure_iterations"]) is not int or not 0 <= d["turbine_pressure_iterations"] <= 80 or len(d["exit_element_relative_residual"]) != 3: raise ValueError("Invalid iteration/element diagnostics")
    for e, amount in enumerate(elements(report["chamber"]["gas"])):
        incoming = mf * feeds["fuel"]["elements_kmol_per_kg"][e] + mo * feeds["oxidizer"]["elements_kmol_per_kg"][e]
        residual = (main * amount + external * ret_elements[e] - incoming) / incoming
        same("exit element residual", d["exit_element_relative_residual"][e], residual, 1e-12)
        same("exit element conservation", residual, 0, 1e-8, 0)
    if not isinstance(report["limitations"], list) or len(report["limitations"]) < 4 or any(not isinstance(s, str) or not s for s in report["limitations"]): raise ValueError("Missing limitations")
    return len(equations)


def cea_card(name, pressure, inventory, h, expanded=False):
    carbon = inventory[0]
    formula = f"C 1 H {inventory[1]/carbon:.17g} O {inventory[2]/carbon:.17g}"
    return (f"problem case={name} hp p,bar={pressure/1e5:.17g}\nreactants\n"
            f" name=MIXED_FEED {formula} wt%=100 t,k=298.15 h,j/mole={h/(1000*carbon):.17g}\n"
            + ("" if expanded else "only " + " ".join(SPECIES) + "\n") + "output siunits trace=1.e-7\nend\n")


def run_logged(command, folder, name, code=0):
    run = subprocess.run([str(x) for x in command], cwd=folder, capture_output=True, text=True, encoding="utf-8", timeout=60, env=subprocess_env())
    atomic_text(folder / (name + "-stdout.txt"), run.stdout); atomic_text(folder / (name + "-stderr.txt"), run.stderr)
    if run.returncode != code or (code == 0 and run.stderr) or (code != 0 and (run.stdout or not run.stderr)):
        raise ValueError("Unexpected execution protocol: " + name)
    return run


def source_identity(root=ROOT):
    """Capture Git identity before creating the archive inside the worktree."""
    head = git(root, "rev-parse", "HEAD", check=True).stdout.strip()
    dirty = bool(git(root, "status", "--porcelain").stdout)
    return head, dirty


def verify(folder):
    manifest = read_json(folder / "manifest.json")
    if manifest.get("status") != "PASS" or manifest.get("kind") != "adiabatic_cycle_research" or manifest.get("model") != MODEL:
        raise ValueError("Unsuccessful/incompatible engine cycle archive")
    for f in manifest["files"]:
        if digest(local_path(folder, f["path"])) != f["sha256"]: raise ValueError("Archive hash mismatch: " + f["path"])
    reports = {}
    for entry in manifest["runs"]:
        name = entry["id"]; text = (folder / (name + ".ini")).read_text(encoding="utf-8")
        if entry["exit_code"] == 0:
            report = strict_json((folder / (name + "-stdout.txt")).read_text(encoding="utf-8"))
            if validate(report, text) != entry["relations"]: raise ValueError("Archive relation count mismatch")
            reports[name] = report
        elif (folder / (name + "-stdout.txt")).read_bytes() or not (folder / (name + "-stderr.txt")).read_bytes():
            raise ValueError("Invalid archived refusal streams")
    for entry in manifest["cea_runs"]:
        if parse_cea((folder / (entry["id"] + ".out")).read_bytes()) != entry["summary"]: raise ValueError("CEA summary mismatch")
    return dict(runs=len(manifest["runs"]), cea_runs=len(manifest["cea_runs"]), relations=sum(x.get("relations", 0) for x in manifest["runs"]))


def archive(folder):
    if folder.exists(): raise ValueError("Archive destination already exists; choose a new ID")
    build_path = verified_build(ROOT, "Release", require_tests=True); build = read_json(build_path)
    binary = local_path(ROOT, build["application"]["path"])
    cea_ref = check_reference(); source = ROOT / "build/reference/cea-v3.3.4"
    source_head, source_dirty = source_identity(ROOT)
    cea = ROOT / "build/reference/cea-build-v3.3.4/source/cea.exe"; db = cea.parent.parent
    if digest(cea) != cea_ref["executable_sha256"] or git(source, "rev-parse", "HEAD", check=True).stdout.strip() != COMMIT or digest(source / "data/thermo.inp") != THERMO_SHA:
        raise ValueError("Pinned CEA binary/source mismatch")
    folder.mkdir(parents=True, exist_ok=False)
    manifest = dict(kind="adiabatic_cycle_research", schema_version=1, status="RUNNING", model=MODEL, started_at=now(),
                    source_head=source_head, source_dirty=source_dirty,
                    c_binary_sha256=digest(binary), build_manifest_sha256=digest(build_path), cea_commit=COMMIT,
                    cea_binary_sha256=digest(cea), thermo_sha256=THERMO_SHA, runs=[], cea_runs=[], comparisons=[], files=[],
                    scope="Assumed single-shaft GG/ORSC; CEA validates chemical method on shared data, not real engines or independent experiment.")
    atomic_json(folder / "manifest.json", manifest)
    try:
        shutil.copy2(build_path, folder / "build-manifest.json"); shutil.copy2(build_path.parent / "test-report.json", folder / "test-report.json")
        for name in ("thermo.lib", "trans.lib"):
            if digest(db / name) != cea_ref["compiled_database_hashes"][name]: raise ValueError("CEA database mismatch")
            shutil.copy2(db / name, folder / name)
        reports = {}
        for name in CASES:
            text = (ROOT / f"cases/vehicles/{name}.ini").read_text(encoding="utf-8")
            atomic_text(folder / (name + ".ini"), text)
            run = run_logged([binary, "cycle", "adiabatic", name + ".ini"], folder, name)
            report = strict_json(run.stdout); relations = validate(report, text); reports[name] = report
            manifest["runs"].append(dict(id=name, exit_code=0, relations=relations))
        # Refusals exercise physical reachability, allocation and HP domains.
        for name, base, old, new, token in (
            ("reject_return_pressure", "cz10b_first_stage1", "return_pressure_drop_pa=1000000", "return_pressure_drop_pa=12000000", "out_of_domain"),
            ("reject_return_power", "cz10b_first_stage1", "auxiliary_power_w=10000", "auxiliary_power_w=100000000", "out_of_domain"),
            ("reject_low_preburner_temperature", "cz10b_first_stage1", "preburner_oxidizer_fuel_ratio=30", "preburner_oxidizer_fuel_ratio=200", "not_bracketed"),
            ("reject_starvation", "zq3_y1_stage1", "maximum_branch_fraction=0.20", "maximum_branch_fraction=0.00001", "out_of_domain"),
        ):
            text = (ROOT / f"cases/vehicles/{base}.ini").read_text(encoding="utf-8").replace(old, new)
            atomic_text(folder / (name + ".ini"), text)
            run = run_logged([binary, "cycle", "adiabatic", name + ".ini"], folder, name, 4)
            if not run.stderr.startswith(token + ":"): raise ValueError("Unexpected rejection status")
            manifest["runs"].append(dict(id=name, exit_code=4, expected_status=token))
        for case_name in ("zq3_y1_stage1", "cz10b_first_stage1", "cz10b_first_stage2_orsc"):
            report = reports[case_name]; i = report["inputs"]; pumps = report["pumps"]; feeds = report["feed_states"]
            pb = i["preburner_oxidizer_fuel_ratio"]
            pb_inventory = [(feeds["fuel"]["elements_kmol_per_kg"][e] + pb * feeds["oxidizer"]["elements_kmol_per_kg"][e]) / (1 + pb) for e in range(3)]
            pb_h = (pumps["fuel"]["outlet_h_j_per_kg"] + pb * pumps["oxidizer"]["outlet_h_j_per_kg"]) / (1 + pb)
            for state, inventory, h, pressure in (("preburner", pb_inventory, pb_h, i["preburner_pressure_pa"]),
                                                ("chamber", report["mixing"]["elements_kmol_per_kg"], report["mixing"]["h_j_per_kg"], i["chamber_pressure_pa"])):
                for expanded in (False, True):
                    name = case_name + "_" + state + ("_expanded" if expanded else "_nine")
                    atomic_text(folder / (name + ".inp"), cea_card(name, pressure, inventory, h, expanded))
                    run_logged([cea, "-v", name], folder, name + "-cea")
                    summary = parse_cea((folder / (name + ".out")).read_bytes())
                    if summary["status"] != "COMPLETE": raise ValueError("CEA state incomplete: " + name)
                    temperature = summary["rows"]["temperature_k"][0]
                    difference = report[state]["gas"]["temperature_k"] - temperature
                    if not expanded and abs(difference) > .06: raise ValueError("C/CEA HP temperature mismatch: " + name)
                    carbon = summary["mole_fractions"].get("C(gr)", [0])[0]
                    manifest["cea_runs"].append(dict(id=name, summary=summary))
                    manifest["comparisons"].append(dict(id=name, c_temperature_k=report[state]["gas"]["temperature_k"], cea_temperature_k=temperature,
                                                         c_minus_cea_k=difference, carbon_mole_fraction=carbon, product_set="expanded" if expanded else "nine"))
        # Runtime databases are developer dependencies; archive raw cards/logs,
        # database hashes instead of shipping the large compiled libraries.
        for name in ("thermo.lib", "trans.lib"): (folder / name).unlink()
        manifest.update(status="PASS", finished_at=now())
        manifest["files"] = [dict(path=p.name, sha256=digest(p)) for p in sorted(folder.iterdir()) if p.name != "manifest.json"]
        atomic_json(folder / "manifest.json", manifest)
        verify(folder)
    except Exception as exc:
        manifest.update(status="FAIL", error=str(exc)); raise
    finally:
        manifest["finished_at"] = now(); atomic_json(folder / "manifest.json", manifest)
    return verify(folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    for name in ("archive", "verify"): sub.add_parser(name).add_argument("path")
    args = parser.parse_args()
    try:
        path = local_path(ROOT, args.path)
        print(archive(path) if args.command == "archive" else verify(path))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr); sys.exit(1)
