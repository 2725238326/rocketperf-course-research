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

from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, lock, now, read_json, subprocess_env

CORE_KEYS={"gamma","gas_constant_j_kg_k","stagnation_temperature_k","stagnation_pressure_pa","area_ratio","throat_area_m2","ambient_pressure_pa"}
RESULT_KEYS={"exit_mach","exit_temperature_k","exit_pressure_pa","exit_velocity_m_s","exit_area_m2","characteristic_velocity_m_s","mass_flow_kg_s","thrust_n","thrust_coefficient","specific_impulse_s"}
DEFAULT_RATIOS=[1,1.25,1.6875,2,4,8,16]
DEFAULT_PRESSURES=[0,25000,50000,100000]


def strict_json(text):
    def bad(value): raise ValueError(f"Non-finite JSON constant: {value}")
    return json.loads(text,parse_constant=bad)


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
    values=dict(line.strip().split('=',1) for line in input_text.lstrip('\ufeff').splitlines() if line.strip() and not line.strip().startswith('#'))
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
        else: raise ValueError('Calculation error is not an expected domain exclusion')
        counts[status]+=1
    if not re.fullmatch(r'\d+\.\d+\.\d+',str(report['program_version'])) or not isinstance(report['limitations'],list) or not report['limitations'] or any(not isinstance(x,str) or not x for x in report['limitations']):
        raise ValueError('Study version/limitations missing')
    return counts


def validate_result(report, input_text):
    required={"schema_version","program_version","model","case","inputs","results","diagnostics","limitations"}
    if not isinstance(report,dict) or set(report)!=required or type(report["schema_version"]) is not int or report["schema_version"]!=1:
        raise ValueError("Result does not match v1 report schema")
    values={}
    for line in input_text.lstrip('\ufeff').splitlines():
        line=line.strip()
        if not line or line.startswith('#'): continue
        key,sep,value=line.partition('=')
        if not sep or key.strip() in values: raise ValueError("Snapshot contains malformed/duplicate fields")
        values[key.strip()]=value.strip()
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
    if not isinstance(report["limitations"],list) or not report["limitations"] or any(not isinstance(x,str) for x in report["limitations"]): raise ValueError("Model limitations missing")


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
    sources += ["tests/test_core.c","tests/test_adapters.c","tests/test_thermo.c","tests/test_combustion.c","tests/reference/nasa9_cantera.h","tests/fixtures/sanitizer_probe.c","tools/pipeline.py","tools/projectlib.py","project/modules.json","scripts/build.ps1","CMakeLists.txt"]
    return file_records(root,sources)


def test_records(root):
    files=[p.relative_to(root).as_posix() for folder in ("tests","cases/benchmarks","data/thermo","results/validation") for p in (root/folder).rglob('*') if p.suffix in {'.c','.h','.py','.json','.ini','.tsv','.inp','.out'}]
    files += ['tools/thermo_data.py','tools/cea_reference.py','tools/combustion_reference.py']
    return file_records(root,files)


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
            core=modules["core"]["sources"]+modules["nozzle"]["sources"]+modules["thermo"]["sources"]
            adapters=modules["adapters"]["sources"]+modules["cli"]["sources"]
            flags=['-std=c17','-Wall','-Wextra','-Wpedantic','-Werror','-Wconversion','-Wshadow','-Wstrict-prototypes','-Wmissing-prototypes','-fno-common','-Iinclude','-Isrc/adapters']
            flags += ['-O0','-g3'] if configuration=="Debug" else ['-O2','-DNDEBUG']
            if sanitize: flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
            suffix='.exe' if os.name=='nt' else ''
            app=attempt/("rocketperf"+suffix); unit=attempt/("test_core"+suffix); adapter=attempt/("test_adapters"+suffix); thermo=attempt/("test_thermo"+suffix)
            combustion=attempt/("test_combustion"+suffix)
            commands=[[executable,*flags,*(['-municode'] if os.name=='nt' else []),*core,*adapters,'-lm','-o',str(app)],
                      [executable,*flags,*core,'tests/test_core.c','-lm','-o',str(unit)],
                      [executable,*flags,*core,*modules['adapters']['sources'],'tests/test_adapters.c','-lm','-o',str(adapter)],
                      [executable,*flags,*core,'tests/test_thermo.c','-lm','-o',str(thermo)],
                      [executable,*flags,*core,'tests/test_combustion.c','-lm','-o',str(combustion)]]
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
                            combustion_test={"path":combustion.relative_to(root).as_posix(),"sha256":digest(combustion)})
            if sanitize: manifest['sanitizer_probe']={'path':(attempt/'sanitizer_probe').relative_to(root).as_posix(),'sha256':digest(attempt/'sanitizer_probe')}
            # Compatibility aliases. Consumers must use the manifest pointer, not trust old aliases.
            for output in (app,unit,adapter,thermo,combustion):
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
    for field in ('application','core_test','adapter_test','thermo_test','combustion_test',*(['sanitizer_probe'] if sanitize else [])):
        artifact=local_path(root,manifest[field]['path'])
        if not artifact.is_file() or digest(artifact)!=manifest[field]['sha256']: raise ValueError("Build artifact hash mismatch")
    if require_tests:
        report=read_json(path.parent/'test-report.json')
        if report.get('status')!='PASS' or report.get('build_manifest_sha256')!=digest(path) or report.get('validation_inputs')!=test_records(root):
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
        cli_log=execute([python,'tests/test_cli.py','--binary',local_path(root,manifest['application']['path'])],root,path.parent/'cli-test.log')
        cli_count=cli_test_count(cli_log)
        data_log=execute([python,'-m','unittest','discover','-s','tests','-p','test_thermo_data.py','-v'],root,path.parent/'thermo-data-test.log')
        reference_log=execute([python,'-m','unittest','discover','-s','tests','-p','test_cea_reference.py','-v'],root,path.parent/'cea-reference-test.log')
        if sanitize:
            probe=local_path(root,manifest['sanitizer_probe']['path'])
            for mode,expected in [('address','ERROR: AddressSanitizer'),('undefined','runtime error: signed integer overflow')]:
                completed=subprocess.run([str(probe),mode],cwd=root,capture_output=True,text=True,timeout=15,env=subprocess_env())
                output=completed.stdout+completed.stderr
                atomic_text(path.parent/(mode+'-probe.log'),output)
                if completed.returncode==0 or expected not in output: raise ValueError(f'{mode} negative control did not detect its deliberate defect')
        if manifest['inputs']!=source_records(root) or report['validation_inputs']!=test_records(root): raise ValueError("Validation inputs changed during tests")
        report.update(status='PASS',checks=[{"name":name,"status":"PASS"} for name in ('core','adapters','thermo','combustion','thermo-data','cea-reference','cli',*(['sanitizer-controls'] if sanitize else []))],
                      core_checks=int(re.search(r'core: (\d+) checks',core_log).group(1)),
                      adapter_checks=int(re.search(r'adapters: (\d+) checks',adapter_log).group(1)),
                      thermo_checks=int(re.search(r'thermo: (\d+) checks',thermo_log).group(1)),
                      combustion_checks=int(re.search(r'combustion: (\d+) checks',combustion_log).group(1)),
                      cli_groups=cli_count,cli_skipped=0,
                      thermo_data_groups=int(re.search(r'Ran (\d+) tests',data_log).group(1)),
                      cea_reference_groups=int(re.search(r'Ran (\d+) tests',reference_log).group(1)),
                      binary_sha256=manifest['application']['sha256'])
        print(core_log.strip()); print(adapter_log.strip()); print(thermo_log.strip()); print(combustion_log.strip()); print(f"CLI: {report['cli_groups']} groups PASS")
    except Exception as exc:
        report.update(status='FAIL',error=str(exc)); raise
    finally:
        report['finished_at']=now(); atomic_json(report_path,report)
        atomic_json(root/'build'/name/'test-report.json',report)
    return path


