"""Pinned offline liquid references, chemical enthalpy alignment and table checks."""
from __future__ import annotations

import argparse
import bisect
from datetime import datetime
import json
import math
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import uuid

from adiabatic_study import typed_equal
from liquid_eos import close, coefficients_equal, evaluate, ideal, nasa9
from pipeline import strict_json
from projectlib import ROOT, atomic_json, digest, git, local_path, now, read_json
from thermo_data import CEA_GAS_CONSTANT, COMMIT, RAW, SOURCE_HASHES, parse_selected

DATASET = "coolprop710-cea334-liquid-molar-v1"
VERSION = "7.1.0"
REVISION = "2a1c5d7231011ed1c20067b8528150398d12c841"
WHEEL = "coolprop-7.1.0-cp313-cp313-win_amd64.whl"
WHEEL_SHA = "9846aabfcc7c72d8fb8f1bd02f6c58125640b6e8e4321487c4746ede7a4590da"
PYD_SHA = "9ee9ceaa56fb330712149cb7179ad7e7cb9bec9caf602d1b89054b548d831932"
SOURCE_IDS = {
    "Methane": "F02_coolprop_methane_7_1_0",
    "Oxygen": "F03_coolprop_oxygen_7_1_0",
}
FLUID_SPECIES = {"Methane": "CH4", "Oxygen": "O2"}
FIXED_SOURCES = {
    "F02_coolprop_methane_7_1_0": "5cb01cbafb6da28da358f3fd1c0985be39c99cb9aef8b872ff2b5807a6a79dff",
    "F03_coolprop_oxygen_7_1_0": "7ed571aa8753b7ed8a421f625fb4c896e17d17ec506bcd264642e5d88f34eadc",
    "F04_coolprop_license_7_1_0": "9bf835333ef602af4cb19338b9f9d43671e174fa029b00280e9bdba6ea4719b2",
    "F07_coolprop_bibliography_7_1_0": "84d767376da3313fb59cf593adea07ba7b1c79e41f76835b34b4b4606c21aec6",
}
SCOPE = (
    "Assumed pure CH4/O2 single-phase liquid-like HEOS states and offline bilinear reference. "
    "Molar enthalpy aligned to CEA/NASA9 ideal gas at 298.15 K; residual enthalpy retained. "
    "No flight inlet identification, full EOS port, pump, combustion or cycle closure."
)
TEMPERATURES = {"Methane": list(range(100, 141, 2)), "Oxygen": list(range(80, 111, 2))}
PRESSURES = [1e6, 2e6, 4e6, 6e6, 8e6, 10e6, 12e6, 14e6, 16e6, 18e6, 20e6]
IDEAL_TEMPERATURES = [200.0, 250.0, 298.15, 350.0, 400.0, 500.0, 600.0]
T_REF = 298.15
LIMITS = dict(critical_temperature_fraction=0.9, saturation_pressure_factor=1.2,
              saturation_pressure_margin_pa=50000.0, max_density_relative_error=0.0005,
              max_molar_enthalpy_error_j_per_mol=5.0)
PACKAGE = dict(name="CoolProp", version=VERSION, gitrevision=REVISION, wheel=WHEEL,
               wheel_sha256=WHEEL_SHA, extension_sha256=PYD_SHA, license="MIT",
               index_url="https://pypi.org/pypi/CoolProp/7.1.0/json")
MANIFEST_KEYS = {
    "schema_version", "kind", "dataset_id", "status", "scope", "started_at", "finished_at",
    "source_head", "source_dirty", "package", "source_files", "run", "counts", "summary", "files",
}


def design():
    return dict(dataset_id=DATASET, input_role="assumed_research_not_engine_fact",
                backend="HEOS", temperatures_k=TEMPERATURES, pressures_pa=PRESSURES,
                ideal_temperatures_k=IDEAL_TEMPERATURES, reference_temperature_k=T_REF,
                limits=LIMITS, interpolation="bilinear_T_P", cea_commit=COMMIT,
                mass_conversion="CEA species molar mass; EOS density keeps EOS mass convention")


