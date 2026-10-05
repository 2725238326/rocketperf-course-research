"""Archive continuous-liquid C17 HP/nozzle runs and explicit-molar-h CEA checks."""
from __future__ import annotations

import argparse
from datetime import datetime
import re
import shutil
import subprocess
import sys
import uuid

from adiabatic_inlet import read_output, relation
from adiabatic_study import typed_equal
from cea_reference import COMMIT, THERMO_SHA, check_reference, parse_output
from combustion_reference import compare_report
from liquid_table import BASIS, REFERENCE_SHA, expected_report, reference
from liquid_feed import DATASET
from pipeline import verified_build, verify_test_report
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json
from research_frozen_reference import SOURCE_HASHES
from research_tp_reference import run_logged

SCOPE = "Assumed continuous single-phase CH4/O2 table h and CEA chemical mass -> nine ideal-gas HP, Q=0 -> fixed-area chamber-frozen nozzle; not pump, injector, split-flow or full-cycle closure."
CONDITIONS = (
    ("base",120,1e7,100,1e7,3.4),
    ("fuel_hot",140,1e7,100,1e7,3.4),
    ("oxidizer_hot",120,1e7,110,1e7,3.4),
    ("both_hot",140,1e7,110,1e7,3.4),
    ("interior",121,11e6,101,11e6,3.4),
    ("pressure_low",120,1e6,100,1e6,3.4),
    ("pressure_high",120,20e6,100,20e6,3.4),
    ("of_2_6",120,1e7,100,1e7,2.6),
    ("of_4_2",120,1e7,100,1e7,4.2),
)
DESIGN = dict(pressure_pa=1e7, throat_area_m2=0.01, area_ratios=[10,40], ambient_pressure_pa=0.0)
TRACE = 1e-7
KEYS = {
    "schema_version","kind","status","scope","started_at","finished_at","source_head","source_dirty",
    "design","conditions","liquid_reference_sha256","c_binary_sha256","build_manifest_sha256","test_report_sha256",
    "cea_commit","cea_version","cea_binary_sha256","thermo_source_sha256","compiled_database_hashes",
    "rocket_source_hashes","explicit_inlets","runs","cea_runs","comparisons","responses","files",
}


def inputs(condition=CONDITIONS[0], area=None, ambient=0.0, throat=0.01):
    _,tf,pf,to,po,of = condition
    result = dict(feed_phase="liquid",enthalpy_basis=BASIS,fuel_temperature_k=tf,fuel_pressure_pa=pf,
                  oxidizer_temperature_k=to,oxidizer_pressure_pa=po,pressure_pa=1e7,oxidizer_fuel_mass_ratio=of)
    if area is not None:
        result.update(area_ratio=area,ambient_pressure_pa=ambient,throat_area_m2=throat)
    return result


def arguments(data, mode="hp-liquid-state", dataset=DATASET):
    fields = ["fuel_temperature_k","fuel_pressure_pa","oxidizer_temperature_k","oxidizer_pressure_pa",
              "pressure_pa","oxidizer_fuel_mass_ratio"]
    if mode == "frozen-liquid-state":
        fields += ["area_ratio","ambient_pressure_pa","throat_area_m2"]
    return ["combustion",mode,dataset,data["enthalpy_basis"],data["feed_phase"],
            *[format(data[k],".17g") for k in fields]]


def recipes():
    runs=[]
    for condition in CONDITIONS:
        name=condition[0]
        runs.append((name+"_hp",arguments(inputs(condition)),0))
        runs.extend((name+"_A"+str(area),arguments(inputs(condition,area),"frozen-liquid-state"),0)
                    for area in (10,40))
    runs += [
        ("double_area",arguments(inputs(area=10,throat=0.02),"frozen-liquid-state"),0),
        ("ambient_5000",arguments(inputs(area=10,ambient=5000),"frozen-liquid-state"),0),
    ]
    for name,change in (
        ("reject_basis",dict(enthalpy_basis="nasa9-cea-v3.3.4")),
        ("reject_gas",dict(feed_phase="gas")),("reject_two_phase",dict(feed_phase="two-phase")),
        ("reject_phase",dict(feed_phase="auto")),
        ("reject_fuel_t",dict(fuel_temperature_k=99.99)),
        ("reject_oxidizer_t",dict(oxidizer_temperature_k=110.01)),
        ("reject_fuel_p",dict(fuel_pressure_pa=999999)),
        ("reject_oxidizer_p",dict(oxidizer_pressure_pa=20000001)),
        ("reject_saturation",dict(fuel_pressure_pa=191430)),
        ("reject_pc",dict(pressure_pa=99)),("reject_of",dict(oxidizer_fuel_mass_ratio=20.01)),
        ("reject_zero",dict(pressure_pa=0)),
    ):
        runs.append((name,arguments(dict(inputs(),**change)),4))
    runs += [
        ("reject_dataset",arguments(inputs(),dataset="arbitrary-zero"),4),
        ("reject_backpressure",arguments(inputs(area=40,ambient=100000),"frozen-liquid-state"),4),
        ("reject_throat",arguments(inputs(area=10,throat=0),"frozen-liquid-state"),4),
        ("reject_nan",arguments(inputs())[:5]+["nan"]+arguments(inputs())[6:],2),
        ("reject_hex",arguments(inputs())[:5]+["0x1p7"]+arguments(inputs())[6:],2),
        ("reject_override",arguments(inputs())+["h=0"],2),
    ]
    return runs


