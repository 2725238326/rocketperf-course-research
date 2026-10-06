"""Archive paired pure-C inlet/nozzle studies and fresh pinned CEA references."""
from __future__ import annotations

import argparse
from datetime import datetime
import math
import re
import shutil
import subprocess
import sys
import uuid

from adiabatic_study import typed_equal
from cea_reference import parse_output
from combustion_reference import compare_report
from kerosene_reference import BINARY, DATABASE, card, identity
import kerosene_validation as rp1
import liquid_combustion as ch4
from pipeline import verified_build, verify_test_report
from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json
from research_tp_reference import run_logged

SCENARIOS = (("representative", 3.4, 2.6), ("common_2_6", 2.6, 2.6), ("common_3_4", 3.4, 3.4))
AREAS = (10, 40)
AMBIENTS = (0, 5000, 100000)
SCOPE = "Declared CH4 continuous-liquid and fixed RP-1 inlets; common Pc=10MPa/At=.01m2/area/back pressure, nine-gas HP/chamber-frozen nozzle. No optimum, batch or engine ranking."
LIMITS = ["Declared inlet states and O/F; not flight engine performance or optimum mixtures.",
          "Nine neutral gas HP and chamber-frozen nozzle; no carbon, pump, cycle or hardware losses."]


def profile(fuel, ratio, area=None, ambient=0):
    if fuel == "methane":
        data = ch4.inputs(("fixed", 120, 1e7, 100, 1e7, ratio), area, ambient)
        mode = "frozen-liquid-state" if area is not None else "hp-liquid-state"
        args = ch4.arguments(data, mode)
    else:
        data = rp1.inputs(ratio, area)
        if area is not None:
            data["ambient_pressure_pa"] = ambient
        mode = "frozen-rp1" if area is not None else "hp-rp1"
        args = rp1.arguments(data, mode)
    return data, mode, args


def points():
    return [dict(id=f"{name}_A{area}_p{pa}", scenario=name, methane_of=cm, kerosene_of=cr,
                 area_ratio=area, ambient_pressure_pa=pa)
            for name, cm, cr in SCENARIOS for area in AREAS for pa in AMBIENTS]


def recipes():
    runs = []
    for point in points():
        code = 4 if point["area_ratio"] == 40 and point["ambient_pressure_pa"] == 100000 else 0
        pair = ["study", "propellants", *[str(point[key]) for key in
                ("methane_of", "kerosene_of", "area_ratio", "ambient_pressure_pa")]]
        runs.append(dict(id=point["id"]+"_pair", args=pair, exit_code=code))
        for fuel in ("methane", "kerosene"):
            _, _, args = profile(fuel, point[fuel+"_of"], point["area_ratio"], point["ambient_pressure_pa"])
            runs.append(dict(id=point["id"]+"_"+fuel, args=args, exit_code=code))
    runs += [dict(id="reject_ratio", args=["study","propellants","3.4","1","10","0"], exit_code=4),
             dict(id="reject_nan", args=["study","propellants","nan","2.6","10","0"], exit_code=2),
             dict(id="reject_count", args=["study","propellants","3.4","2.6","10"], exit_code=2)]
    return runs


def references():
    return [dict(id=f"{fuel}_{str(ratio).replace('.', '_')}_{mode}", fuel=fuel, ratio=ratio, mode=mode)
            for fuel in ("methane", "kerosene") for ratio in (2.6, 3.4) for mode in ("hp", "rocket")]


def reference_card(ref):
    if ref["fuel"] == "kerosene":
        return card(dict(id=ref["id"], ratio=ref["ratio"], mode="hp" if ref["mode"] == "hp" else "rocket frozen nfz=1",
                         products="nine-gas", fuel_temperature=298.15))
    condition = ("fixed", 120, 1e7, 100, 1e7, ref["ratio"])
    inlet = ch4.explicit_inlets()["base"]
    return ch4.case_card(ref["id"], condition, ref["mode"], dict(fixed=inlet))


