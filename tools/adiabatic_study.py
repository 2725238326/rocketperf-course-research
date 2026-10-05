"""Fixed-geometry gas-inlet response: C17 solves; Python archives and checks."""

from __future__ import annotations

import argparse
from datetime import datetime
from html import escape
import math
import re
import shutil
import subprocess
import sys
import uuid

from adiabatic_inlet import inlet_value, read_output
from cea_reference import COMMIT, THERMO_SHA, check_reference, parse_output
from combustion_reference import compare_report
from pipeline import verified_build, verify_test_report
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json
from research_frozen_reference import SOURCE_HASHES
from research_tp_reference import run_logged

SCOPE = (
    "Restricted NASA9 CH4/O2 gas HP, Q=0, chamber-frozen single nozzle. "
    "Each A10/A40 family fixes Pc=10 MPa, At=0.01 m2, Ae and vacuum. "
    "Not liquid properties, heating-system/full-cycle closure or flight performance."
)
BASIS = "nasa9-cea-v3.3.4"
TEMPERATURES = (200.0, 298.15, 450.0, 600.0, 900.0)
CONDITIONS = (
    ("base", 298.15, 298.15, 3.4),
    ("both_200", 200.0, 200.0, 3.4),
    ("both_450", 450.0, 450.0, 3.4),
    ("both_600", 600.0, 600.0, 3.4),
    ("both_900", 900.0, 900.0, 3.4),
    ("fuel_600", 600.0, 298.15, 3.4),
    ("oxidizer_600", 298.15, 600.0, 3.4),
    ("of_2_6", 298.15, 298.15, 2.6),
    ("of_3_0", 298.15, 298.15, 3.0),
    ("of_3_8", 298.15, 298.15, 3.8),
    ("of_4_2", 298.15, 298.15, 4.2),
    ("of_5_0", 298.15, 298.15, 5.0),
)
DESIGN = dict(pressure_pa=1e7, throat_area_m2=0.01, area_ratios=[10, 40],
              ambient_pressure_pa=0.0, feed_phase="gas", enthalpy_basis=BASIS)
KEYS = {
    "schema_version", "kind", "status", "scope", "started_at", "finished_at",
    "source_head", "source_dirty", "design", "conditions", "c_binary_sha256",
    "build_manifest_sha256", "test_report_sha256", "cea_commit", "cea_version",
    "cea_binary_sha256", "thermo_source_sha256", "compiled_database_hashes",
    "rocket_source_hashes", "runs", "cea_runs", "comparisons", "responses", "files",
}
CEA_SUFFIXES = (".inp", ".out", "-cea-stdout.txt", "-cea-stderr.txt")