def explicit_inlets():
    tables,_=reference()
    return {
        c[0]:{name:expected_report(fluid,inputs(c)[name+"_temperature_k"],
                                  inputs(c)[name+"_pressure_pa"],tables)["results"]
              for name,fluid in (("fuel","Methane"),("oxidizer","Oxygen"))}
        for c in CONDITIONS
    }


def cea_recipes():
    return [(c[0]+"_"+mode,c,mode) for c in CONDITIONS for mode in ("hp","rocket")]


def case_card(name, condition, mode, inlets):
    problem="hp" if mode == "hp" else "rocket frozen nfz=1"
    areas="" if mode == "hp" else " supar=10,40"
    h=inlets[condition[0]]
    return (
        "! Custom formulas with explicit total chemical h in J/mol; not CEA liquid anchors.\n"
        "! t,k=298.15 labels the assigned-h record, not a liquid table temperature.\n"
        f"problem case={name} {problem} p,bar=100 o/f={condition[-1]:.17g}{areas}\nreactants\n"
        f" fuel=FEED_CH4 C 1 H 4 wt%=100 t,k=298.15 h,j/mole={h['fuel']['h_j_per_mol']:.17g}\n"
        f" oxid=FEED_O2 O 2 wt%=100 t,k=298.15 h,j/mole={h['oxidizer']['h_j_per_mol']:.17g}\n"
        "only H2 O2 H2O CO CO2 CH4 H O OH\noutput siunits trace=1.e-7\nend\n"
    )


def check_report(report, data, mode, area=None):
    # No reference solver is called here: use its already printed values or a
    # self-snapshot to exercise all independent relations before archival.
    chamber=report["chamber"]
    rows=dict(temperature_k=[chamber["temperature_k"]],pressure_bar=[chamber["pressure_pa"]/1e5],
              enthalpy_kj_kg=[chamber["h_j_per_kg"]/1000],
              entropy_kj_kg_k=[chamber["s_j_per_kg_k"]/1000],
              molar_mass_kg_kmol=[chamber["molar_mass_kg_per_kmol"]])
    if area is not None:
        nozzle=report["nozzle"]
        for key,field in (("temperature_k","temperature_k"),("pressure_bar","pressure_pa"),
                          ("enthalpy_kj_kg","h_j_per_kg"),("entropy_kj_kg_k","s_j_per_kg_k"),
                          ("molar_mass_kg_kmol","molar_mass_kg_per_kmol")):
            scale=1e5 if key=="pressure_bar" else 1000 if key in ("enthalpy_kj_kg","entropy_kj_kg_k") else 1
            rows[key] += [nozzle["throat"]["gas"][field]/scale,nozzle["exit"]["gas"][field]/scale,
                          nozzle["exit"]["gas"][field]/scale]
        rows.update(mach=[0,nozzle["throat"]["mach"],nozzle["exit"]["mach"],nozzle["exit"]["mach"]],
                    isp_velocity_m_s=[nozzle["throat"]["velocity_m_per_s"],nozzle["exit"]["velocity_m_per_s"],nozzle["exit"]["velocity_m_per_s"]],
                    cstar_m_s=[0,nozzle["cstar_m_per_s"],nozzle["cstar_m_per_s"]],
                    ivac_m_s=[0,nozzle["vacuum_effective_velocity_m_per_s"],nozzle["vacuum_effective_velocity_m_per_s"]])
    summary=dict(rows=rows,mole_fractions={k:[v]*4 for k,v in chamber["mole_fractions"].items()},
                 output_trace_threshold=TRACE)
    compare_report(report,dict(summary=summary),mode,area,expected_inputs=data)
    return report