def evaluate(folder):
    reference = {ref["id"]: dict(summary=parse_output((folder/(ref["id"]+".out")).read_bytes(),
                        ref["mode"] == "rocket", ref["mode"] == "rocket", 1e-7)) for ref in references()}
    comparisons, responses = {}, []
    for point in points():
        name = point["id"]
        if point["area_ratio"] == 40 and point["ambient_pressure_pa"] == 100000:
            responses.append(dict(point, status="out_of_domain"))
            continue
        pair = read_json(folder/(name+"_pair-stdout.json"))
        if set(pair) != {"schema_version","study","inputs","inlets","methane","kerosene","methane_minus_kerosene","limitations"}:
            raise ValueError("Pair result schema differs")
        typed_equal(pair["schema_version"], 1, "pair schema")
        typed_equal(pair["study"], "propellant_fixed_geometry_v1", "pair study")
        typed_equal(pair["limitations"], LIMITS, "pair limitations")
        expected = dict(pressure_pa=1e7, throat_area_m2=.01, area_ratio=point["area_ratio"],
                        ambient_pressure_pa=point["ambient_pressure_pa"],
                        methane_of=point["methane_of"],kerosene_of=point["kerosene_of"])
        typed_equal(pair["inputs"], expected, "pair inputs")
        inlets = dict(methane=dict(dataset=ch4.DATASET,basis=ch4.BASIS,fuel_temperature_k=120,
                                  oxidizer_temperature_k=100,fuel_pressure_pa=1e7,oxidizer_pressure_pa=1e7),
                      kerosene=dict(dataset=rp1.KEROSENE_DATASET,fuel="RP-1",oxidizer="O2(L)",
                                    fuel_temperature_k=298.15,oxidizer_temperature_k=90.170))
        typed_equal(pair["inlets"], inlets, "pair inlets")
        response = dict(point, status="ok", differences=pair["methane_minus_kerosene"])
        for fuel in ("methane", "kerosene"):
            report = read_json(folder/(name+"_"+fuel+"-stdout.json"))
            data, mode, _ = profile(fuel, point[fuel+"_of"],point["area_ratio"],point["ambient_pressure_pa"])
            ref = reference[f"{fuel}_{str(point[fuel+'_of']).replace('.', '_')}_rocket"]
            comparisons[name+"_"+fuel] = compare_report(report,ref,mode,point["area_ratio"],expected_inputs=data)
            expected_side = {key:report[key] for key in ("chamber","diagnostics","nozzle","geometry")}
            expected_side["inlet_mixture_h_j_per_kg"] = report["boundary"]["inlet_mixture_h_j_per_kg"]
            typed_equal(pair[fuel],expected_side,"paired vs individual "+fuel)
            response[fuel] = dict(report["geometry"], temperature_k=report["chamber"]["temperature_k"],
                                  cstar_m_per_s=report["nozzle"]["cstar_m_per_s"],
                                  exit_pressure_pa=report["nozzle"]["exit"]["gas"]["pressure_pa"],
                                  inlet_h_j_per_kg=report["boundary"]["inlet_mixture_h_j_per_kg"])
        keys = {"thrust_n":"thrust_n","isp_s":"specific_impulse_s",
                "mass_flow_kg_per_s":"mass_flow_kg_per_s","cstar_m_per_s":"cstar_m_per_s"}
        if set(response["differences"]) != set(keys):
            raise ValueError("Pair difference fields differ")
        for key,field in keys.items():
            actual = response["differences"][key]
            expected = response["methane"][field]-response["kerosene"][field]
            if type(actual) not in (int,float) or not math.isfinite(actual) or not math.isclose(actual,expected,abs_tol=1e-10,rel_tol=1e-12):
                raise ValueError("C pair difference differs")
        responses.append(response)
    return comparisons,responses


def required_files():
    files = {"build-manifest.json","test-report.json"}
    files |= {run["id"]+suffix for run in recipes() for suffix in ("-stdout.json","-stderr.txt")}
    files |= {ref["id"]+suffix for ref in references() for suffix in (".inp",".out","-cea-stdout.txt","-cea-stderr.txt")}
    return files