def typed_equal(actual, expected, label):
    """Exact deterministic snapshots; bool must never masquerade as 0 or 1."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError("Study object mismatch: " + label)
        for key in expected:
            typed_equal(actual[key], expected[key], label + "." + key)
    elif isinstance(expected, (list, tuple)):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError("Study list mismatch: " + label)
        for index, value in enumerate(expected):
            typed_equal(actual[index], value, label + "." + str(index))
    elif type(expected) in (int, float):
        if type(actual) not in (int, float) or not math.isfinite(actual) or actual != expected:
            raise ValueError("Study number mismatch: " + label)
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError("Study value mismatch: " + label)


def conditions():
    return [dict(id=n, fuel_temperature_k=tf, oxidizer_temperature_k=to,
                 oxidizer_fuel_mass_ratio=of) for n, tf, to, of in CONDITIONS]


def property_name(species, temperature):
    return species.lower() + "_" + format(temperature, "g").replace(".", "_")


def properties(folder):
    return {(s, t): inlet_value(folder, property_name(s, t), s, t)
            for s in ("CH4", "O2") for t in TEMPERATURES}


def supplied(h, tf, to, of, area=None):
    inputs = dict(feed_phase="gas", enthalpy_basis=BASIS, pressure_pa=1e7,
                  oxidizer_fuel_mass_ratio=of, fuel_h_j_per_kg=h[("CH4", tf)],
                  oxidizer_h_j_per_kg=h[("O2", to)])
    if area is not None:
        inputs.update(area_ratio=area, ambient_pressure_pa=0.0, throat_area_m2=0.01)
    return inputs


def arguments(inputs, mode):
    keys = ["pressure_pa", "oxidizer_fuel_mass_ratio", "fuel_h_j_per_kg", "oxidizer_h_j_per_kg"]
    if mode == "frozen-h":
        keys += ["area_ratio", "ambient_pressure_pa", "throat_area_m2"]
    return ["combustion", mode, inputs["enthalpy_basis"], inputs["feed_phase"],
            *[format(inputs[k], ".17g") for k in keys]]


def recipes(h):
    result = [(property_name(s, t), ["thermo", s, format(t, ".17g")], 0)
              for s in ("CH4", "O2") for t in TEMPERATURES]
    for name, tf, to, of in CONDITIONS:
        result.append((name + "_hp", arguments(supplied(h, tf, to, of), "hp-h"), 0))
        for area in DESIGN["area_ratios"]:
            result.append((name + "_A" + str(area),
                           arguments(supplied(h, tf, to, of, area), "frozen-h"), 0))
    base = supplied(h, 298.15, 298.15, 3.4)
    for name, changed, mode in [
        ("reject_liquid", dict(feed_phase="liquid"), "hp-h"),
        ("reject_basis", dict(enthalpy_basis="arbitrary-zero"), "hp-h"),
        ("reject_of", dict(oxidizer_fuel_mass_ratio=20.01), "hp-h"),
        ("reject_h", dict(fuel_h_j_per_kg=-1e308), "hp-h"),
        ("reject_backpressure", dict(area_ratio=40, ambient_pressure_pa=100000,
                                     throat_area_m2=0.01), "frozen-h"),
    ]:
        result.append((name, arguments(dict(base, **changed), mode), 4))
    return result


def case_card(name, tf, to, of):
    return (
        "! Gas-feed HP, infinite-area chamber, chamber-frozen nfz=1; not liquid feed.\n"
        f"problem case={name} rocket frozen nfz=1 p,bar=100 o/f={of:.17g} supar=10,40\n"
        f"reactants\n fuel=CH4 wt%=100 t,k={tf:.17g}\n oxid=O2 wt%=100 t,k={to:.17g}\n"
        "only H2 O2 H2O CO CO2 CH4 H O OH\noutput siunits trace=1.e-8\nend\n"
    )


def evaluate(folder):
    h = properties(folder)
    comparisons, responses = {}, []
    for name, tf, to, of in CONDITIONS:
        reference = {"summary": parse_output((folder / (name + ".out")).read_bytes(),
                                             rocket=True, frozen=True)}
        hp = read_output(folder, name + "_hp")
        comparisons[name + "_hp"] = compare_report(
            hp, reference, "hp-h", expected_inputs=supplied(h, tf, to, of))
        for area in DESIGN["area_ratios"]:
            point = name + "_A" + str(area)
            report = read_output(folder, point)
            comparisons[point] = compare_report(
                report, reference, "frozen-h", area, expected_inputs=supplied(h, tf, to, of, area))
            if report["chamber"] != hp["chamber"] or report["diagnostics"] != hp["diagnostics"]:
                raise ValueError("Fixed nozzle changed HP chamber: " + point)
            responses.append(dict(
                id=point, condition=name, area_ratio=area,
                inlet_mixture_h_j_per_kg=hp["boundary"]["inlet_mixture_h_j_per_kg"],
                chamber_temperature_k=hp["chamber"]["temperature_k"],
                mole_fractions=hp["chamber"]["mole_fractions"],
                cstar_m_per_s=report["nozzle"]["cstar_m_per_s"],
                throat_mass_flux_kg_per_m2_s=report["nozzle"]["throat"]["mass_flux_kg_per_m2_s"],
                exit_temperature_k=report["nozzle"]["exit"]["gas"]["temperature_k"],
                exit_pressure_pa=report["nozzle"]["exit"]["gas"]["pressure_pa"],
                mass_flow_kg_per_s=report["geometry"]["mass_flow_kg_per_s"],
                thrust_n=report["geometry"]["thrust_n"],
                specific_impulse_s=report["geometry"]["specific_impulse_s"],
            ))
    return comparisons, responses


def required_files():
    files = {"build-manifest.json", "test-report.json"} | set(SOURCE_HASHES)
    placeholder = {(s, t): 0 for s in ("CH4", "O2") for t in TEMPERATURES}
    files |= {name + suffix for name, *_ in recipes(placeholder)
              for suffix in ("-stdout.txt", "-stderr.txt")}
    files |= {name + suffix for name, *_ in CONDITIONS for suffix in CEA_SUFFIXES}
    return files


def verify(folder):
    record = read_json(folder / "manifest.json")
    fixed = check_reference()
    if (not isinstance(record, dict) or set(record) != KEYS
        or type(record["schema_version"]) is not int or record["schema_version"] != 1
        or record["kind"] != "adiabatic-inlet-response" or record["status"] != "PASS"
        or record["scope"] != SCOPE or type(record["source_dirty"]) is not bool
        or not isinstance(record["source_head"], str)
        or not re.fullmatch("[0-9a-f]{40}", record["source_head"])):
        raise ValueError("Study manifest identity mismatch")
    try:
        start, finish = [datetime.fromisoformat(record[k]) for k in ("started_at", "finished_at")]
        if start.utcoffset() is None or finish.utcoffset() is None or finish < start:
            raise ValueError("Timestamp order/timezone")
    except (ValueError, TypeError) as exc:
        raise ValueError("Study timestamp mismatch") from exc
    typed_equal(record["design"], DESIGN, "design")
    typed_equal(record["conditions"], conditions(), "conditions")
    expected_identity = dict(cea_commit=COMMIT, cea_version="3.3.4",
                             cea_binary_sha256=fixed["executable_sha256"],
                             thermo_source_sha256=THERMO_SHA,
                             compiled_database_hashes=fixed["compiled_database_hashes"],
                             rocket_source_hashes=SOURCE_HASHES)
    for key, value in expected_identity.items():
        typed_equal(record[key], value, key)
    required = required_files()
    if ({p.name for p in folder.iterdir()} != required | {"manifest.json"}
        or any(not p.is_file() for p in folder.iterdir())
        or not isinstance(record["files"], list) or len(record["files"]) != len(required)):
        raise ValueError("Study archive inventory mismatch")
    entries = record["files"]
    if (any(not isinstance(f, dict) or set(f) != {"path", "sha256"}
            or not isinstance(f["path"], str) or not isinstance(f["sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", f["sha256"]) for f in entries)
        or {f["path"] for f in entries} != required):
        raise ValueError("Study file list mismatch")
    for item in entries:
        if digest(folder / item["path"]) != item["sha256"]:
            raise ValueError("Study archive bytes changed")
    for name, identity in SOURCE_HASHES.items():
        if digest(folder / name) != identity:
            raise ValueError("Pinned rocket source changed")
    build = read_json(folder / "build-manifest.json")
    tests = read_json(folder / "test-report.json")
    verify_test_report(tests, build, digest(folder / "build-manifest.json"))
    for key, identity in dict(c_binary_sha256=build["application"]["sha256"],
                              build_manifest_sha256=digest(folder / "build-manifest.json"),
                              test_report_sha256=digest(folder / "test-report.json")).items():
        if record[key] != identity:
            raise ValueError("Study C build/test identity mismatch")
    h = properties(folder)
    expected = recipes(h)
    if not isinstance(record["runs"], list) or len(record["runs"]) != len(expected):
        raise ValueError("Study C run count mismatch")
    for run, (name, args, code) in zip(record["runs"], expected):
        if (not isinstance(run, dict) or set(run) != {"id", "arguments", "exit_code"}
            or type(run["exit_code"]) is not int):
            raise ValueError("Study C run schema mismatch")
        typed_equal(run, dict(id=name, arguments=args, exit_code=code), "C recipe")
        stdout = (folder / (name + "-stdout.txt")).read_text(encoding="utf-8")
        stderr = (folder / (name + "-stderr.txt")).read_text(encoding="utf-8")
        if (code == 0 and stderr) or (code != 0 and (stdout or not stderr.startswith("out_of_domain:"))):
            raise ValueError("Study C success/failure protocol mismatch")
    if not isinstance(record["cea_runs"], list) or len(record["cea_runs"]) != len(CONDITIONS):
        raise ValueError("Study CEA run count mismatch")
    for run, (name, tf, to, of) in zip(record["cea_runs"], CONDITIONS):
        if (not isinstance(run, dict) or set(run) != {"id", "arguments", "exit_code"}
            or type(run["exit_code"]) is not int):
            raise ValueError("Study CEA run schema mismatch")
        typed_equal(run, dict(id=name, arguments=["-v", name], exit_code=0), "CEA recipe")
        if (folder / (name + ".inp")).read_text(encoding="utf-8") != case_card(name, tf, to, of):
            raise ValueError("Study CEA card/condition mismatch")
        log = (folder / (name + "-cea-stdout.txt")).read_text(encoding="utf-8")
        if ("CEA Version: 3.3.4" not in log or "WARNING" in log or "ERROR" in log
            or (folder / (name + "-cea-stderr.txt")).read_bytes()):
            raise ValueError("Study CEA diagnostics/version mismatch")
    comparisons, responses = evaluate(folder)
    typed_equal(record["comparisons"], comparisons, "comparisons")
    typed_equal(record["responses"], responses, "responses")
    return len(expected), len(CONDITIONS), len(responses)


def archive(destination):
    target = local_path(ROOT, destination)
    if target.exists():
        raise FileExistsError("Study destination already exists")
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
        or any(digest(source / "source" / name) != identity for name, identity in SOURCE_HASHES.items())):
        raise ValueError("Pinned CEA source/database/binary changed")
    folder = ROOT / "build/adiabatic-study" / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    record = dict(
        schema_version=1, kind="adiabatic-inlet-response", status="RUNNING", scope=SCOPE,
        started_at=now(), source_head=git(ROOT, "rev-parse", "HEAD", check=True).stdout.strip(),
        source_dirty=bool(git(ROOT, "status", "--porcelain", check=True).stdout.strip()),
        design=DESIGN, conditions=conditions(), c_binary_sha256=digest(executable),
        cea_commit=COMMIT, cea_version="3.3.4", cea_binary_sha256=digest(cea),
        thermo_source_sha256=THERMO_SHA, compiled_database_hashes=fixed["compiled_database_hashes"],
        rocket_source_hashes=SOURCE_HASHES, runs=[], cea_runs=[],
    )
    atomic_json(folder / "manifest.json", record)
    try:
        shutil.copy2(build_path, folder / "build-manifest.json")
        shutil.copy2(build_path.parent / "test-report.json", folder / "test-report.json")
        for name in SOURCE_HASHES:
            shutil.copy2(source / "source" / name, folder / name)
        for name in ("thermo.lib", "trans.lib"):
            original = ROOT / "build/reference/cea-build-v3.3.4" / name
            if digest(original) != fixed["compiled_database_hashes"][name]:
                raise ValueError("Compiled CEA database changed")
            shutil.copy2(original, folder / name)
        def run_c(name, args, code):
            run = run_logged([str(executable), *args], ROOT, folder / (name + "-stdout.txt"),
                             folder / (name + "-stderr.txt"), 15)
            if run.returncode != code:
                raise ValueError("Unexpected C exit: " + name)
            record["runs"].append(dict(id=name, arguments=args, exit_code=run.returncode))
        placeholder = {(s, t): 0 for s in ("CH4", "O2") for t in TEMPERATURES}
        for name, args, code in recipes(placeholder)[:10]:
            run_c(name, args, code)
        h = properties(folder)
        for name, args, code in recipes(h)[10:]:
            run_c(name, args, code)
        for name, tf, to, of in CONDITIONS:
            atomic_text(folder / (name + ".inp"), case_card(name, tf, to, of))
            run = run_logged([str(cea), "-v", name], folder,
                             folder / (name + "-cea-stdout.txt"), folder / (name + "-cea-stderr.txt"), 30)
            if run.returncode:
                raise ValueError("Unexpected CEA exit: " + name)
            record["cea_runs"].append(dict(id=name, arguments=["-v", name], exit_code=run.returncode))
        if digest(executable) != record["c_binary_sha256"] or digest(cea) != record["cea_binary_sha256"]:
            raise ValueError("Executable changed during study")
        record["comparisons"], record["responses"] = evaluate(folder)
        record.update(status="PASS", build_manifest_sha256=digest(folder / "build-manifest.json"),
                      test_report_sha256=digest(folder / "test-report.json"))
        record["files"] = [{"path": name, "sha256": digest(folder / name)}
                           for name in sorted(required_files())]
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


def response_svg(folder):
    """Normalize saved C measurements for display, never interpolate a solver."""
    verify(folder)
    record = read_json(folder / "manifest.json")
    points = {p["id"]: p for p in record["responses"]}
    heating = [(n, tf) for n, tf, to, of in CONDITIONS if tf == to and of == 3.4]
    heating.sort(key=lambda item: item[1])
    ratios = [(n, of) for n, tf, to, of in CONDITIONS if tf == to == 298.15]
    ratios.sort(key=lambda item: item[1])
    metrics = [
        ("chamber_temperature_k", "燃烧室温度变化 (%)", -8, 4, 4),
        ("mass_flow_kg_per_s", "阻塞质量流量变化 (%)", -4, 8, 4),
        ("specific_impulse_s", "单喷管真空比冲变化 (%)", -8, 4, 4),
        ("thrust_n", "单喷管真空推力变化 (%)", -1, 0.5, 0.5),
    ]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1520" height="1340" viewBox="0 0 1520 1340" role="img" aria-labelledby="title desc">',
        '<title id="title">固定几何气态入口焓与混合比响应</title>',
        '<desc id="desc">八个面板分别展示入口温度与混合比对温度、流量、比冲、推力的影响；每个值来自已验证的C17离散计算。</desc>',
        '<rect width="1520" height="1340" fill="#f7f9fc"/>',
        '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#203248} .tick{font-size:15px;fill:#52657a} .label{font-size:17px} .panel{font-size:20px;font-weight:600}</style>',
    ]
    def text(x, y, value, size=18, **attrs):
        attributes = " ".join(f'{k.replace("_", "-")}="{escape(str(v), quote=True)}"' for k, v in attrs.items())
        svg.append(f'<text x="{x}" y="{y}" font-size="{size}" {attributes}>{escape(value)}</text>')
    text(46, 48, "固定尺寸之后，升温与推力并不一起增长", 30, font_weight="700")
    text(46, 83, "CH₄/O₂ 受限气相 HP · 燃烧室 Q = 0 · Pc = 10 MPa · At = 0.01 m² · 真空", 19)
    text(46, 113, "变化基准：两种入口均为 298.15 K、O/F = 3.4；A10 与 A40 分别保留各自出口面积。", 17)
    text(118, 162, "同时改变两种气态入口温度（O/F 固定）", 22, font_weight="600")
    text(858, 162, "改变 O/F（两种气态入口温度固定）", 22, font_weight="600")
    colors = {10: "#166d9b", 40: "#b45c28"}
    for row, (field, label, lower, upper, step) in enumerate(metrics):
        for col, data in enumerate((heating, ratios)):
            card_x, card_y = 36 + col * 746, 183 + row * 262
            svg.append(f'<rect x="{card_x}" y="{card_y}" width="712" height="244" rx="12" fill="#fff" stroke="#d7e1ec"/>')
            text(card_x + 20, card_y + 28, label, 20, font_weight="600")
            left, top, width, height = card_x + 82, card_y + 49, 592, 140
            xlo, xhi = data[0][1], data[-1][1]
            def xy(x, y):
                return left + (x-xlo)/(xhi-xlo)*width, top + (upper-y)/(upper-lower)*height
            ticks = round((upper - lower) / step)
            for index in range(ticks + 1):
                value = lower + index * step
                _, y = xy(xlo, value)
                style = 'stroke="#708297" stroke-dasharray="5 5"' if value == 0 else 'stroke="#e1e7ef"'
                svg.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left+width}" y2="{y:.2f}" {style}/>')
                text(left - 12, round(y + 5, 2), format(value, "g"), 15, text_anchor="end", **{"class": "tick"})
            for _, value in data:
                x, _ = xy(value, 0)
                svg.append(f'<line x1="{x:.2f}" y1="{top+height}" x2="{x:.2f}" y2="{top+height+5}" stroke="#7b8ca0"/>')
                text(round(x, 2), top + height + 24, format(value, "g"), 15, text_anchor="middle", **{"class": "tick"})
            text(left + width / 2, card_y + 229, "气态入口温度 (K)" if col == 0 else "氧 / 燃质量比 O/F", 16, text_anchor="middle")
            for area in ([10] if row < 2 else [10, 40]):
                baseline = points["base_A" + str(area)][field]
                coordinates = [xy(x, 100 * (points[n + "_A" + str(area)][field]/baseline - 1)) for n, x in data]
                if any(y < top - 1e-8 or y > top + height + 1e-8 for _, y in coordinates):
                    raise ValueError("Response plot scale does not cover saved data")
                path = " ".join(("M" if index == 0 else "L") + f"{x:.2f},{y:.2f}"
                                for index, (x, y) in enumerate(coordinates))
                svg.append(f'<path d="{path}" fill="none" stroke="{colors[area]}" stroke-width="2.5"/>')
                for x, y in coordinates:
                    svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{colors[area]}" stroke="#fff" stroke-width="1.4"/>')
            if row < 2:
                text(card_x + 500, card_y + 28, "A10 / A40 相同", 16)
            else:
                for area, offset in [(10, 475), (40, 581)]:
                    svg.append(f'<line x1="{card_x+offset}" y1="{card_y+22}" x2="{card_x+offset+21}" y2="{card_y+22}" stroke="{colors[area]}" stroke-width="3"/>')
                    text(card_x + offset + 28, card_y + 28, "A" + str(area), 16)
    text(46, 1269, "离散情景，不是连续最优解；连线只作导读。各行纵轴尺度不同，零线为各自固定几何基准。", 17)
    text(46, 1302, "NASA9 CEA v3.3.4 同源物性对照；不包含预热装置代价、液态物性、整机循环、冷却或分离。", 17)
    text(46, 1328, "C17 研究记录：adiabatic_inlet_response_v1 · manifest SHA256 " + digest(folder / "manifest.json")[:16], 14)
    svg.append("</svg>\n")
    return "\n".join(svg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["archive", "verify", "plot"])
    parser.add_argument("directory")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        if args.action == "archive":
            print(archive(args.directory))
        elif args.action == "verify":
            print(f"Adiabatic study verified (C runs, CEA cases, geometry points): {verify(local_path(ROOT, args.directory))}")
        else:
            output = ROOT / "docs/adiabatic-inlet-response.svg"
            atomic_text(output, response_svg(local_path(ROOT, args.directory)))
            print(output)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