def evaluate(folder):
    comparisons,responses={},[]
    for c in CONDITIONS:
        name=c[0]
        hp_ref=dict(summary=parse_output((folder/(name+"_hp.out")).read_bytes(),trace_threshold=TRACE))
        rocket_ref=dict(summary=parse_output((folder/(name+"_rocket.out")).read_bytes(),True,True,TRACE))
        hp=read_output(folder,name+"_hp")
        comparisons[name+"_hp"]=compare_report(hp,hp_ref,"hp-liquid-state",expected_inputs=inputs(c))
        comparisons[name+"_hp_rocket"]=compare_report(hp,rocket_ref,"hp-liquid-state",expected_inputs=inputs(c))
        points=[(name+"_A"+str(a),a,0.0,0.01) for a in (10,40)]
        if name=="base":
            points += [("double_area",10,0.0,0.02),("ambient_5000",10,5000.0,0.01)]
        for point,area,ambient,throat in points:
            report=read_output(folder,point)
            comparisons[point]=compare_report(report,rocket_ref,"frozen-liquid-state",area,
                                               expected_inputs=inputs(c,area,ambient,throat))
            if report["chamber"]!=hp["chamber"] or report["boundary"]!=hp["boundary"]:
                raise ValueError("Continuous nozzle changed HP inlet/chamber")
            responses.append(dict(id=point,**report["geometry"],area_ratio=area,
                                  ambient_pressure_pa=ambient,oxidizer_fuel_mass_ratio=c[-1],
                                  chamber_temperature_k=hp["chamber"]["temperature_k"],
                                  inlet_mixture_h_j_per_kg=hp["boundary"]["inlet_mixture_h_j_per_kg"],
                                  cstar_m_per_s=report["nozzle"]["cstar_m_per_s"]))
    base,doubled,ambient=[read_output(folder,n) for n in ("base_A10","double_area","ambient_5000")]
    for key in ("mass_flow_kg_per_s","thrust_n","exit_area_m2"):
        relation(doubled["geometry"][key],2*base["geometry"][key],"continuous double "+key)
    relation(doubled["geometry"]["specific_impulse_s"],base["geometry"]["specific_impulse_s"],"continuous double Isp")
    relation(ambient["geometry"]["mass_flow_kg_per_s"],base["geometry"]["mass_flow_kg_per_s"],"continuous ambient flow")
    relation(base["geometry"]["thrust_n"]-ambient["geometry"]["thrust_n"],5000*base["geometry"]["exit_area_m2"],"continuous ambient thrust")
    return comparisons,responses


def required_files():
    return {"build-manifest.json","test-report.json","cea-manifest.json"} | set(SOURCE_HASHES) | {
        n+s for n,_,_ in recipes() for s in ("-stdout.txt","-stderr.txt")
    } | {n+s for n,_,_ in cea_recipes() for s in (".inp",".out","-cea-stdout.txt","-cea-stderr.txt")}


