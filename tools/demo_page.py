"""Assemble deliverables/demo/index.html from deliverables/demo/src and collect the
non-solver facts it shows (archived CEA comparisons, engineering evidence).

The page is one offline file: CSS, data and scripts are inlined in a fixed order.
Edit the sources under deliverables/demo/src, then run tools/demo_data.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from projectlib import ROOT, atomic_text, digest, read_json

PAGE = ROOT / "deliverables" / "demo" / "index.html"
SRC = ROOT / "deliverables" / "demo" / "src"
STYLES = ("base.css", "components.css", "schematic.css")
SCRIPTS = ("core.js", "ui.js", "charts.js", "charts_more.js", "schematic_parts.js", "schematic_cycle.js",
           "tab_chamber.js", "tab_propellant.js", "tab_nozzle.js", "tab_cycle.js", "tab_validation.js",
           "tab_engineering.js", "main.js")
DATA = re.compile(r'<script id="rp-data" type="application/json">(.*?)</script>', re.S)
PHYSICS_FIELDS = ("axes", "grid", "matched_area_ratio", "chamber", "cycles", "commands", "validation", "engineering")
VALIDATION = (("ch4", "results/validation/liquid_combustion_v1"), ("rp1", "results/validation/kerosene_anchor_v1"))
EVIDENCE = "results/research/engineering_evidence_20261014"
QUALITY_GROUPS = (("project", "状态机/派生视图/链接/目录/秘密/依赖/原始证据哈希"),
                  ("governance", "非法流转、循环依赖、WIP、证据过期等治理行为"),
                  ("debug", "GCC Debug 构建与全部 C/CLI/数据测试"),
                  ("release", "GCC Release 构建与全部 C/CLI/数据测试"),
                  ("runner", "运行协议、输入对应、失败/超时、快照完整性"),
                  ("handoff", "交付包、哈希、成功/失败演示与篡改拒绝"))


def number(value):
    return float(f"{value:.6g}")


def assemble(data_text):
    page = (SRC / "page.html").read_text(encoding="utf-8")
    style = "\n".join((SRC / name).read_text(encoding="utf-8") for name in STYLES)
    script = "\n".join(f"/* ---- {name} ---- */\n" + (SRC / name).read_text(encoding="utf-8") for name in SCRIPTS)
    for marker, text in (("/*STYLE*/", style), ("<!--DATA-->", data_text), ("/*SCRIPT*/", script)):
        if page.count(marker) != 1:
            raise ValueError(f"page.html must contain exactly one {marker}")
        page = page.replace(marker, text)
    return page


def write(payload):
    atomic_text(PAGE, assemble(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")))


def reassemble():
    """Rebuild the page from its sources, keeping the already embedded (C-generated) data."""
    found = DATA.search(PAGE.read_text(encoding="utf-8"))
    if not found:
        raise SystemExit("No embedded data yet; run tools/demo_data.py first.")
    atomic_text(PAGE, assemble(found.group(1)))


def check(fresh, fields):
    page = PAGE.read_text(encoding="utf-8")
    found = DATA.search(page)
    if not found:
        raise SystemExit(f"Embedded data block missing in {PAGE}")
    embedded = json.loads(found.group(1))
    fresh = json.loads(json.dumps(fresh))
    for field in fields:
        if embedded.get(field) != fresh[field]:
            raise SystemExit(f"Embedded demo data field '{field}' differs from a fresh run.")
    if assemble(found.group(1)) != page:
        raise SystemExit("index.html differs from deliverables/demo/src; rerun tools/demo_data.py.")


def validation_summary():
    """Archived C-vs-CEA field comparisons, read from the saved manifests, not recomputed."""
    out = {}
    for fuel, folder in VALIDATION:
        manifest = read_json(ROOT / folder / "manifest.json")
        out[fuel] = {"archive": folder, "c_runs": len(manifest.get("runs", manifest.get("recipes", []))),
                     "cea_cards": len(list((ROOT / folder).glob("*.inp"))),
                     "rows": [[case, row["field"], number(row["difference"]), row["absolute_tolerance"]]
                              for case, entries in manifest["comparisons"].items() for row in entries]}
    return out


def lines(path):
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def evidence():
    folder = ROOT / EVIDENCE
    manifest = read_json(folder / "manifest.json")
    for entry in manifest["files"]:
        if digest(folder / entry["path"]) != entry["sha256"]:
            raise ValueError(f"Engineering evidence hash mismatch: {entry['path']}")
    bench, analysis = read_json(folder / "benchmark-hp.json"), read_json(folder / "static-analysis.json")
    before, after = bench["samples"]["before"], bench["samples"]["after"]
    audit = (ROOT / "docs/maintenance-audit.md").read_text(encoding="utf-8")
    if "旧版0.159 s、新版0.085 s" not in audit:
        raise ValueError("Frozen-nozzle benchmark record moved; update the historical entry")
    return {"archive": EVIDENCE,
            "hp": {"before_s": bench["median_cpu_seconds"]["before"], "after_s": bench["median_cpu_seconds"]["after"],
                   "speedup": number(bench["speedup"]), "samples": len(before), "solves": 310,
                   "iterations_before": number(before[0]["mean_hp_iterations"]), "iterations_after": number(after[0]["mean_hp_iterations"]),
                   "checksum_delta_k": number(abs(after[0]["checksum_temperature_k"] - before[0]["checksum_temperature_k"])),
                   "baseline": bench["baseline_head"][:7]},
            "frozen": {"before_s": 0.159, "after_s": 0.085, "solves": 2000, "source": "docs/maintenance-audit.md"},
            "analyzer": {"status": analysis["status"], "units": analysis["checks"], "compiler": analysis["compiler_version"],
                         "clean_logs": sum(1 for unit in analysis["units"] if unit["log_bytes"] == 0 and unit["exit_code"] == 0)}}


def engineering(manifest_path, manifest):
    registry = read_json(ROOT / "project/modules.json")["modules"]
    modules = []
    for module in registry:
        if module["id"] == "tooling":
            continue
        files = sorted({p for pattern in module["paths"] for p in ROOT.glob(pattern) if p.suffix in (".c", ".h")})
        code = [p for p in files if not p.name.endswith("_generated.h")]
        modules.append({"id": module["id"], "name": module["name"], "deps": module["allowed_dependencies"],
                        "files": len(code), "lines": sum(lines(p) for p in code),
                        "generated_lines": sum(lines(p) for p in files if p.name.endswith("_generated.h"))})
    report = read_json(manifest_path.parent / "test-report.json")
    tests = {k: report[k] for k in ("core_checks", "adapter_checks", "thermo_checks", "combustion_checks", "cycle_checks",
                                    "cli_groups", "parameter_data_groups", "thermo_data_groups", "cea_reference_groups",
                                    "cycle_reference_groups")}
    test_files = sorted((ROOT / "tests").glob("test_*.*"))
    return {"modules": modules, "tests": tests,
            "c_checks": sum(tests[k] for k in ("core_checks", "adapter_checks", "thermo_checks", "combustion_checks", "cycle_checks")),
            "test_files": [{"name": p.name, "lines": lines(p)} for p in test_files if p.suffix in (".c", ".py")],
            "flags": [f for f in manifest["flags"] if f.startswith(("-W", "-std", "-f"))],
            "quality_groups": [{"id": k, "scope": v} for k, v in QUALITY_GROUPS], "evidence": evidence()}
