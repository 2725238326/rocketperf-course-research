"""Generate C17 liquid tables and check/archive real CLI queries."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import re
import shutil
import subprocess
import sys
import uuid

import liquid_feed
from adiabatic_study import typed_equal
from liquid_eos import close
from pipeline import strict_json, verified_build, verify_test_report
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json

REFERENCE = "results/research/liquid_feed_reference_v1"
REFERENCE_SHA = "b1118927139793f0ef418872fb2074b37915c624d43bfca9ad519caba2b5a651"
MODEL = "single_phase_liquid_table_v1"
BASIS = "heos710-cea334-ideal-zero-298.15-v1"
LIMITATIONS = [
    "Assumed pure CH4/O2 single-phase liquid reference, not measured engine inlet data.",
    "Bilinear interpolation within the pinned rectangle; no flash, extrapolation, pump or cycle solve.",
    "EOS density mass and CEA chemical enthalpy mass conventions are returned separately.",
    "HEOS ideal cp differs from NASA9 after the single ideal-zero alignment.",
]
SCOPE = "C17 single-phase liquid table queries and rejection protocol; no combustion, pump or cycle closure."


def reference():
    folder = ROOT/REFERENCE
    if digest(folder/"manifest.json") != REFERENCE_SHA:
        raise ValueError("Pinned liquid reference manifest changed")
    liquid_feed.verify(folder)
    return read_json(folder/"tables.json"), read_json(folder/"raw-output.json")


def generated():
    tables, raw = reference()
    f = lambda value: format(value,".17g")
    header = [
        "/* GENERATED offline HEOS/CEA-aligned data. See third_party/README.md and liquid-feed-contract.md. */",
        "#ifndef RP_LIQUID_FEED_GENERATED_H", "#define RP_LIQUID_FEED_GENERATED_H",
        f'#define RP_LIQUID_DATASET_ID "{liquid_feed.DATASET}"',
        f'#define RP_LIQUID_REFERENCE_SHA256 "{REFERENCE_SHA}"',
        "static const double rp_liquid_pressures[] = {"+", ".join(map(f,liquid_feed.PRESSURES))+"};",
    ]
    refs = [
        "/* GENERATED from raw CoolProp nodes and off-grid points, not C interpolation. */",
        "#ifndef RP_LIQUID_FEED_REFERENCE_H", "#define RP_LIQUID_FEED_REFERENCE_H",
        "typedef struct { const char *fluid; double temperature, pressure, density, h_molar; int node; } RpLiquidReference;",
        "static const RpLiquidReference rp_liquid_references[] = {",
    ]
    declarations = []
    for fluid, table in tables.items():
        prefix = fluid.lower()
        axis = liquid_feed.TEMPERATURES[fluid]
        header += [
            f"static const double rp_liquid_{prefix}_temperatures[] = {{"+", ".join(map(f,axis))+"};",
            f"static const double rp_liquid_{prefix}_points[][2] = {{",
            *["    {"+f(row["density_kg_per_m3"])+", "+f(row["aligned_h_j_per_mol"])+"},"
              for row in table["nodes"]], "};",
        ]
        declarations.append('    {"%s", %s, %s, %dU, rp_liquid_%s_temperatures, %dU, rp_liquid_pressures, rp_liquid_%s_points}' % (
            fluid,f(table["molar_mass_eos_kg_per_mol"]),f(table["molar_mass_cea_kg_per_mol"]),
            len(axis),prefix,len(liquid_feed.PRESSURES),prefix))
        for kind in ("nodes","interior"):
            for row in raw["fluids"][fluid][kind]:
                refs.append('    {"%s", %s, %s, %s, %s, %d},' % (
                    fluid,f(row["temperature_k"]),f(row["pressure_pa"]),f(row["density_kg_per_m3"]),
                    f(row["h_j_per_mol"]+table["aligned_offset_j_per_mol"]),int(kind=="nodes")))
    header += ["static const RpLiquidTable rp_liquid_tables[] = {",",\n".join(declarations),"};","#endif",""]
    refs += ["};","#endif",""]
    return {"src/thermo/liquid_feed_generated.h":"\n".join(header),
            "tests/reference/liquid_feed.h":"\n".join(refs)}


def check_generated():
    for path, expected in generated().items():
        if (ROOT/path).read_text(encoding="utf-8") != expected:
            raise ValueError("Generated liquid C data changed: "+path)
    return 2


def expected_report(fluid, t, p, tables):
    table = tables[fluid]
    result = liquid_feed.interpolation(table["nodes"],fluid,dict(fluid=fluid,temperature_k=t,pressure_pa=p))
    if result["status"] != "ok":
        raise ValueError("Expected successful liquid query is outside the reference")
    return dict(
        schema_version=1, model=MODEL, dataset_id=liquid_feed.DATASET, status="ok",
        inputs=dict(fluid=fluid,phase="liquid",temperature_k=t,pressure_pa=p),
        results=dict(density_kg_per_m3=result["density_kg_per_m3"],
                     h_j_per_mol=result["aligned_h_j_per_mol"],
                     h_j_per_kg=result["aligned_h_j_per_mol"]/table["molar_mass_cea_kg_per_mol"],
                     eos_molar_mass_kg_per_mol=table["molar_mass_eos_kg_per_mol"],
                     chemical_molar_mass_kg_per_mol=table["molar_mass_cea_kg_per_mol"]),
        provenance=dict(reference_manifest_sha256=REFERENCE_SHA,enthalpy_basis=BASIS,
                        density_mass_basis="CoolProp7.1.0 EOS molar mass",input_role="assumed_research"),
        limitations=LIMITATIONS)


def validate_report(report, fluid, t, p, tables=None):
    if tables is None:
        tables,_ = reference()
    expected = expected_report(fluid,t,p,tables)
    if not isinstance(report,dict) or set(report) != set(expected):
        raise ValueError("Liquid CLI report schema mismatch")
    for key in expected:
        if key == "results":
            if not isinstance(report[key],dict) or set(report[key]) != set(expected[key]):
                raise ValueError("Liquid CLI result fields differ")
            for field,value in expected[key].items():
                close(report[key][field],value,"liquid C "+field,rel=2e-13,absolute=1e-9)
        else:
            typed_equal(report[key],expected[key],"liquid C "+key)
    return report


def recipes():
    base = ["liquid-feed",liquid_feed.DATASET,"Methane","liquid","120","10000000"]
    runs = []
    for name,fluid,t,p in (("methane_node","Methane",120,1e7),("oxygen_node","Oxygen",100,1e7),
                           ("methane_interior","Methane",121,11e6),("oxygen_interior","Oxygen",101,11e6),
                           ("methane_lower","Methane",100,1e6),("oxygen_upper","Oxygen",110,20e6)):
        runs.append((name,["liquid-feed",liquid_feed.DATASET,fluid,"liquid",format(t,".17g"),format(p,".17g")],0))
    for name,index,value,code in (
        ("reject_dataset",1,"unknown-zero",4),("reject_fluid",2,"RP-1",4),
        ("reject_gas",3,"gas",4),("reject_two_phase",3,"two-phase",4),
        ("reject_phase",3,"auto",4),("reject_lower_temperature",4,"99.99",4),
        ("reject_upper_temperature",4,"140.01",4),("reject_lower_pressure",5,"999999",4),
        ("reject_upper_pressure",5,"20000001",4),("reject_critical",4,"185",4),
        ("reject_saturation",5,"191430",4),("reject_nan",4,"nan",2),
        ("reject_hex",4,"0x1p7",2),("reject_negative",4,"-1",4),("reject_zero",5,"0",4),
    ):
        args = base.copy()
        args[index] = value
        runs.append((name,args,code))
    runs.append(("reject_override",base+["h=0"],2))
    return runs


def verify(folder):
    record = read_json(folder/"manifest.json")
    keys = {"schema_version","kind","status","scope","started_at","finished_at","reference_sha256",
            "source_head","source_dirty","build_manifest_sha256","test_report_sha256","binary_sha256","runs","files"}
    if (not isinstance(record,dict) or set(record) != keys
        or type(record["schema_version"]) is not int or record["schema_version"] != 1
        or record["kind"] != "liquid-table-validation" or record["status"] != "PASS"
        or record["scope"] != SCOPE or type(record["source_dirty"]) is not bool
        or not isinstance(record["source_head"],str) or not re.fullmatch("[0-9a-f]{40}",record["source_head"])
        or record["reference_sha256"] != REFERENCE_SHA):
        raise ValueError("Liquid C archive identity mismatch")
    if any(not isinstance(record[k],str) for k in ("started_at","finished_at")):
        raise ValueError("Liquid C archive timestamp type mismatch")
    start,finish = [datetime.fromisoformat(record[k]) for k in ("started_at","finished_at")]
    if start.utcoffset() is None or finish.utcoffset() is None or finish < start:
        raise ValueError("Liquid C archive timestamp order/timezone mismatch")
    tables,_ = reference()
    required = {"build-manifest.json","test-report.json"} | {
        name+suffix for name,_,_ in recipes() for suffix in ("-stdout.txt","-stderr.txt")}
    files = record["files"]
    if ({p.name for p in folder.iterdir()} != required | {"manifest.json"}
        or any(not p.is_file() for p in folder.iterdir()) or not isinstance(files,list)
        or len(files) != len(required)
        or any(not isinstance(f,dict) or set(f) != {"path","sha256"}
               or not isinstance(f["path"],str) or not isinstance(f["sha256"],str)
               or not re.fullmatch("[0-9a-f]{64}",f["sha256"]) for f in files)
        or {f["path"] for f in files} != required):
        raise ValueError("Liquid C archive inventory mismatch")
    for item in files:
        if digest(folder/item["path"]) != item["sha256"]:
            raise ValueError("Liquid C archive bytes changed")
    build = read_json(folder/"build-manifest.json")
    tests = read_json(folder/"test-report.json")
    verify_test_report(tests,build,digest(folder/"build-manifest.json"))
    typed_equal(record["binary_sha256"],build["application"]["sha256"],"liquid C binary")
    typed_equal(record["build_manifest_sha256"],digest(folder/"build-manifest.json"),"liquid C build")
    typed_equal(record["test_report_sha256"],digest(folder/"test-report.json"),"liquid C tests")
    for path,content in generated().items():
        identities = build["inputs"] if path.startswith("src/") else tests["validation_inputs"]
        identity = next((entry["sha256"] for entry in identities if entry["path"] == path),None)
        if identity != hashlib.sha256(content.encode("utf-8")).hexdigest():
            raise ValueError("Archived C build used different liquid data: "+path)
    if not isinstance(record["runs"],list) or len(record["runs"]) != len(recipes()):
        raise ValueError("Liquid C archive run count mismatch")
    for run,(name,args,code) in zip(record["runs"],recipes()):
        if not isinstance(run,dict) or set(run) != {"id","arguments","exit_code"} or type(run["exit_code"]) is not int:
            raise ValueError("Liquid C archive run schema mismatch")
        typed_equal(run,dict(id=name,arguments=args,exit_code=code),"liquid C recipe")
        stdout = (folder/(name+"-stdout.txt")).read_text(encoding="utf-8")
        stderr = (folder/(name+"-stderr.txt")).read_text(encoding="utf-8")
        if code == 0:
            if stderr:
                raise ValueError("Liquid C success has diagnostics")
            validate_report(strict_json(stdout),args[2],float(args[4]),float(args[5]),tables)
        elif stdout or not stderr.startswith("Usage" if code == 2 else
                                             "invalid_argument:" if name in ("reject_negative","reject_zero") else "out_of_domain:"):
            raise ValueError("Liquid C rejection protocol mismatch")
    return len(record["runs"])


def archive(destination):
    target = local_path(ROOT,destination)
    if target.exists():
        raise FileExistsError("Liquid C archive destination already exists")
    folder = ROOT/"build/liquid-table"/uuid.uuid4().hex
    folder.mkdir(parents=True)
    record = dict(schema_version=1,kind="liquid-table-validation",status="RUNNING",
                  scope=SCOPE,started_at=now(),reference_sha256=REFERENCE_SHA,runs=[])
    atomic_json(folder/"manifest.json",record)
    try:
        check_generated()
        build_path = verified_build(ROOT,"Release",require_tests=True)
        build = read_json(build_path)
        binary = local_path(ROOT,build["application"]["path"])
        shutil.copy2(build_path,folder/"build-manifest.json")
        shutil.copy2(build_path.parent/"test-report.json",folder/"test-report.json")
        record.update(source_head=git(ROOT,"rev-parse","HEAD",check=True).stdout.strip(),
                      source_dirty=bool(git(ROOT,"status","--porcelain",check=True).stdout.strip()),
                      build_manifest_sha256=digest(folder/"build-manifest.json"),
                      test_report_sha256=digest(folder/"test-report.json"),binary_sha256=digest(binary))
        for name,args,code in recipes():
            completed = subprocess.run([str(binary),*args],cwd=ROOT,capture_output=True,timeout=15,check=False)
            (folder/(name+"-stdout.txt")).write_bytes(completed.stdout)
            (folder/(name+"-stderr.txt")).write_bytes(completed.stderr)
            record["runs"].append(dict(id=name,arguments=args,exit_code=completed.returncode))
            if completed.returncode != code:
                raise ValueError("Unexpected liquid C exit: "+name)
        verified_build(ROOT,"Release",require_tests=True)
        record["files"] = [dict(path=p.name,sha256=digest(p)) for p in sorted(folder.iterdir())
                           if p.name != "manifest.json"]
        record["status"] = "PASS"
        record["finished_at"] = now()
        atomic_json(folder/"manifest.json",record)
        # Semantic verification is part of this attempt, not a later publication
        # step: a rejected result must leave FAIL and its original streams.
        verify(folder)
    except Exception as exc:
        record.update(status="FAIL",error=str(exc))
        raise
    finally:
        record["finished_at"] = now()
        atomic_json(folder/"manifest.json",record)
    target.parent.mkdir(parents=True,exist_ok=True)
    staged = target.with_name(target.name+"-"+uuid.uuid4().hex+".tmp")
    shutil.copytree(folder,staged)
    verify(staged)
    staged.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command",required=True)
    sub.add_parser("generate")
    sub.add_parser("check")
    for name in ("archive","verify"):
        sub.add_parser(name).add_argument("path")
    args = parser.parse_args()
    if args.command == "generate":
        for path,content in generated().items():
            atomic_text(ROOT/path,content)
        print("Generated 2 liquid C data files")
    elif args.command == "check":
        print(check_generated())
    elif args.command == "archive":
        print(archive(args.path))
    else:
        print(verify(local_path(ROOT,args.path)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)
