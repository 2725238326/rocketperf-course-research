"""Build/test/run lifecycle with immutable builds and truthful failure records."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, lock, now, read_json, strict_json, subprocess_env

CORE_KEYS={"gamma","gas_constant_j_kg_k","stagnation_temperature_k","stagnation_pressure_pa","area_ratio","throat_area_m2","ambient_pressure_pa"}
RESULT_KEYS={"exit_mach","exit_temperature_k","exit_pressure_pa","exit_velocity_m_s","exit_area_m2","characteristic_velocity_m_s","mass_flow_kg_s","thrust_n","thrust_coefficient","specific_impulse_s"}
DEFAULT_RATIOS=[1,1.25,1.6875,2,4,8,16]
DEFAULT_PRESSURES=[0,25000,50000,100000]


def snapshot_values(input_text):
    values={}
    for line in input_text.lstrip('\ufeff').splitlines():
        line=line.strip()
        if not line or line.startswith('#'): continue
        key,sep,value=line.partition('=')
        if not sep or key.strip() in values: raise ValueError('Snapshot contains malformed/duplicate fields')
        values[key.strip()]=value.strip()
    return values


def ideal_input_domain(inputs):
    if (not 1 < inputs['gamma'] <= 2 or not 1 <= inputs['area_ratio'] <= 1e4
        or inputs['ambient_pressure_pa'] < 0
        or any(inputs[k] <= 0 for k in CORE_KEYS-{'gamma','area_ratio','ambient_pressure_pa'})):
        raise ValueError('Ideal-nozzle inputs outside the C domain')


def ideal_log_area(mach, gamma):
    delta=gamma-1
    return -math.log(mach)+(gamma+1)/(2*delta)*(math.log1p(delta*mach*mach/2)-math.log1p(delta/2))


def check_relation(actual, expected, label, rel=1e-8, absolute=1e-10):
    if not math.isfinite(expected) or not math.isclose(actual,expected,rel_tol=rel,abs_tol=absolute):
        raise ValueError('Inconsistent result relation: '+label)


def ideal_exclusion_supported(inputs):
    """Invert pressure at the domain boundary, not the area/Mach root solve."""
    ideal_input_domain(inputs)
    pa=inputs['ambient_pressure_pa']/(1+1e-10)
    if pa <= 0: return False
    gamma=inputs['gamma']; delta=gamma-1; pc=inputs['stagnation_pressure_pa']
    critical=pc*math.exp(-gamma/delta*math.log1p(delta/2))
    if pa > critical: return True
    mach=math.sqrt(2/delta*math.expm1(delta/gamma*math.log(pc/pa)))
    # C's accepted area residual bounds the position of the pressure boundary.
    # Retain that tiny numerical ambiguity, never reject a legitimate grid due
    # to a few ulps or claim experimental accuracy for the exclusion threshold.
    return ideal_log_area(mach,gamma) < math.log(inputs['area_ratio'])+1e-8


def grid_axis(text, pressure=False):
    tokens=text.split(',')
    if not 1<=len(tokens)<=32 or any(not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',x.strip()) for x in tokens):
        raise ValueError('Grid requires 1..32 comma-separated decimal values')
    values=[float(x) for x in tokens]
    if any(not math.isfinite(x) or (x<0 if pressure else not 1<=x<=1e4) for x in values):
        raise ValueError('Grid values outside the supported range')
    return values


def validate_study(report, input_text, ratios, pressures):
    required={'schema_version','program_version','study','base_inputs','grid','points','limitations'}
    if not isinstance(report,dict) or set(report)!=required or type(report['schema_version']) is not int or report['schema_version']!=1:
        raise ValueError('Result does not match S1 report schema')
    expected_grid={'area_ratios':ratios,'ambient_pressures_pa':pressures,'ordering':'area_ratio_outer_ambient_pressure_inner'}
    if report['grid']!=expected_grid: raise ValueError('Study grid differs from requested grid')
    for axis in ('area_ratios','ambient_pressures_pa'):
        if any(type(x) not in {int,float} or not math.isfinite(x) for x in report['grid'][axis]): raise ValueError('Invalid grid value')
    values=snapshot_values(input_text)
    if set(values)!=CORE_KEYS|{'schema_version','case_id','case_kind','source_ref','model'} or values['schema_version']!='1':
        raise ValueError('Invalid ideal snapshot schema')
    expected_study={'id':'S1_area_ratio_ambient','model':values['model'],'case_id':values['case_id'],'kind':values['case_kind'],'source_ref':values['source_ref']}
    if report['study']!=expected_study: raise ValueError('Study provenance differs from input snapshot')
    if not isinstance(report['base_inputs'],dict) or set(report['base_inputs'])!=CORE_KEYS-{'area_ratio','ambient_pressure_pa'}:
        raise ValueError('Study base input fields incomplete')
    for key,x in report['base_inputs'].items():
        if type(x) not in {int,float} or not math.isfinite(x) or x!=float(values[key]): raise ValueError('Study input mismatch')
    points=report['points']
    if not isinstance(points,list) or len(points)!=len(ratios)*len(pressures): raise ValueError('Study point count mismatch')
    counts={'ok':0,'out_of_domain':0}
    for i,point in enumerate(points):
        ratio=ratios[i//len(pressures)];pressure=pressures[i%len(pressures)]
        if not isinstance(point,dict) or any(type(point.get(key)) not in {int,float} or point[key]!=expected for key,expected in [('area_ratio',ratio),('ambient_pressure_pa',pressure)]):
            raise ValueError('Study point coordinate/order mismatch')
        status=point.get('status')
        if status=='ok':
            if set(point)!={'area_ratio','ambient_pressure_pa','status','results','diagnostics'}: raise ValueError('Invalid successful point schema')
            inputs={**report['base_inputs'],'area_ratio':ratio,'ambient_pressure_pa':pressure}
            synthetic={'schema_version':1,'program_version':report['program_version'],'model':values['model'],
                'case':{'id':values['case_id'],'kind':values['case_kind'],'source_ref':values['source_ref']},
                'inputs':inputs,'results':point['results'],'diagnostics':point['diagnostics'],'limitations':report['limitations']}
            point_input='\n'.join(f'{k}={v}' for k,v in {**values,'area_ratio':ratio,'ambient_pressure_pa':pressure}.items())
            validate_result(synthetic,point_input)
        elif status=='out_of_domain':
            if set(point)!={'area_ratio','ambient_pressure_pa','status','error'} or not isinstance(point['error'],str) or not point['error'].strip():
                raise ValueError('Domain exclusion has no valid diagnostic')
            inputs={**report['base_inputs'],'area_ratio':ratio,'ambient_pressure_pa':pressure}
            if (point['error'] != 'Overexpanded/back-pressure flow is not supported by this model.'
                or not ideal_exclusion_supported(inputs)):
                raise ValueError('Domain exclusion is inconsistent with back-pressure/area inputs')
        else: raise ValueError('Calculation error is not an expected domain exclusion')
        counts[status]+=1
    if not re.fullmatch(r'\d+\.\d+\.\d+',str(report['program_version'])) or not isinstance(report['limitations'],list) or not report['limitations'] or any(not isinstance(x,str) or not x for x in report['limitations']):
        raise ValueError('Study version/limitations missing')
    return counts


def validate_result(report, input_text):
    required={"schema_version","program_version","model","case","inputs","results","diagnostics","limitations"}
    if not isinstance(report,dict) or set(report)!=required or type(report["schema_version"]) is not int or report["schema_version"]!=1:
        raise ValueError("Result does not match v1 report schema")
    values=snapshot_values(input_text)
    if set(values)!=CORE_KEYS|{'schema_version','case_id','case_kind','source_ref','model'} or values['schema_version']!='1':
        raise ValueError('Invalid ideal snapshot schema')
    if report["model"]!=values.get("model") or report["model"]!="ideal_constant_gamma_v1":
        raise ValueError("Result model differs from input snapshot")
    if not isinstance(report["program_version"],str) or not re.fullmatch(r"\d+\.\d+\.\d+",report["program_version"]):
        raise ValueError("Missing semantic program version")
    if report["case"]!={"id":values.get("case_id"),"kind":values.get("case_kind"),"source_ref":values.get("source_ref")}:
        raise ValueError("Result provenance differs from input snapshot")
    if report["case"]["kind"] not in {"synthetic_benchmark","research_scenario"}: raise ValueError("Unsupported case category")
    if not isinstance(report["inputs"],dict) or set(report["inputs"])!=CORE_KEYS: raise ValueError("Result input fields incomplete")
    if not isinstance(report["results"],dict) or set(report["results"])!=RESULT_KEYS: raise ValueError("Result output fields incomplete")
    for key,value in report["inputs"].items():
        if type(value) not in {float,int} or not math.isfinite(value) or value!=float(values[key]):
            raise ValueError(f"Input mismatch/non-finite value: {key}")
    for key,value in report["results"].items():
        if type(value) not in {float,int} or not math.isfinite(value) or value<=0: raise ValueError(f"Invalid result value: {key}")
    diag=report["diagnostics"]
    if not isinstance(diag,dict) or set(diag)!={"root_iterations","relative_area_residual"}: raise ValueError("Invalid diagnostics schema")
    if type(diag["root_iterations"]) is not int or not 0<=diag["root_iterations"]<=100000: raise ValueError("Invalid iteration count")
    residual=diag["relative_area_residual"]
    if type(residual) not in {int,float} or not math.isfinite(residual) or not 0<=residual<=1e-8: raise ValueError("Area residual exceeds contract")
    if not isinstance(report["limitations"],list) or not report["limitations"] or any(not isinstance(x,str) or not x.strip() for x in report["limitations"]): raise ValueError("Model limitations missing")
    ideal_input_domain(report['inputs'])
    i=report['inputs']; r=report['results']; g=i['gamma']; delta=g-1; mach=r['exit_mach']
    if mach < 1: raise ValueError('Expected sonic/supersonic nozzle branch')
    try:
        area_residual=abs(math.expm1(ideal_log_area(mach,g)-math.log(i['area_ratio'])))
        if area_residual > 1e-8: raise ValueError('Recomputed area residual exceeds contract')
        check_relation(residual,area_residual,'area residual identity',absolute=2e-12)
        te=i['stagnation_temperature_k']/(1+delta*mach*mach/2)
        pe=i['stagnation_pressure_pa']*math.exp(-g/delta*math.log1p(delta*mach*mach/2))
        if i['ambient_pressure_pa'] > pe*(1+1e-10): raise ValueError('Successful result outside back-pressure domain')
        velocity=mach*math.sqrt(g*i['gas_constant_j_kg_k']*te)
        area=i['throat_area_m2']*i['area_ratio']
        cstar=math.sqrt(i['gas_constant_j_kg_k']*i['stagnation_temperature_k']/g)*math.exp((g+1)/(2*delta)*math.log1p(delta/2))
        flow=i['stagnation_pressure_pa']*i['throat_area_m2']/cstar
        thrust=flow*velocity+(pe-i['ambient_pressure_pa'])*area
        expected={'exit_temperature_k':te,'exit_pressure_pa':pe,'exit_velocity_m_s':velocity,'exit_area_m2':area,
                  'characteristic_velocity_m_s':cstar,'mass_flow_kg_s':flow,'thrust_n':thrust,
                  'thrust_coefficient':thrust/(i['stagnation_pressure_pa']*i['throat_area_m2']),
                  'specific_impulse_s':thrust/(flow*9.80665)}
        for key,value in expected.items(): check_relation(r[key],value,key)
        check_relation(flow,pe/(i['gas_constant_j_kg_k']*te)*velocity*area,'exit continuity')
    except (OverflowError,ZeroDivisionError) as exc:
        raise ValueError('Invalid ideal-nozzle algebraic state') from exc


def config_name(configuration,sanitize):
    if configuration not in {"Debug","Release"}: raise ValueError("Unsupported build configuration")
    if sanitize and os.name=="nt": raise ValueError("Sanitizers are configured only for Linux GCC")
    return configuration.lower()+("-sanitized" if sanitize else "")


def cli_test_count(log):
    summary=re.search(r'Ran (\d+) tests?\b',log)
    if summary is None or int(summary.group(1)) == 0 or 'skipped' in log.lower() or not re.search(r'^OK\s*$', log, re.MULTILINE):
        raise ValueError('CLI evidence requires executed tests and zero skips')
    return int(summary.group(1))


def file_records(root,paths):
    return [{"path":p,"sha256":digest(local_path(root,p))} for p in sorted(set(paths))]


def source_records(root):
    modules=read_json(root/"project/modules.json")["modules"]
    sources=[s for m in modules for s in m["sources"]]
    sources += [p.relative_to(root).as_posix() for folder in ("include","src") for p in (root/folder).rglob('*.h')]
    sources += [p.relative_to(root).as_posix() for p in (root/'tests').rglob('*.h')]
    sources += ["tests/test_core.c","tests/test_adapters.c","tests/test_thermo.c","tests/test_combustion.c","tests/test_cycle.c","tests/reference/nasa9_cantera.h","tests/fixtures/sanitizer_probe.c","tools/pipeline.py","tools/projectlib.py","project/modules.json","scripts/build.ps1","CMakeLists.txt"]
    return file_records(root,sources)


def test_records(root):
    # Validation consumes archive stdout/stderr as well as JSON and raw references.
    files=[p.relative_to(root).as_posix() for folder in ("tests","cases/benchmarks","data","results/validation","results/research")
           for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'
           and not (folder=='results/research' and p.name=='README.md')]
    files += ['tools/thermo_data.py','tools/cea_reference.py','tools/combustion_reference.py',
              'tools/cycle_validation.py','tools/gas_checks.py','tools/check_data.py','tools/handoff.py','tools/cycle_study.py','tools/research_tp_reference.py','tools/research_frozen_reference.py','tools/thermal_boundary.py','tools/adiabatic_inlet.py','tools/adiabatic_study.py',
              '调研/原始来源/来源文件索引.json','docs/adiabatic-inlet-response.svg',
              'tools/feed_candidates.py','tools/liquid_anchor.py','tools/liquid_feed.py',
              'tools/liquid_eos.py','tools/liquid_table.py','tools/liquid_combustion.py',
              'tools/kerosene_reference.py','tools/kerosene_validation.py','tools/kerosene_probe.c','调研/feed_sources.json']
    # Parameter checks resolve source IDs and local references; those inputs must
    # invalidate a previous data PASS too. Task states are intentionally dynamic.
    for dataset in (root/'data/parameters').glob('*.json'):
        payload=read_json(dataset)
        if not isinstance(payload,dict): raise ValueError('Parameter dataset must be an object: '+str(dataset))
        records=payload.get('records',[])
        if not isinstance(records,list): raise ValueError('Parameter records must be a list: '+str(dataset))
        for record in records:
            if not isinstance(record,dict): continue
            refs=record.get('source_refs',[])
            if not isinstance(refs,list): continue
            files += [ref.split('#',1)[0] for ref in refs
                      if isinstance(ref,str) and ref.startswith(('docs/','调研/'))]
        if payload.get('dataset_id') == 'feed-property-candidates-v1':
            for collection in ('source_files', 'cea_source_files'):
                entries = payload.get(collection)
                if not isinstance(entries, list) or not entries:
                    raise ValueError('Feed property source identities must be nonempty arrays')
                for entry in entries:
                    if not isinstance(entry,dict) or not isinstance(entry.get('path'),str):
                        raise ValueError('Feed property source identity requires a path')
                    files.append(entry['path'])
        if payload.get('dataset_id') == 'assignment-case-map-v1':
            cases = payload.get('research_cases')
            if not isinstance(cases, list):
                raise ValueError('Assignment research cases must be an array')
            for case in cases:
                if not isinstance(case, dict) or not isinstance(case.get('artifact_refs'), list):
                    raise ValueError('Assignment method requires artifact references')
                if any(not isinstance(ref, str) for ref in case['artifact_refs']):
                    raise ValueError('Assignment artifact reference must be a path')
                files += case['artifact_refs']
    return file_records(root,files)


def verify_test_report(report, manifest, manifest_sha256):
    if (not isinstance(report,dict) or not isinstance(manifest,dict)
        or manifest.get('kind') != 'build' or manifest.get('status') != 'PASS'
        or not isinstance(manifest.get('application'),dict) or not isinstance(manifest['application'].get('sha256'),str)):
        raise ValueError('Test evidence has invalid report/build shape')
    names = {'core','adapters','thermo','combustion','cycle','parameter-data','thermo-data','cea-reference','cycle-reference','cli'}
    if manifest.get('sanitizer_enabled'): names.add('sanitizer-controls')
    checks=report.get('checks',[])
    if (type(report.get('schema_version')) is not int or report['schema_version'] != 2 or report.get('kind') != 'test' or report.get('status') != 'PASS'
        or report.get('build_manifest_sha256') != manifest_sha256
        or report.get('binary_sha256') != manifest['application']['sha256']
        or report.get('configuration') != manifest.get('configuration')
        or not isinstance(checks,list) or len(checks) != len(names)
        or any(not isinstance(c,dict) or c.get('status') != 'PASS' for c in checks)
        or any(not isinstance(c.get('name'),str) for c in checks) or {c.get('name') for c in checks} != names
        or type(report.get('cli_skipped')) is not int or report['cli_skipped'] != 0
        or any(type(report.get(k)) is not int or report[k] <= 0 for k in
               ('core_checks','adapter_checks','thermo_checks','combustion_checks','cycle_checks','cli_groups',
                'parameter_data_groups','thermo_data_groups','cea_reference_groups','cycle_reference_groups'))):
        raise ValueError('Test evidence incomplete or inconsistent')


def execute(arguments,root,log_path,timeout=180):
    try:
        completed=subprocess.run([str(x) for x in arguments],cwd=root,capture_output=True,encoding="utf-8",errors="replace",timeout=timeout,check=False,env=subprocess_env())
    except subprocess.TimeoutExpired as exc:
        atomic_text(log_path,"TIMEOUT\n"+str(exc))
        raise ValueError(f"Command timed out; log: {log_path}") from exc
    atomic_text(log_path,completed.stdout+completed.stderr)
    if completed.returncode:
        raise ValueError(f"Command exited {completed.returncode}; log: {log_path}\n"+(completed.stdout+completed.stderr)[-3000:])
    return completed.stdout+completed.stderr


def build(root=ROOT,configuration="Debug",compiler="gcc",sanitize=False):
    name=config_name(configuration,sanitize)
    executable=shutil.which(compiler)
    if executable is None: raise ValueError(f"Compiler not found: {compiler}")
    with lock(root,"build-"+name):
        attempt=root/"build/artifacts"/name/uuid.uuid4().hex
        attempt.mkdir(parents=True,exist_ok=False)
        pointer=root/"build"/name/"latest.json"
        manifest_path=attempt/"build-manifest.json"
        manifest={"schema_version":2,"kind":"build","status":"RUNNING","started_at":now(),"configuration":configuration,
                  "compiler":executable,"sanitizer_enabled":sanitize,"inputs":[],"commands":[]}
        atomic_json(manifest_path,manifest)
        atomic_json(pointer,{"manifest":manifest_path.relative_to(root).as_posix()})
        try:
            before=source_records(root)
            modules={m['id']:m for m in read_json(root/"project/modules.json")["modules"]}
            core=modules["core"]["sources"]+modules["nozzle"]["sources"]+modules["thermo"]["sources"]+modules["cycle"]["sources"]
            adapters=modules["adapters"]["sources"]+modules["cli"]["sources"]
            flags=['-std=c17','-Wall','-Wextra','-Wpedantic','-Werror','-Wconversion','-Wshadow','-Wstrict-prototypes','-Wmissing-prototypes','-fno-common','-Iinclude','-Isrc/adapters']
            flags += ['-O0','-g3'] if configuration=="Debug" else ['-O2','-DNDEBUG']
            if sanitize: flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
            suffix='.exe' if os.name=='nt' else ''
            app=attempt/("rocketperf"+suffix); unit=attempt/("test_core"+suffix); adapter=attempt/("test_adapters"+suffix); thermo=attempt/("test_thermo"+suffix)
            combustion=attempt/("test_combustion"+suffix)
            cycle=attempt/("test_cycle"+suffix)
            commands=[[executable,*flags,*(['-municode'] if os.name=='nt' else []),*core,*adapters,'-lm','-o',str(app)],
                      [executable,*flags,*core,'tests/test_core.c','-lm','-o',str(unit)],
                      [executable,*flags,*core,*modules['adapters']['sources'],'tests/test_adapters.c','-lm','-o',str(adapter)],
                      [executable,*flags,*core,'tests/test_thermo.c','-lm','-o',str(thermo)],
                      [executable,*flags,*core,'tests/test_combustion.c','-lm','-o',str(combustion)],
                      [executable,*flags,*core,'tests/test_cycle.c','-lm','-o',str(cycle)]]
            if sanitize:
                commands.append([executable,*flags,'tests/fixtures/sanitizer_probe.c','-o',str(attempt/'sanitizer_probe')])
            version=execute([executable,'--version'],root,attempt/'compiler.log',30).splitlines()[0]
            for index,command in enumerate(commands): execute(command,root,attempt/f'compile-{index}.log')
            if source_records(root)!=before: raise ValueError("Sources changed while compiling; build not published")
            manifest.update(status="PASS",compiler_version=version,flags=flags,inputs=before,commands=commands,
                            application={"path":app.relative_to(root).as_posix(),"sha256":digest(app)},
                            core_test={"path":unit.relative_to(root).as_posix(),"sha256":digest(unit)},
                            adapter_test={"path":adapter.relative_to(root).as_posix(),"sha256":digest(adapter)},
                            thermo_test={"path":thermo.relative_to(root).as_posix(),"sha256":digest(thermo)},
                            combustion_test={"path":combustion.relative_to(root).as_posix(),"sha256":digest(combustion)},
                            cycle_test={"path":cycle.relative_to(root).as_posix(),"sha256":digest(cycle)})
            if sanitize: manifest['sanitizer_probe']={'path':(attempt/'sanitizer_probe').relative_to(root).as_posix(),'sha256':digest(attempt/'sanitizer_probe')}
            # Compatibility aliases. Consumers must use the manifest pointer, not trust old aliases.
            for output in (app,unit,adapter,thermo,combustion,cycle):
                destination=root/'build'/name/output.name
                temporary=destination.with_name('.'+output.name+'.'+uuid.uuid4().hex)
                shutil.copy2(output,temporary); os.replace(temporary,destination)
        except Exception as exc:
            manifest.update(status="FAIL",error=str(exc))
            raise
        finally:
            manifest['finished_at']=now(); atomic_json(manifest_path,manifest)
            atomic_json(root/'build'/name/'build-manifest.json',manifest)
        print(f"Build PASS: {name} ({attempt.name[:8]})")
        return manifest_path


def verified_build(root,configuration="Debug",sanitize=False,require_tests=False):
    name=config_name(configuration,sanitize)
    pointer=read_json(root/'build'/name/'latest.json')
    path=local_path(root,pointer['manifest']); manifest=read_json(path)
    if manifest.get('status')!='PASS' or manifest.get('kind')!='build': raise ValueError("Latest build attempt did not pass")
    if manifest['inputs']!=source_records(root): raise ValueError("Build is stale for current source inputs")
    for field in ('application','core_test','adapter_test','thermo_test','combustion_test','cycle_test',*(['sanitizer_probe'] if sanitize else [])):
        artifact=local_path(root,manifest[field]['path'])
        if not artifact.is_file() or digest(artifact)!=manifest[field]['sha256']: raise ValueError("Build artifact hash mismatch")
    if require_tests:
        report=read_json(path.parent/'test-report.json')
        verify_test_report(report,manifest,digest(path))
        if report.get('validation_inputs')!=test_records(root):
            raise ValueError("Test evidence missing, failed or stale")
    return path


def test(root=ROOT,configuration="Debug",compiler="gcc",sanitize=False,python=sys.executable):
    path=build(root,configuration,compiler,sanitize)
    manifest=read_json(path)
    name=config_name(configuration,sanitize)
    report_path=path.parent/'test-report.json'
    report={"schema_version":2,"kind":"test","status":"RUNNING","started_at":now(),"configuration":configuration,"checks":[],"validation_inputs":[],"build_manifest_sha256":digest(path)}
    atomic_json(report_path,report)
    atomic_json(root/'build'/name/'test-report.json',report)
    try:
        report['validation_inputs']=test_records(root)
        atomic_json(report_path,report)
        core_log=execute([local_path(root,manifest['core_test']['path'])],root,path.parent/'core-test.log')
        adapter_log=execute([local_path(root,manifest['adapter_test']['path'])],root,path.parent/'adapter-test.log')
        thermo_log=execute([local_path(root,manifest['thermo_test']['path'])],root,path.parent/'thermo-test.log')
        combustion_log=execute([local_path(root,manifest['combustion_test']['path'])],root,path.parent/'combustion-test.log')
        cycle_log=execute([local_path(root,manifest['cycle_test']['path'])],root,path.parent/'cycle-test.log')
        cli_log=execute([python,'tests/test_cli.py','--binary',local_path(root,manifest['application']['path'])],root,path.parent/'cli-test.log')
        cli_count=cli_test_count(cli_log)
        parameter_log=execute([python,'-m','unittest','discover','-s','tests','-p','test_data.py','-v'],root,path.parent/'parameter-data-test.log')
        data_log=execute([python,'-m','unittest','discover','-s','tests','-p','test_thermo_data.py','-v'],root,path.parent/'thermo-data-test.log')
        reference_log=execute([python,'-m','unittest','discover','-s','tests','-p','test_cea_reference.py','-v'],root,path.parent/'cea-reference-test.log')
        cycle_reference_log=execute([python,'-m','unittest','discover','-s','tests','-p','test_cycle_reference.py','-v'],root,path.parent/'cycle-reference-test.log')
        if sanitize:
            probe=local_path(root,manifest['sanitizer_probe']['path'])
            for mode,expected in [('address','ERROR: AddressSanitizer'),('undefined','runtime error: signed integer overflow')]:
                completed=subprocess.run([str(probe),mode],cwd=root,capture_output=True,text=True,timeout=15,env=subprocess_env())
                output=completed.stdout+completed.stderr
                atomic_text(path.parent/(mode+'-probe.log'),output)
                if completed.returncode==0 or expected not in output: raise ValueError(f'{mode} negative control did not detect its deliberate defect')
        if manifest['inputs']!=source_records(root) or report['validation_inputs']!=test_records(root): raise ValueError("Validation inputs changed during tests")
        report.update(status='PASS',checks=[{"name":name,"status":"PASS"} for name in ('core','adapters','thermo','combustion','cycle','parameter-data','thermo-data','cea-reference','cycle-reference','cli',*(['sanitizer-controls'] if sanitize else []))],
                      core_checks=int(re.search(r'core: (\d+) checks',core_log).group(1)),
                      adapter_checks=int(re.search(r'adapters: (\d+) checks',adapter_log).group(1)),
                      thermo_checks=int(re.search(r'thermo: (\d+) checks',thermo_log).group(1)),
                      combustion_checks=int(re.search(r'combustion: (\d+) checks',combustion_log).group(1)),
                      cycle_checks=int(re.search(r'cycle: (\d+) checks',cycle_log).group(1)),
                      cli_groups=cli_count,cli_skipped=0,
                      parameter_data_groups=cli_test_count(parameter_log),
                      thermo_data_groups=cli_test_count(data_log),
                      cea_reference_groups=cli_test_count(reference_log),
                      cycle_reference_groups=cli_test_count(cycle_reference_log),
                      binary_sha256=manifest['application']['sha256'])
        print(core_log.strip()); print(adapter_log.strip()); print(thermo_log.strip()); print(combustion_log.strip()); print(cycle_log.strip()); print(f"CLI: {report['cli_groups']} groups PASS")
    except Exception as exc:
        report.update(status='FAIL',error=str(exc)); raise
    finally:
        report['finished_at']=now(); atomic_json(report_path,report)
        atomic_json(root/'build'/name/'test-report.json',report)
    return path


def run_case(root,case_path,configuration='Release',run_id=None,no_build=False,timeout=15,study=False,area_ratios=None,ambient_pressures=None,model='ideal',cycle_field=None,cycle_values=None):
    if (cycle_field is None) != (cycle_values is None) or (cycle_field is not None and study): raise ValueError('Cycle study requires field/values and excludes S1')
    if cycle_field is not None:
        from cycle_study import FIELDS
        if cycle_field not in FIELDS: raise ValueError('Unsupported cycle study field')
        cycle_axis=grid_axis(cycle_values,True)
    if model not in {'ideal','prescribed-cycle'}: raise ValueError('Unsupported run model')
    if study and model != 'ideal': raise ValueError('Study grid is currently only supported by the ideal nozzle')
    if not study and (area_ratios is not None or ambient_pressures is not None): raise ValueError('Grid options require --study')
    ratios=grid_axis(area_ratios) if area_ratios is not None else DEFAULT_RATIOS.copy()
    pressures=grid_axis(ambient_pressures,True) if ambient_pressures is not None else DEFAULT_PRESSURES.copy()
    run_id=run_id or 'run_'+uuid.uuid4().hex[:16]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,100}',run_id): raise ValueError("Unsafe RunId")
    case_path=Path(case_path)
    if not case_path.is_absolute(): case_path=root/case_path
    folder=local_path(root,'results/local/'+run_id)
    folder.mkdir(parents=True,exist_ok=False)  # Atomic reservation; race cannot overwrite a run.
    record={"schema_version":2,"kind":"run","run_id":run_id,"status":"PREPARING","started_at":now(),"original_case_path":str(case_path)}
    atomic_json(folder/'run-manifest.json',record)
    try:
        case_path=case_path.resolve(strict=True)
        if not case_path.is_file(): raise ValueError('Case input must be a regular file')
        record['original_case_path']=str(case_path)
        shutil.copy2(case_path,folder/'input.ini')
        record['input_sha256']=digest(folder/'input.ini')
        try: build_path=verified_build(root,configuration,require_tests=True)
        except (ValueError,OSError,KeyError):
            if no_build: raise ValueError("No fresh tested build; run test first or omit --no-build")
            build_path=test(root,configuration)
        build_manifest=read_json(build_path)
        source_binary=local_path(root,build_manifest['application']['path'])
        executable=folder/source_binary.name
        shutil.copy2(source_binary,executable)
        shutil.copy2(build_path,folder/'build-manifest.json')
        shutil.copy2(build_path.parent/'test-report.json',folder/'test-report.json')
        if digest(executable)!=build_manifest['application']['sha256']: raise ValueError("Binary changed during snapshot")
        if digest(folder/'build-manifest.json') != digest(build_path): raise ValueError('Build manifest changed during snapshot')
        verify_test_report(read_json(folder/'test-report.json'),build_manifest,digest(folder/'build-manifest.json'))
        if read_json(folder/'test-report.json')['validation_inputs'] != test_records(root):
            raise ValueError('Test inputs changed during snapshot')
        arguments=['study','area-ratio-ambient','input.ini','--area-ratios',','.join(map(str,ratios)),'--ambient-pressures',','.join(map(str,pressures))] if study else (['cycle','prescribed','input.ini'] if model=='prescribed-cycle' else ['run','input.ini'])
        if cycle_field is not None: arguments=['study','prescribed-cycle','input.ini',cycle_field,','.join(map(str,cycle_axis))]
        record.update(status='RUNNING',executable_sha256=digest(executable),build_manifest_sha256=digest(folder/'build-manifest.json'),test_report_sha256=digest(folder/'test-report.json'),command=[executable.name,*arguments])
        if study: record['requested_grid']={'area_ratios':ratios,'ambient_pressures_pa':pressures}
        if cycle_field is not None: record['requested_axis']={'field':cycle_field,'values':cycle_axis}
        atomic_json(folder/'run-manifest.json',record)
        completed=subprocess.run([str(executable),*arguments],cwd=folder,capture_output=True,encoding='utf-8',errors='strict',timeout=timeout,check=False,env=subprocess_env())
        atomic_text(folder/'stdout.txt',completed.stdout); atomic_text(folder/'stderr.txt',completed.stderr)
        record['exit_code']=completed.returncode
        if completed.returncode: raise ValueError(f"Case rejected with exit {completed.returncode}")
        if completed.stderr: raise ValueError("Success path unexpectedly wrote stderr")
        data=strict_json(completed.stdout)
        input_text=(folder/'input.ini').read_text(encoding='utf-8-sig')
        if cycle_field is not None:
            from cycle_study import validate_study as validate_cycle_study
            record['study_validation']=validate_cycle_study(data,input_text,cycle_field,cycle_axis,root)
        elif study: record['point_counts']=validate_study(data,input_text,ratios,pressures)
        elif model=='prescribed-cycle':
            from cycle_validation import VALIDATION_VERSION, validate_cycle
            record['accounting_checks']=len(validate_cycle(data,input_text))
            record['validation_version']=VALIDATION_VERSION
        else: validate_result(data,input_text)
        if digest(folder/'input.ini')!=record['input_sha256']: raise ValueError("Input changed during execution")
        atomic_text(folder/'result.json',completed.stdout)
        record.update(status='SUCCESS',output_file='result.json',output_sha256=digest(folder/'result.json'))
    except Exception as exc:
        record.update(status='FAILED',error=str(exc),timed_out=isinstance(exc,subprocess.TimeoutExpired))
        if isinstance(exc,subprocess.TimeoutExpired):
            for filename,output in (('stdout.txt',exc.stdout),('stderr.txt',exc.stderr)):
                if output is not None:
                    atomic_text(folder/filename,output.decode('utf-8',errors='replace') if isinstance(output,bytes) else output)
        if not (folder/'stderr.txt').exists(): atomic_text(folder/'stderr.txt',str(exc)+'\n')
        raise ValueError(f"Run failed; diagnostics preserved: {folder}: {exc}") from exc
    finally:
        record['finished_at']=now(); atomic_json(folder/'run-manifest.json',record)
    print(f"Run SUCCESS: {folder}")
    return folder


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('build','test'):
        p=sub.add_parser(name);p.add_argument('--configuration',choices=['Debug','Release'],default='Debug');p.add_argument('--compiler',default='gcc');p.add_argument('--sanitize',action='store_true');p.add_argument('--python',default=sys.executable)
    p=sub.add_parser('run');p.add_argument('--case',default='cases/benchmarks/air_mach2_vacuum.ini');p.add_argument('--configuration',choices=['Debug','Release'],default='Release');p.add_argument('--run-id');p.add_argument('--no-build',action='store_true')
    p.add_argument('--study',choices=['area-ratio-ambient']);p.add_argument('--area-ratios');p.add_argument('--ambient-pressures')
    p.add_argument('--model',choices=['ideal','prescribed-cycle'],default='ideal')
    p.add_argument('--cycle-field');p.add_argument('--cycle-values')
    args=parser.parse_args()
    if args.command=='build': build(ROOT,args.configuration,args.compiler,args.sanitize)
    elif args.command=='test': test(ROOT,args.configuration,args.compiler,args.sanitize,args.python)
    else: run_case(ROOT,args.case,args.configuration,args.run_id,args.no_build,study=bool(args.study),area_ratios=args.area_ratios,ambient_pressures=args.ambient_pressures,model=args.model,cycle_field=args.cycle_field,cycle_values=args.cycle_values)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try: main()
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        print(f"pipeline: {exc}",file=sys.stderr);sys.exit(1)