def sources():
    index = {entry["id"]: entry for entry in read_json(ROOT/"调研/原始来源/来源文件索引.json")}
    result = []
    for name, expected in FIXED_SOURCES.items():
        entry = index[name]
        path = local_path(ROOT, "调研/原始来源/"+entry["file"])
        if entry["sha256"] != expected or digest(path) != expected:
            raise ValueError("Fixed liquid source changed: " + name)
        result.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=expected,
                           url=entry["url"], id=name))
    for name, expected in SOURCE_HASHES.items():
        path = ROOT/RAW/name
        if digest(path) != expected:
            raise ValueError("Fixed CEA source changed: " + name)
        result.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=expected,
                           id="CEA-"+name, url="https://github.com/nasa/cea/tree/v3.3.4/data"))
    return result


def fluid_data():
    return {name: read_json(ROOT/"调研/原始来源"/(identity+".txt"))
            for name, identity in SOURCE_IDS.items()}


def coordinates(fluid):
    ts = TEMPERATURES[fluid]
    nodes = [(float(t), p) for t in ts for p in PRESSURES]
    interior = [(float(t+u)/2, (p+q)/2)
                for t, u in zip(ts, ts[1:]) for p, q in zip(PRESSURES, PRESSURES[1:])]
    # Additional non-centred quarter-cell samples expose errors missed at a midpoint.
    interior += [(t+(u-t)*0.25, p+(q-p)*0.75)
                 for t, u in zip(ts, ts[1:]) for p, q in zip(PRESSURES, PRESSURES[1:])]
    return nodes, interior


def queries(fluid, boundary):
    low, high = TEMPERATURES[fluid][0], TEMPERATURES[fluid][-1]
    critical = boundary["reducing_temperature_k"]
    sat = next(row for row in boundary["saturation"] if row["temperature_k"] == float(high))
    return [
        dict(id="valid_lower", fluid=fluid, temperature_k=float(low), pressure_pa=PRESSURES[0]),
        dict(id="valid_upper", fluid=fluid, temperature_k=float(high), pressure_pa=PRESSURES[-1]),
        dict(id="below_temperature", fluid=fluid, temperature_k=low-0.01, pressure_pa=1e6),
        dict(id="above_temperature", fluid=fluid, temperature_k=high+0.01, pressure_pa=1e6),
        dict(id="below_pressure", fluid=fluid, temperature_k=float(low), pressure_pa=999999.0),
        dict(id="above_pressure", fluid=fluid, temperature_k=float(low), pressure_pa=20000001.0),
        dict(id="saturation", fluid=fluid, temperature_k=float(high), pressure_pa=sat["pressure_pa"]),
        dict(id="near_saturation", fluid=fluid, temperature_k=float(high), pressure_pa=sat["pressure_pa"]*1.01),
        dict(id="gas_side", fluid=fluid, temperature_k=float(high), pressure_pa=sat["pressure_pa"]*0.8),
        dict(id="critical_neighbourhood", fluid=fluid, temperature_k=critical*0.95, pressure_pa=5e6),
        dict(id="two_phase", fluid=fluid, temperature_k=float(low), pressure_pa=1e6, vapor_quality=0.5),
        dict(id="unknown_fluid", fluid="RP-1", temperature_k=float(low), pressure_pa=1e6),
    ]


def interpolation(nodes, fluid, query):
    """Research-side contract for the future C17 adapter, with no extrapolation."""
    if not isinstance(query, dict) or set(query)-{"id", "fluid", "temperature_k", "pressure_pa", "vapor_quality"}:
        raise ValueError("Invalid liquid query schema")
    t, p = query.get("temperature_k"), query.get("pressure_pa")
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in (t, p)):
        raise ValueError("Invalid liquid temperature/pressure")
    if query.get("fluid") != fluid or "vapor_quality" in query:
        return dict(status="out_of_domain")
    ts, ps = TEMPERATURES[fluid], PRESSURES
    if not ts[0] <= t <= ts[-1] or not ps[0] <= p <= ps[-1]:
        return dict(status="out_of_domain")
    i, j = min(bisect.bisect_right(ts, t)-1, len(ts)-2), min(bisect.bisect_right(ps, p)-1, len(ps)-2)
    a, b = (t-ts[i])/(ts[i+1]-ts[i]), (p-ps[j])/(ps[j+1]-ps[j])
    rows = [nodes[x*len(ps)+y] for x, y in ((i,j), (i,j+1), (i+1,j), (i+1,j+1))]
    weights = [(1-a)*(1-b), (1-a)*b, a*(1-b), a*b]
    return dict(status="ok", **{key: sum(w*r[key] for w, r in zip(weights, rows))
                               for key in ("density_kg_per_m3", "aligned_h_j_per_mol")})