def verify(folder):
    record = read_json(folder/"manifest.json")
    if (type(record.get("schema_version")) is not int or record["schema_version"] != 1
        or record.get("kind") != "propellant-method-comparison" or record.get("status") != "PASS"
        or record.get("scope") != SCOPE):
        raise ValueError("Propellant study identity differs")
    typed_equal(record["recipes"],recipes(),"study recipes")
    typed_equal(record["points"],points(),"study points")
    typed_equal(record["cea_identity"],identity(),"study CEA identity")
    if type(record.get("source_dirty")) is not bool or not re.fullmatch("[a-f0-9]{40}",record["source_head"]):
        raise ValueError("Study source identity differs")
    start,finish=[datetime.fromisoformat(record[k]) for k in ("started_at","finished_at")]
    if start.utcoffset() is None or finish.utcoffset() is None or finish<start:
        raise ValueError("Study timestamp differs")
    required=required_files()
    if (any(not p.is_file() for p in folder.iterdir()) or {p.name for p in folder.iterdir()} != required|{"manifest.json"}
        or set(record["files"]) != required or any(digest(folder/name)!=sha for name,sha in record["files"].items())):
        raise ValueError("Study file inventory or bytes differ")
    build=read_json(folder/"build-manifest.json")
    verify_test_report(read_json(folder/"test-report.json"),build,digest(folder/"build-manifest.json"))
    if record["c_binary_sha256"] != build["application"]["sha256"]:
        raise ValueError("Study tested binary differs")
    for run in recipes():
        stdout=(folder/(run["id"]+"-stdout.json")).read_text(encoding="utf-8")
        stderr=(folder/(run["id"]+"-stderr.txt")).read_text(encoding="utf-8")
        if run["exit_code"] == 0:
            if stderr: raise ValueError("Study success has diagnostics")
            read_json(folder/(run["id"]+"-stdout.json"))
        elif stdout or not stderr.startswith("Usage" if run["exit_code"]==2 else "out_of_domain:"):
            raise ValueError("Study rejection protocol differs")
        if run["exit_code"]==4 and "_A40_p100000_" in run["id"] and "Overexpanded frozen nozzle" not in stderr:
            raise ValueError("Study exclusion is not the declared nozzle domain")
    for ref in references():
        name=ref["id"]
        if (folder/(name+".inp")).read_text(encoding="utf-8") != reference_card(ref):
            raise ValueError("Study CEA card differs")
        log=(folder/(name+"-cea-stdout.txt")).read_text(encoding="utf-8")
        if "CEA Version: 3.3.4" not in log or any(w in log for w in ("WARNING","ERROR")) or (folder/(name+"-cea-stderr.txt")).read_bytes():
            raise ValueError("Study CEA diagnostics differ")
    comparisons,responses=evaluate(folder)
    typed_equal(record["comparisons"],comparisons,"study comparisons")
    typed_equal(record["responses"],responses,"study responses")
    return len(recipes()),len(references())