def verify(folder):
    record=read_json(folder/"manifest.json")
    fixed=check_reference()
    if (not isinstance(record,dict) or set(record)!=KEYS
        or type(record["schema_version"]) is not int or record["schema_version"]!=1
        or record["kind"]!="liquid-combustion-validation" or record["status"]!="PASS"
        or record["scope"]!=SCOPE or type(record["source_dirty"]) is not bool
        or not isinstance(record["source_head"],str) or not re.fullmatch("[0-9a-f]{40}",record["source_head"])):
        raise ValueError("Continuous liquid archive identity mismatch")
    if any(not isinstance(record[k],str) for k in ("started_at","finished_at")):
        raise ValueError("Continuous liquid archive timestamp type mismatch")
    start,finish=[datetime.fromisoformat(record[k]) for k in ("started_at","finished_at")]
    if start.utcoffset() is None or finish.utcoffset() is None or finish<start:
        raise ValueError("Continuous liquid archive timestamp order/timezone mismatch")
    identities=dict(design=DESIGN,conditions=[inputs(c) | dict(id=c[0]) for c in CONDITIONS],
                    liquid_reference_sha256=REFERENCE_SHA,explicit_inlets=explicit_inlets(),
                    cea_commit=COMMIT,cea_version="3.3.4",cea_binary_sha256=fixed["executable_sha256"],
                    thermo_source_sha256=THERMO_SHA,compiled_database_hashes=fixed["compiled_database_hashes"],
                    rocket_source_hashes=SOURCE_HASHES)
    for key,value in identities.items():
        typed_equal(record[key],value,"continuous "+key)
    required=required_files()
    entries=record["files"]
    if ({p.name for p in folder.iterdir()}!=required | {"manifest.json"}
        or any(not p.is_file() for p in folder.iterdir()) or not isinstance(entries,list)
        or len(entries)!=len(required)
        or any(not isinstance(f,dict) or set(f)!={"path","sha256"}
               or not isinstance(f["path"],str) or not isinstance(f["sha256"],str)
               or not re.fullmatch("[0-9a-f]{64}",f["sha256"]) for f in entries)
        or {f["path"] for f in entries}!=required):
        raise ValueError("Continuous liquid archive inventory mismatch")
    for item in entries:
        if digest(folder/item["path"])!=item["sha256"]:
            raise ValueError("Continuous liquid archive bytes changed")
    for name,value in SOURCE_HASHES.items():
        if digest(folder/name)!=value:
            raise ValueError("Pinned rocket source changed")
    if digest(folder/"cea-manifest.json")!=digest(ROOT/"tests/reference/cea/manifest.json"):
        raise ValueError("Pinned CEA snapshot differs")
    build=read_json(folder/"build-manifest.json");tests=read_json(folder/"test-report.json")
    verify_test_report(tests,build,digest(folder/"build-manifest.json"))
    for key,value in dict(c_binary_sha256=build["application"]["sha256"],
                          build_manifest_sha256=digest(folder/"build-manifest.json"),
                          test_report_sha256=digest(folder/"test-report.json")).items():
        typed_equal(record[key],value,"continuous "+key)
    for category,specs in (("runs",recipes()),("cea_runs",cea_recipes())):
        runs=record[category]
        if not isinstance(runs,list) or len(runs)!=len(specs):
            raise ValueError("Continuous liquid run count mismatch")
        for run,spec in zip(runs,specs):
            if not isinstance(run,dict) or set(run)!={"id","arguments","exit_code"} or type(run["exit_code"]) is not int:
                raise ValueError("Continuous liquid run schema mismatch")
            name=spec[0]
            if category=="runs":
                _,args,code=spec
                typed_equal(run,dict(id=name,arguments=args,exit_code=code),"continuous C recipe")
                stdout=(folder/(name+"-stdout.txt")).read_text(encoding="utf-8")
                stderr=(folder/(name+"-stderr.txt")).read_text(encoding="utf-8")
                prefix="Usage" if code==2 else "invalid_argument:" if name in ("reject_zero","reject_throat") else "out_of_domain:"
                if (code==0 and stderr) or (code!=0 and (stdout or not stderr.startswith(prefix))):
                    raise ValueError("Continuous liquid C stream protocol mismatch")
            else:
                _,condition,mode=spec
                typed_equal(run,dict(id=name,arguments=["-v",name],exit_code=0),"continuous CEA recipe")
                if (folder/(name+".inp")).read_text(encoding="utf-8")!=case_card(name,condition,mode,identities["explicit_inlets"]):
                    raise ValueError("Continuous explicit-h CEA card mismatch")
                log=(folder/(name+"-cea-stdout.txt")).read_text(encoding="utf-8")
                if "CEA Version: 3.3.4" not in log or "WARNING" in log or "ERROR" in log or (folder/(name+"-cea-stderr.txt")).read_bytes():
                    raise ValueError("Continuous CEA diagnostics/version mismatch")
    comparisons,responses=evaluate(folder)
    typed_equal(record["comparisons"],comparisons,"continuous comparisons")
    typed_equal(record["responses"],responses,"continuous responses")
    return len(record["runs"]),len(record["cea_runs"])