def load_runtime():
    runtime = ROOT/"build/tooling/coolprop710"
    wheel = ROOT/"build/tooling/coolprop-wheels"/WHEEL
    binary = runtime/"CoolProp/CoolProp.cp313-win_amd64.pyd"
    if (not wheel.is_file() or digest(wheel) != WHEEL_SHA or not binary.is_file()
        or digest(binary) != PYD_SHA):
        raise ValueError("Install the pinned Windows CPython 3.13 CoolProp wheel under build/tooling")
    sys.path.insert(0, str(runtime))
    import CoolProp
    import CoolProp.CoolProp as cp
    if (CoolProp.__version__ != VERSION or CoolProp.__gitrevision__ != REVISION
        or Path(cp.__file__).resolve() != binary.resolve()):
        raise ValueError("CoolProp runtime identity mismatch")
    return CoolProp, cp


def worker(input_path):
    typed_equal(read_json(input_path), design(), "liquid input")
    sources()
    module, cp = load_runtime()
    output = dict(package=PACKAGE, environment=dict(
        python_version=platform.python_version(), platform=platform.platform(),
        architecture=platform.machine(), python_executable=sys.executable,
        python_sha256=digest(Path(sys.executable)), extension_sha256=PYD_SHA), fluids={})
    for fluid, source in fluid_data().items():
        state = module.AbstractState("HEOS", fluid)
        exported = cp.get_fluid_param_string(fluid, "JSON")
        coefficients_equal(json.loads(exported)[0]["EOS"], source["EOS"])
        reducing = source["EOS"][0]["STATES"]["reducing"]
        boundary = dict(reducing_temperature_k=reducing["T"], reducing_pressure_pa=reducing["p"],
                        runtime_critical_temperature_k=state.T_critical(),
                        runtime_critical_pressure_pa=state.p_critical(), saturation=[])
        saturation_t = sorted(set(map(float, TEMPERATURES[fluid])) |
                              {t for t, _ in coordinates(fluid)[1]})
        for t in saturation_t:
            state.update(cp.QT_INPUTS, 0, t)
            liquid = dict(rhomolar=state.rhomolar(), hmolar=state.hmolar(), gmolar=state.gibbsmolar())
            pressure = state.p()
            state.update(cp.QT_INPUTS, 1, t)
            vapor = dict(rhomolar=state.rhomolar(), hmolar=state.hmolar(), gmolar=state.gibbsmolar())
            boundary["saturation"].append(dict(temperature_k=t, pressure_pa=pressure,
                                                liquid=liquid, vapor=vapor))
        def point(t, p):
            state.update(cp.PT_INPUTS, p, t)
            return dict(temperature_k=t, pressure_pa=p, phase_code=int(state.phase()),
                        phase_name=cp.PhaseSI("T", t, "P", p, fluid),
                        rhomolar=state.rhomolar(), density_kg_per_m3=state.rhomass(),
                        h_j_per_mol=state.hmolar(), h_residual_j_per_mol=state.hmolar_residual(),
                        h0_j_per_mol=state.gas_constant()*t*(1+state.tau()*state.dalpha0_dTau()),
                        cp0_j_per_mol_k=state.cp0molar(),
                        high_level_density_kg_per_m3=cp.PropsSI("Dmass", "T", t, "P", p, fluid),
                        high_level_h_j_per_mol=cp.PropsSI("Hmolar", "T", t, "P", p, fluid))
        nodes, interior = coordinates(fluid)
        ideals = []
        for t in IDEAL_TEMPERATURES:
            state.update(cp.PT_INPUTS, 100000, t)
            ideals.append(dict(temperature_k=t,
                               h0_j_per_mol=state.gas_constant()*t*(1+state.tau()*state.dalpha0_dTau()),
                               cp0_j_per_mol_k=state.cp0molar(),
                               finite_pressure_h_j_per_mol=state.hmolar(),
                               finite_pressure_h_residual_j_per_mol=state.hmolar_residual()))
        output["fluids"][fluid] = dict(exported_json=exported, boundary=boundary, ideals=ideals,
                                       nodes=[point(t,p) for t,p in nodes],
                                       interior=[point(t,p) for t,p in interior])
    print(json.dumps(output, ensure_ascii=False, allow_nan=False))