def plot(folder):
    verify(folder)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    record=read_json(folder/'manifest.json')
    rows={r['id']:r for r in record['responses'] if r['status']=='ok'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none'})
    fig,axes=plt.subplots(2,2,figsize=(10,6),layout='constrained')
    for column,scenario in enumerate(('representative','common_2_6')):
        for row,(field,label,scale) in enumerate((('specific_impulse_s','Vacuum Isp (s)',1),('thrust_n','Vacuum thrust (kN)',1000))):
            ax=axes[row,column]
            for fuel,color,marker in (('methane','#197f89','o'),('kerosene','#be4b48','s')):
                values=[rows[f'{scenario}_A{area}_p0'][fuel][field]/scale for area in AREAS]
                ax.plot(AREAS,values,color=color,marker=marker,label='CH4 liquid table' if fuel=='methane' else 'RP-1 fixed anchor')
                other='kerosene' if fuel=='methane' else 'methane'
                for x,y in zip(AREAS,values):
                    oy=rows[f'{scenario}_A{x}_p0'][other][field]/scale
                    offset=-14 if abs(y-oy)<1 and y<oy else 6
                    ax.annotate(f'{y:.2f}',(x,y),xytext=(4,offset),textcoords='offset points',fontsize=8)
            ax.set_xticks(AREAS);ax.set_xlim(7,46);ax.margins(y=.14)
            ax.set_xlabel('Nozzle area ratio Ae/At');ax.set_ylabel(label)
            ax.grid(axis='y',color='#dddddd',linewidth=.6);ax.spines[['top','right']].set_visible(False)
            if row==0:
                ax.set_title('CH4 O/F 3.4; RP-1 O/F 2.6' if scenario=='representative' else 'Both O/F 2.6')
                ax.legend(frameon=False,fontsize=8,loc='lower right')
    fig.suptitle('Declared inlet methods: Pc 10 MPa, At 0.01 m2, vacuum',fontsize=13)
    output=ROOT/'docs/propellant-comparison.svg'
    fig.savefig(output);fig.savefig(ROOT/'build/propellant-comparison.png',dpi=150)
    plt.close(fig)
    return output


def archive(target):
    if target.exists(): raise FileExistsError("Use a new propellant study version")
    folder=ROOT/"build/propellant-comparison"/uuid.uuid4().hex
    folder.mkdir(parents=True)
    record=dict(schema_version=1,kind="propellant-method-comparison",scope=SCOPE,status="RUNNING",started_at=now())
    atomic_json(folder/"manifest.json",record)
    try:
        fixed=identity(check_runtime=True)
        build_path=verified_build(ROOT,"Release",require_tests=True)
        build=read_json(build_path); binary=local_path(ROOT,build["application"]["path"])
        record.update(cea_identity=fixed,source_head=git(ROOT,"rev-parse","HEAD",check=True).stdout.strip(),
                      source_dirty=bool(git(ROOT,"status","--porcelain",check=True).stdout.strip()),
                      c_binary_sha256=digest(binary),recipes=recipes(),points=points())
        shutil.copy2(build_path,folder/"build-manifest.json")
        shutil.copy2(build_path.parent/"test-report.json",folder/"test-report.json")
        for name in fixed["databases"]: shutil.copy2(DATABASE/name,folder/name)
        for run in recipes():
            result=run_logged([str(binary),*run["args"]],ROOT,folder/(run["id"]+"-stdout.json"),folder/(run["id"]+"-stderr.txt"),30)
            if result.returncode != run["exit_code"]:
                raise ValueError("Unexpected C point status: "+run["id"])
        for ref in references():
            name=ref["id"]
            atomic_text(folder/(name+".inp"),reference_card(ref))
            run=run_logged([str(BINARY),"-v",name],folder,folder/(name+"-cea-stdout.txt"),folder/(name+"-cea-stderr.txt"),30)
            if run.returncode: raise ValueError("CEA process failed")
        record["comparisons"],record["responses"]=evaluate(folder)
        if digest(binary)!=record["c_binary_sha256"] or identity(check_runtime=True)!=fixed:
            raise ValueError("Study binary/reference changed")
        record["files"]={name:digest(folder/name) for name in sorted(required_files())}
        record.update(status="PASS",finished_at=now());atomic_json(folder/"manifest.json",record)
        saved=folder/"archive";saved.mkdir()
        for name in required_files()|{"manifest.json"}: shutil.copy2(folder/name,saved/name)
        verify(saved)
        target.parent.mkdir(parents=True,exist_ok=True);saved.rename(target)
    except Exception as exc:
        record.update(status="FAIL",error=str(exc),finished_at=now());atomic_json(folder/"manifest.json",record)
        raise
    return target


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("archive","verify","plot"));parser.add_argument("directory")
    args=parser.parse_args();sys.stdout.reconfigure(encoding="utf-8")
    try: print({'archive':archive,'verify':verify,'plot':plot}[args.action](local_path(ROOT,args.directory)))
    except (ValueError,OSError,KeyError,TypeError,IndexError,subprocess.SubprocessError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(1)