def archive(destination):
    target=local_path(ROOT,destination)
    if target.exists():
        raise FileExistsError("Continuous liquid archive destination already exists")
    folder=ROOT/"build/liquid-combustion"/uuid.uuid4().hex
    folder.mkdir(parents=True)
    record=dict(schema_version=1,kind="liquid-combustion-validation",status="RUNNING",
                scope=SCOPE,started_at=now(),runs=[],cea_runs=[])
    atomic_json(folder/"manifest.json",record)
    try:
        inlets=explicit_inlets()
        build_path=verified_build(ROOT,"Release",require_tests=True)
        build=read_json(build_path);binary=local_path(ROOT,build["application"]["path"])
        fixed=check_reference()
        source=ROOT/"build/reference/cea-v3.3.4"
        cea=ROOT/"build/reference/cea-build-v3.3.4/source/cea.exe"
        if (git(source,"rev-parse","HEAD",check=True).stdout.strip()!=COMMIT
            or git(source,"status","--porcelain","--untracked-files=no",check=True).stdout.strip()
            or digest(source/"data/thermo.inp")!=THERMO_SHA or digest(cea)!=fixed["executable_sha256"]
            or any(digest(source/"source"/n)!=v for n,v in SOURCE_HASHES.items())):
            raise ValueError("Pinned CEA source/database/binary changed")
        record.update(source_head=git(ROOT,"rev-parse","HEAD",check=True).stdout.strip(),
                      source_dirty=bool(git(ROOT,"status","--porcelain",check=True).stdout.strip()),
                      design=DESIGN,conditions=[inputs(c) | dict(id=c[0]) for c in CONDITIONS],
                      explicit_inlets=inlets,liquid_reference_sha256=REFERENCE_SHA,
                      c_binary_sha256=digest(binary),cea_commit=COMMIT,cea_version="3.3.4",
                      cea_binary_sha256=digest(cea),thermo_source_sha256=THERMO_SHA,
                      compiled_database_hashes=fixed["compiled_database_hashes"],rocket_source_hashes=SOURCE_HASHES)
        shutil.copy2(build_path,folder/"build-manifest.json")
        shutil.copy2(build_path.parent/"test-report.json",folder/"test-report.json")
        shutil.copy2(ROOT/"tests/reference/cea/manifest.json",folder/"cea-manifest.json")
        for name in SOURCE_HASHES:
            shutil.copy2(source/"source"/name,folder/name)
        for name in ("thermo.lib","trans.lib"):
            original=ROOT/"build/reference/cea-build-v3.3.4"/name
            if digest(original)!=fixed["compiled_database_hashes"][name]:
                raise ValueError("Compiled CEA database changed")
            shutil.copy2(original,folder/name)
        for name,args,code in recipes():
            run=run_logged([str(binary),*args],ROOT,folder/(name+"-stdout.txt"),folder/(name+"-stderr.txt"),15)
            record["runs"].append(dict(id=name,arguments=args,exit_code=run.returncode))
            if run.returncode!=code:
                raise ValueError("Unexpected continuous C exit: "+name)
        for name,condition,mode in cea_recipes():
            atomic_text(folder/(name+".inp"),case_card(name,condition,mode,inlets))
            run=run_logged([str(cea),"-v",name],folder,folder/(name+"-cea-stdout.txt"),folder/(name+"-cea-stderr.txt"),30)
            record["cea_runs"].append(dict(id=name,arguments=["-v",name],exit_code=run.returncode))
            if run.returncode:
                raise ValueError("Unexpected continuous CEA exit: "+name)
        verified_build(ROOT,"Release",require_tests=True)
        if digest(binary)!=record["c_binary_sha256"] or digest(cea)!=record["cea_binary_sha256"]:
            raise ValueError("Executable changed during continuous liquid runs")
        record["comparisons"],record["responses"]=evaluate(folder)
        record.update(status="PASS",finished_at=now(),build_manifest_sha256=digest(folder/"build-manifest.json"),
                      test_report_sha256=digest(folder/"test-report.json"))
        record["files"]=[dict(path=n,sha256=digest(folder/n)) for n in sorted(required_files())]
        atomic_json(folder/"manifest.json",record)
        staged=target.with_name(target.name+"-"+uuid.uuid4().hex+".tmp")
        target.parent.mkdir(parents=True,exist_ok=True)
        staged.mkdir()
        for name in required_files() | {"manifest.json"}:
            shutil.copy2(folder/name,staged/name)
        verify(staged)
        staged.rename(target)
    except Exception as exc:
        record.update(status="FAIL",error=str(exc))
        raise
    finally:
        if record["status"] != "PASS":
            record["finished_at"]=now()
        atomic_json(folder/"manifest.json",record)
    return target


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["archive","verify"])
    parser.add_argument("directory")
    args=parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        print(archive(args.directory) if args.action=="archive" else verify(local_path(ROOT,args.directory)))
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)