def check_point(row, eos, t, p, saturation):
    expected_keys = {
        "temperature_k", "pressure_pa", "phase_code", "phase_name", "rhomolar",
        "density_kg_per_m3", "h_j_per_mol", "h_residual_j_per_mol", "h0_j_per_mol",
        "cp0_j_per_mol_k", "high_level_density_kg_per_m3", "high_level_h_j_per_mol",
    }
    if not isinstance(row, dict) or set(row) != expected_keys:
        raise ValueError("Liquid state schema mismatch")
    typed_equal([row["temperature_k"], row["pressure_pa"]], [t,p], "liquid coordinates")
    if (type(row["phase_code"]) is not int or
        (row["phase_code"], row["phase_name"]) not in ((0,"liquid"), (3,"supercritical_liquid"))):
        raise ValueError("Reference is not single-phase liquid-like")
    if row["phase_code"] != (0 if p < eos["STATES"]["reducing"]["p"] else 3):
        raise ValueError("Reference phase label disagrees with pressure region")
    if not t < eos["STATES"]["reducing"]["T"]*LIMITS["critical_temperature_fraction"]:
        raise ValueError("Reference enters critical neighbourhood")
    sat_pressure = saturation["pressure_pa"]
    if p < max(sat_pressure*LIMITS["saturation_pressure_factor"],
               sat_pressure+LIMITS["saturation_pressure_margin_pa"]):
        raise ValueError("Reference too close to saturation")
    for key, value in row.items():
        if key not in ("phase_code", "phase_name"):
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Nonfinite or nonnumeric liquid reference")
    if row["rhomolar"] <= 0 or row["density_kg_per_m3"] <= 0:
        raise ValueError("Nonpositive liquid density")
    if row["rhomolar"] < saturation["liquid"]["rhomolar"]:
        raise ValueError("Reference density lies below the saturated liquid branch")
    independent = evaluate(eos, t, row["rhomolar"])
    for key in ("pressure_pa", "h0_j_per_mol", "h_residual_j_per_mol", "h_j_per_mol", "cp0_j_per_mol_k"):
        close(row[key], independent[key], key)
    if independent["dp_drhomolar_j_per_mol"] <= 0:
        raise ValueError("Mechanically unstable reference branch")
    close(row["density_kg_per_m3"], row["rhomolar"]*eos["molar_mass"], "EOS density mass")
    close(row["density_kg_per_m3"], row["high_level_density_kg_per_m3"], "high/low density")
    close(row["h_j_per_mol"], row["high_level_h_j_per_mol"], "high/low h")
    return independent