def run_case(root,case_path,configuration='Release',run_id=None,no_build=False,timeout=15,study=False,area_ratios=None,ambient_pressures=None):
    if not study and (area_ratios is not None or ambient_pressures is not None): raise ValueError('Grid options require --study')
    ratios=grid_axis(area_ratios) if area_ratios is not None else DEFAULT_RATIOS.copy()
    pressures=grid_axis(ambient_pressures,True) if ambient_pressures is not None else DEFAULT_PRESSURES.copy()
    run_id=run_id or 'run_'+uuid.uuid4().hex[:16]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,100}',run_id): raise ValueError("Unsafe RunId")
    case_path=Path(case_path)
    if not case_path.is_absolute(): case_path=root/case_path
    case_path=case_path.resolve(strict=True)
    folder=local_path(root,'results/local/'+run_id)
    folder.mkdir(parents=True,exist_ok=False)  # Atomic reservation; race cannot overwrite a run.
    record={"schema_version":2,"kind":"run","run_id":run_id,"status":"PREPARING","started_at":now(),"original_case_path":str(case_path)}
    atomic_json(folder/'run-manifest.json',record)
    try:
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
        arguments=['study','area-ratio-ambient','input.ini','--area-ratios',','.join(map(str,ratios)),'--ambient-pressures',','.join(map(str,pressures))] if study else ['run','input.ini']
        record.update(status='RUNNING',executable_sha256=digest(executable),build_manifest_sha256=digest(folder/'build-manifest.json'),test_report_sha256=digest(folder/'test-report.json'),command=[executable.name,*arguments])
        if study: record['requested_grid']={'area_ratios':ratios,'ambient_pressures_pa':pressures}
        atomic_json(folder/'run-manifest.json',record)
        completed=subprocess.run([str(executable),*arguments],cwd=folder,capture_output=True,encoding='utf-8',errors='strict',timeout=timeout,check=False,env=subprocess_env())
        atomic_text(folder/'stdout.txt',completed.stdout); atomic_text(folder/'stderr.txt',completed.stderr)
        record['exit_code']=completed.returncode
        if completed.returncode: raise ValueError(f"Case rejected with exit {completed.returncode}")
        if completed.stderr: raise ValueError("Success path unexpectedly wrote stderr")
        data=strict_json(completed.stdout)
        input_text=(folder/'input.ini').read_text(encoding='utf-8-sig')
        if study: record['point_counts']=validate_study(data,input_text,ratios,pressures)
        else: validate_result(data,input_text)
        if digest(folder/'input.ini')!=record['input_sha256']: raise ValueError("Input changed during execution")
        atomic_text(folder/'result.json',completed.stdout)
        record.update(status='SUCCESS',output_file='result.json',output_sha256=digest(folder/'result.json'))
    except Exception as exc:
        record.update(status='FAILED',error=str(exc),timed_out=isinstance(exc,subprocess.TimeoutExpired))
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
    args=parser.parse_args()
    if args.command=='build': build(ROOT,args.configuration,args.compiler,args.sanitize)
    elif args.command=='test': test(ROOT,args.configuration,args.compiler,args.sanitize,args.python)
    else: run_case(ROOT,args.case,args.configuration,args.run_id,args.no_build,study=bool(args.study),area_ratios=args.area_ratios,ambient_pressures=args.ambient_pressures)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try: main()
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        print(f"pipeline: {exc}",file=sys.stderr);sys.exit(1)