def analyse(raw):
    if not isinstance(raw, dict) or set(raw) != {"package","environment","fluids"}:
        raise ValueError("Liquid raw output schema mismatch")
    typed_equal(raw["package"], PACKAGE, "liquid package")
    env = raw["environment"]
    if (not isinstance(env, dict) or set(env) != {
            "python_version","platform","architecture","python_executable","python_sha256","extension_sha256"}
        or any(not isinstance(v,str) or not v for v in env.values())
        or not env["python_version"].startswith("3.13.") or env["architecture"] != "AMD64"
        or not env["platform"].startswith("Windows")
        or not re.fullmatch("[0-9a-f]{64}", env["python_sha256"]) or env["extension_sha256"] != PYD_SHA):
        raise ValueError("Liquid runtime environment mismatch")
    if not isinstance(raw["fluids"], dict) or set(raw["fluids"]) != set(SOURCE_IDS):
        raise ValueError("Liquid fluid inventory mismatch")
    species = {r["id"]:r for r in parse_selected((ROOT/RAW/"thermo.inp").read_text(encoding="ascii"))}
    tables, summary = {}, {}
    for fluid, source in fluid_data().items():
        eos, record = source["EOS"][0], raw["fluids"][fluid]
        if not isinstance(record, dict) or set(record) != {"exported_json","boundary","ideals","nodes","interior"}:
            raise ValueError("Liquid fluid record schema mismatch")
        if not isinstance(record["exported_json"], str):
            raise ValueError("Exported fluid JSON type mismatch")
        exported = strict_json(record["exported_json"])
        if not isinstance(exported,list) or len(exported) != 1:
            raise ValueError("Exported fluid JSON shape mismatch")
        coefficients_equal(exported[0]["EOS"], source["EOS"])
        boundary = record["boundary"]
        if not isinstance(boundary, dict) or set(boundary) != {
            "reducing_temperature_k","reducing_pressure_pa","runtime_critical_temperature_k",
            "runtime_critical_pressure_pa","saturation"}:
            raise ValueError("Liquid saturation boundary schema mismatch")
        reducing = eos["STATES"]["reducing"]
        typed_equal(boundary["reducing_temperature_k"], reducing["T"], "reducing T")
        typed_equal(boundary["reducing_pressure_pa"], reducing["p"], "reducing P")
        # Runtime critical solution and the EOS reducing state need not be identical.
        close(boundary["runtime_critical_temperature_k"], reducing["T"], "critical T", rel=0.001, absolute=0)
        close(boundary["runtime_critical_pressure_pa"], reducing["p"], "critical P", rel=0.001, absolute=0)
        expected_ts = sorted(set(map(float,TEMPERATURES[fluid])) |
                             {t for t,_ in coordinates(fluid)[1]})
        saturations = boundary["saturation"]
        if not isinstance(saturations,list) or len(saturations) != len(expected_ts):
            raise ValueError("Liquid saturation count mismatch")
        sat_map = {}
        for sat, t in zip(saturations,expected_ts):
            if not isinstance(sat,dict) or set(sat) != {"temperature_k","pressure_pa","liquid","vapor"}:
                raise ValueError("Liquid saturation record mismatch")
            typed_equal(sat["temperature_k"], t, "saturation temperature")
            if type(sat["pressure_pa"]) not in (int,float) or not math.isfinite(sat["pressure_pa"]) or sat["pressure_pa"] <= 0:
                raise ValueError("Invalid saturation pressure")
            sat_map[t] = sat
            evaluated = []
            for phase in ("liquid","vapor"):
                row = sat[phase]
                if (not isinstance(row,dict) or set(row) != {"rhomolar","hmolar","gmolar"}
                    or any(type(v) not in (int,float) or not math.isfinite(v) for v in row.values())
                    or row["rhomolar"] <= 0):
                    raise ValueError("Invalid saturated phase")
                other = evaluate(eos,t,row["rhomolar"])
                close(other["pressure_pa"], sat["pressure_pa"], "saturation EOS pressure", rel=2e-7, absolute=0.005)
                close(row["hmolar"], other["h_j_per_mol"], "saturation enthalpy")
                close(row["gmolar"], other["g_j_per_mol"], "saturation Gibbs")
                if other["dp_drhomolar_j_per_mol"] <= 0:
                    raise ValueError("Unstable saturation root")
                evaluated.append(other)
            close(evaluated[0]["g_j_per_mol"], evaluated[1]["g_j_per_mol"], "coexistence Gibbs", rel=0, absolute=0.002)
            if sat["liquid"]["rhomolar"] <= sat["vapor"]["rhomolar"] or sat["vapor"]["hmolar"] <= sat["liquid"]["hmolar"]:
                raise ValueError("Saturation branch/latent heat ordering failed")
        if any(a["pressure_pa"] >= b["pressure_pa"] for a,b in zip(saturations,saturations[1:])):
            raise ValueError("Saturation pressure does not rise over the reference interval")
        ideal_rows = record["ideals"]
        if not isinstance(ideal_rows,list) or len(ideal_rows) != len(IDEAL_TEMPERATURES):
            raise ValueError("Ideal reference count mismatch")
        nasa = species[FLUID_SPECIES[fluid]]
        h_ref_eos, h_ref_nasa = ideal(eos,T_REF)["h0_j_per_mol"], nasa9(nasa,T_REF)["h_j_per_mol"]
        offset = h_ref_nasa-h_ref_eos
        ideal_comparison = []
        for row,t in zip(ideal_rows,IDEAL_TEMPERATURES):
            if not isinstance(row,dict) or set(row) != {
                "temperature_k","h0_j_per_mol","cp0_j_per_mol_k",
                "finite_pressure_h_j_per_mol","finite_pressure_h_residual_j_per_mol"}:
                raise ValueError("Ideal reference schema mismatch")
            typed_equal(row["temperature_k"],t,"ideal temperature")
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in row.values()):
                raise ValueError("Invalid ideal reference number")
            base, chemical = ideal(eos,t), nasa9(nasa,t)
            close(row["h0_j_per_mol"],base["h0_j_per_mol"],"ideal h0")
            close(row["cp0_j_per_mol_k"],base["cp0_j_per_mol_k"],"ideal cp0")
            close(row["finite_pressure_h_j_per_mol"]-row["finite_pressure_h_residual_j_per_mol"],
                  row["h0_j_per_mol"],"finite-pressure decomposition")
            # This gas root is checked independently. A common-mode change of h
            # and h_residual must not alter the reported finite-pressure bias.
            density = 100000/(eos["gas_constant"]*t)
            lower, upper = density*0.25, density*4
            if not evaluate(eos,t,lower)["pressure_pa"] < 100000 < evaluate(eos,t,upper)["pressure_pa"]:
                raise ValueError("Ideal reference gas density is not bracketed")
            for _ in range(70):
                middle = (lower+upper)/2
                if evaluate(eos,t,middle)["pressure_pa"] < 100000:
                    lower = middle
                else:
                    upper = middle
            gas_reference = evaluate(eos,t,(lower+upper)/2)
            close(row["finite_pressure_h_j_per_mol"],gas_reference["h_j_per_mol"],"finite-pressure h")
            close(row["finite_pressure_h_residual_j_per_mol"],
                  gas_reference["h_residual_j_per_mol"],"finite-pressure h_residual")
            ideal_comparison.append(dict(
                temperature_k=t, eos_cp0_j_per_mol_k=row["cp0_j_per_mol_k"],
                nasa9_cp_j_per_mol_k=chemical["cp_j_per_mol_k"],
                cp_difference_j_per_mol_k=row["cp0_j_per_mol_k"]-chemical["cp_j_per_mol_k"],
                aligned_ideal_h_difference_j_per_mol=row["h0_j_per_mol"]+offset-chemical["h_j_per_mol"]))
        converted = []
        node_xy, interior_xy = coordinates(fluid)
        for name, xy in (("nodes",node_xy),("interior",interior_xy)):
            rows = record[name]
            if not isinstance(rows,list) or len(rows) != len(xy):
                raise ValueError("Liquid node/interior count mismatch")
            for row,(t,p) in zip(rows,xy):
                check_point(row,eos,t,p,sat_map[t])
                if name == "nodes":
                    aligned = row["h_j_per_mol"]+offset
                    converted.append(dict(temperature_k=t, pressure_pa=p,
                                          density_kg_per_m3=row["density_kg_per_m3"],
                                          aligned_h_j_per_mol=aligned,
                                          aligned_h_j_per_kg=aligned*1000/nasa["molar_mass_kg_per_kmol"]))
        errors = []
        for row in record["interior"]:
            value = interpolation(converted,fluid,dict(fluid=fluid,temperature_k=row["temperature_k"],pressure_pa=row["pressure_pa"]))
            errors.append(dict(
                temperature_k=row["temperature_k"], pressure_pa=row["pressure_pa"],
                density_relative_error=(value["density_kg_per_m3"]/row["density_kg_per_m3"]-1),
                enthalpy_error_j_per_mol=value["aligned_h_j_per_mol"]-row["h_j_per_mol"]-offset))
        rho_error = max(abs(e["density_relative_error"]) for e in errors)
        h_error = max(abs(e["enthalpy_error_j_per_mol"]) for e in errors)
        if rho_error > LIMITS["max_density_relative_error"] or h_error > LIMITS["max_molar_enthalpy_error_j_per_mol"]:
            raise ValueError("Liquid interpolation error exceeds research threshold")
        query_results = [dict(input=q,output=interpolation(converted,fluid,q)) for q in queries(fluid,boundary)]
        if [q["output"]["status"] for q in query_results] != ["ok","ok"]+["out_of_domain"]*10:
            raise ValueError("Liquid rejection contract mismatch")
        tables[fluid] = dict(fluid=fluid, nodes=converted, interpolation_errors=errors,
                             queries=query_results, molar_mass_cea_kg_per_mol=nasa["molar_mass_kg_per_kmol"]/1000,
                             molar_mass_eos_kg_per_mol=eos["molar_mass"],
                             aligned_offset_j_per_mol=offset, ideal_comparison=ideal_comparison)
        summary[fluid] = dict(
            node_count=len(converted), interior_count=len(errors), saturation_count=len(saturations),
            max_density_relative_error=rho_error, max_enthalpy_error_j_per_mol=h_error,
            max_cp0_difference_j_per_mol_k=max(abs(e["cp_difference_j_per_mol_k"]) for e in ideal_comparison),
            max_aligned_ideal_h_difference_j_per_mol=max(abs(e["aligned_ideal_h_difference_j_per_mol"]) for e in ideal_comparison),
            reference_eos_h0_j_per_mol=h_ref_eos, reference_nasa9_h_j_per_mol=h_ref_nasa,
            aligned_offset_j_per_mol=offset, eos_gas_constant_j_per_mol_k=eos["gas_constant"],
            nasa9_gas_constant_j_per_mol_k=CEA_GAS_CONSTANT/1000,
            molar_mass_relative_difference=eos["molar_mass"]/(nasa["molar_mass_kg_per_kmol"]/1000)-1,
            finite_pressure_anchor_bias_j_per_mol=ideal_rows[2]["finite_pressure_h_residual_j_per_mol"],
            minimum_pressure_saturation_ratio=min(p/sat_map[t]["pressure_pa"] for t,p in node_xy+interior_xy))
    return tables, summary


def read_strict(path):
    return strict_json(path.read_text(encoding="utf-8"))


def verify(folder):
    record = read_strict(folder/"manifest.json")
    if (not isinstance(record,dict) or set(record) != MANIFEST_KEYS
        or type(record["schema_version"]) is not int or record["schema_version"] != 1
        or record["kind"] != "liquid-feed-reference" or record["dataset_id"] != DATASET
        or record["scope"] != SCOPE or record["status"] != "PASS"
        or type(record["source_dirty"]) is not bool
        or not isinstance(record["source_head"],str) or not re.fullmatch("[0-9a-f]{40}",record["source_head"])):
        raise ValueError("Liquid archive identity mismatch")
    if any(not isinstance(record[k],str) for k in ("started_at","finished_at")):
        raise ValueError("Liquid archive timestamp type mismatch")
    start,finish = [datetime.fromisoformat(record[k]) for k in ("started_at","finished_at")]
    if start.utcoffset() is None or finish.utcoffset() is None or finish < start:
        raise ValueError("Liquid archive timestamp order/timezone mismatch")
    typed_equal(record["package"],PACKAGE,"liquid package")
    typed_equal(record["source_files"],sources(),"liquid sources")
    run = record["run"]
    if not isinstance(run,dict) or set(run) != {"command","exit_code"} or type(run["exit_code"]) is not int:
        raise ValueError("Liquid run schema mismatch")
    typed_equal(run, dict(command=["python","tools/liquid_feed.py","_worker","input.json"],exit_code=0),"liquid run")
    required = {"input.json","raw-output.json","stderr.txt","tables.json"}
    files = record["files"]
    if ({p.name for p in folder.iterdir()} != required | {"manifest.json"}
        or any(not p.is_file() for p in folder.iterdir()) or not isinstance(files,list)
        or len(files) != len(required)):
        raise ValueError("Liquid archive inventory mismatch")
    if (any(not isinstance(f,dict) or set(f) != {"path","sha256"}
            or not isinstance(f["path"],str) or not isinstance(f["sha256"],str)
            or not re.fullmatch("[0-9a-f]{64}",f["sha256"]) for f in files)
        or {f["path"] for f in files} != required):
        raise ValueError("Liquid archive file declarations mismatch")
    for item in files:
        if digest(folder/item["path"]) != item["sha256"]:
            raise ValueError("Liquid archive hash mismatch")
    if (folder/"stderr.txt").read_bytes():
        raise ValueError("Liquid worker stderr is nonempty")
    typed_equal(read_strict(folder/"input.json"),design(),"liquid input")
    tables,summary = analyse(read_strict(folder/"raw-output.json"))
    typed_equal(read_strict(folder/"tables.json"),tables,"liquid table")
    typed_equal(record["summary"],summary,"liquid summary")
    counts = dict(nodes=sum(r["node_count"] for r in summary.values()),
                  interior=sum(r["interior_count"] for r in summary.values()),
                  saturation=sum(r["saturation_count"] for r in summary.values()),
                  ideal=2*len(IDEAL_TEMPERATURES),queries=24)
    typed_equal(record["counts"],counts,"liquid counts")
    return counts


def archive(destination):
    target = local_path(ROOT,destination)
    if target.exists():
        raise FileExistsError("Liquid reference destination already exists")
    folder = ROOT/"build/liquid-feed"/uuid.uuid4().hex
    folder.mkdir(parents=True)
    record = dict(schema_version=1,kind="liquid-feed-reference",dataset_id=DATASET,
                  status="RUNNING",scope=SCOPE,started_at=now())
    atomic_json(folder/"manifest.json",record)
    try:
        record.update(source_head=git(ROOT,"rev-parse","HEAD",check=True).stdout.strip(),
                      source_dirty=bool(git(ROOT,"status","--porcelain",check=True).stdout.strip()),
                      package=PACKAGE,source_files=sources())
        atomic_json(folder/"input.json",design())
        command = [sys.executable,str(ROOT/"tools/liquid_feed.py"),"_worker",str(folder/"input.json")]
        completed = subprocess.run(command,cwd=ROOT,capture_output=True,timeout=120,check=False)
        (folder/"raw-output.json").write_bytes(completed.stdout)
        (folder/"stderr.txt").write_bytes(completed.stderr)
        record["run"] = dict(command=["python","tools/liquid_feed.py","_worker","input.json"],exit_code=completed.returncode)
        if completed.returncode or completed.stderr:
            raise ValueError("Liquid worker failed; raw streams retained in "+str(folder))
        tables,summary = analyse(read_strict(folder/"raw-output.json"))
        atomic_json(folder/"tables.json",tables)
        record.update(status="PASS",summary=summary,counts=dict(
            nodes=sum(r["node_count"] for r in summary.values()),
            interior=sum(r["interior_count"] for r in summary.values()),
            saturation=sum(r["saturation_count"] for r in summary.values()),
            ideal=2*len(IDEAL_TEMPERATURES),queries=24))
        record["files"] = [dict(path=p,sha256=digest(folder/p)) for p in
                           ("input.json","raw-output.json","stderr.txt","tables.json")]
    except Exception as exc:
        record.update(status="FAIL",error=str(exc))
        raise
    finally:
        record["finished_at"] = now()
        atomic_json(folder/"manifest.json",record)
    verify(folder)
    target.parent.mkdir(parents=True,exist_ok=True)
    # Publish only an independently checked complete archive; failed runs stay in build.
    staged = target.with_name(target.name+"-"+uuid.uuid4().hex+".tmp")
    shutil.copytree(folder,staged)
    verify(staged)
    staged.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command",required=True)
    for name in ("archive","verify","_worker"):
        sub.add_parser(name).add_argument("path")
    args = parser.parse_args()
    if args.command == "_worker":
        worker(Path(args.path))
    elif args.command == "archive":
        print(archive(args.path))
    else:
        print(json.dumps(verify(local_path(ROOT,args.path))))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)
