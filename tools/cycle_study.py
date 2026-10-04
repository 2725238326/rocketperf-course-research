"""Validate and archive C-generated prescribed-state studies; no production physics solve."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import shutil
import sys
import uuid

from projectlib import ROOT, atomic_json, digest, git, local_path, now, read_json
from cycle_validation import validate_cycle

FIELDS = {'main_area_ratio', 'ambient_pressure_pa', 'branch_axial_projection', 'turbine_efficiency',
          'chamber_temperature_k', 'overall_oxidizer_fuel_ratio', 'fuel_pump_efficiency', 'oxidizer_pump_efficiency'}
METRICS = {'thrust_change_n', 'isp_change_s', 'branch_flow_change_kg_per_s', 'required_heat_change_w',
           'main_exit_area_m2', 'main_exit_diameter_m', 'main_exit_area_change_m2', 'thrust_relative_change',
           'isp_relative_change', 'elasticity_defined', 'thrust_secant_elasticity', 'isp_secant_elasticity'}


def changed_snapshot(text, field, value):
    lines = text.splitlines(); matches = 0
    for index, line in enumerate(lines):
        if line.partition('=')[0].strip() == field:
            lines[index] = field + '=' + format(value, '.17g'); matches += 1
    if matches != 1: raise ValueError('Expected one study input field')
    return '\n'.join(lines) + '\n'


def validate_study(report, input_text, field, values, root=ROOT):
    if (not isinstance(report, dict) or set(report) != {'schema_version', 'study', 'field', 'baseline', 'points', 'limitations'}
        or type(report['schema_version']) is not int or report['schema_version'] != 1
        or report['study'] != 'prescribed_cycle_scan_v1' or report['field'] != field or field not in FIELDS):
        raise ValueError('Invalid cycle study schema/axis')
    if not values or any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid cycle study values')
    checks = len(validate_cycle(report['baseline'], input_text, root))
    base = report['baseline']; points = report['points']
    if not isinstance(points,list) or len(points) != len(values): raise ValueError('Study point count mismatch')
    counts = {'ok':0, 'out_of_domain':0, 'invalid_argument':0}
    def same(actual, expected, name):
        if type(actual) not in (int,float) or not math.isfinite(actual) or not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-7):
            raise ValueError('Invalid cycle study metric: '+name)
    for point, value in zip(points,values):
        if not isinstance(point,dict) or type(point.get('value')) not in (int,float) or point['value'] != value:
            raise ValueError('Study coordinate mismatch')
        status = point.get('status')
        if status not in counts: raise ValueError('Unexpected numeric failure in study')
        if status == 'ok':
            if set(point) != {'value','status','report','metrics'}: raise ValueError('Invalid successful study point')
            r = point['report']; m = point['metrics']
            checks += len(validate_cycle(r, changed_snapshot(input_text, field, value), root))
            if not isinstance(m,dict) or set(m) != METRICS or type(m['elasticity_defined']) is not bool:
                raise ValueError('Invalid study metrics schema')
            bp=base['performance']; rp=r['performance']; bi=base['inputs']; ri=r['inputs']
            area=rp['main_throat_area_m2']*ri['main_area_ratio']
            thrust=rp['total_thrust_n']-bp['total_thrust_n']; isp=rp['engine_specific_impulse_s']-bp['engine_specific_impulse_s']
            expected={'thrust_change_n':thrust,'isp_change_s':isp,
                'branch_flow_change_kg_per_s':r['flows']['branch_mass_flow_kg_per_s']-base['flows']['branch_mass_flow_kg_per_s'],
                'required_heat_change_w':sum(r['energy'][key]-base['energy'][key] for key in ('generator_required_heat_w','chamber_required_heat_w')),
                'main_exit_area_m2':area,'main_exit_diameter_m':math.sqrt(4*area/math.pi),
                'main_exit_area_change_m2':area-bp['main_throat_area_m2']*bi['main_area_ratio'],
                'thrust_relative_change':thrust/bp['total_thrust_n'],'isp_relative_change':isp/bp['engine_specific_impulse_s']}
            defined=bi[field] != 0 and value != bi[field]
            if m['elasticity_defined'] != defined: raise ValueError('Incorrect elasticity defined flag')
            fraction=(value-bi[field])/bi[field] if defined else 1
            expected['thrust_secant_elasticity']=expected['thrust_relative_change']/fraction if defined else 0
            expected['isp_secant_elasticity']=expected['isp_relative_change']/fraction if defined else 0
            for key, result in expected.items(): same(m[key],result,key)
        else:
            if set(point) != {'value','status','error'} or not isinstance(point['error'],str) or not point['error']:
                raise ValueError('Invalid failed study point')
            # Prove only exclusions whose cause can be checked without an extra
            # Python cycle/nozzle solver. Unsubstantiated exclusions fail archive.
            invalid=((field in {'turbine_efficiency','fuel_pump_efficiency','oxidizer_pump_efficiency'} and not 0 < value <= 1)
                     or (field=='branch_axial_projection' and not 0 <= value <= 1)
                     or (field in {'chamber_temperature_k','overall_oxidizer_fuel_ratio'} and value <= 0)
                     or (field=='main_area_ratio' and not 1 <= value <= 1e4))
            excluded=(field=='ambient_pressure_pa' and value > min(base['main_nozzle']['exit']['gas']['pressure_pa'],
                       base['branch_nozzle']['exit']['gas']['pressure_pa'] if base['branch_nozzle'] else math.inf))
            if not ((status=='invalid_argument' and invalid) or (status=='out_of_domain' and excluded)):
                raise ValueError('Study exclusion cannot be substantiated from archived states')
        counts[status] += 1
    limits=report['limitations']
    if not isinstance(limits,list) or not limits or any(not isinstance(v,str) or not v.strip() for v in limits):
        raise ValueError('Study limitations missing')
    return {'counts':counts,'state_checks':checks,'metric_checks':len(METRICS)*counts['ok']}


def archive(destination, case='cases/benchmarks/prescribed_cycle.ini'):
    import pipeline
    target_folder=local_path(ROOT,destination)
    if target_folder.exists(): raise FileExistsError('Research destination already exists')
    # Generate below ignored build, then publish once. Adding a tracked archive
    # changes the test identity; do not invalidate it mid-way through a study.
    folder=ROOT/'build/research-draft'/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=False)
    manifest={'schema_version':1,'kind':'cycle-research','status':'PREPARING','started_at':now(),
              'source_head':git(ROOT,'rev-parse','HEAD').stdout.strip(),'source_dirty':bool(git(ROOT,'status','--porcelain').stdout.strip()),
              'scope':'Synthetic fixed-state study; no flight engine claim, experimental error bar or whole-cycle independent reference.', 'runs':[]}
    atomic_json(folder/'manifest.json',manifest)
    studies={
        'main_area_ratio':[10,20,40], 'ambient_pressure_pa':[0,1000,5000,25000,50000,101325],
        'branch_axial_projection':[0,0.5,1], 'turbine_efficiency':[0.693,0.7,0.707],
        'chamber_temperature_k':[3267,3300,3333], 'overall_oxidizer_fuel_ratio':[3.366,3.4,3.434],
        'fuel_pump_efficiency':[0.693,0.7,0.707], 'oxidizer_pump_efficiency':[0.7425,0.75,0.7575]}
    input_text=local_path(ROOT,case).read_text(encoding='utf-8-sig')
    recipes=[(field,field,values,case) for field,values in studies.items()]
    for area in (20,40):
        path=folder/'inputs'/('area'+str(area)+'.ini')
        from projectlib import atomic_text
        atomic_text(path,changed_snapshot(input_text,'main_area_ratio',area))
        recipes.append(('area'+str(area)+'_ambient_pressure','ambient_pressure_pa',studies['ambient_pressure_pa'],path))
    try:
        for study_id,field,values,study_case in recipes:
            run=pipeline.run_case(ROOT,study_case,no_build=True,cycle_field=field,cycle_values=','.join(map(str,values)))
            target=folder/study_id;target.mkdir()
            for name in ('input.ini','stdout.txt','stderr.txt','result.json','build-manifest.json','test-report.json','run-manifest.json'):
                shutil.copy2(run/name,target/name)
            manifest['runs'].append({'field':field,'values':values,'directory':study_id,
                'validation':validate_study(read_json(target/'result.json'),(target/'input.ini').read_text(encoding='utf-8-sig'),field,values)})
        manifest['status']='PASS'
        manifest['files']=[{'path':p.relative_to(folder).as_posix(),'sha256':digest(p)} for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='manifest.json']
    except Exception as exc:
        manifest.update(status='FAIL',error=str(exc));raise
    finally:
        manifest['finished_at']=now();atomic_json(folder/'manifest.json',manifest)
    target_folder.parent.mkdir(parents=True,exist_ok=True)
    folder.rename(target_folder)
    return target_folder


def verify(folder, root=ROOT):
    manifest=read_json(folder/'manifest.json')
    if (not isinstance(manifest,dict) or type(manifest.get('schema_version')) is not int or manifest['schema_version']!=1
        or manifest.get('status')!='PASS' or manifest.get('kind')!='cycle-research'):
        raise ValueError('Research archive not PASS')
    paths={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json'}
    records=manifest.get('files')
    if (not isinstance(records,list) or len(records)!=len(paths)
        or any(not isinstance(r,dict) or set(r)!={'path','sha256'} or not isinstance(r['path'],str) or not isinstance(r['sha256'],str) for r in records)
        or {r['path'] for r in records}!=paths):
        raise ValueError('Research file inventory mismatch')
    for record in records:
        if digest(local_path(folder,record['path']))!=record['sha256']: raise ValueError('Research file hash mismatch')
    runs=manifest['runs']
    if (not isinstance(runs,list) or len(runs)!=10
        or any(not isinstance(r,dict) or set(r)!={'field','values','directory','validation'} or not isinstance(r['field'],str) or not isinstance(r['directory'],str) for r in runs)
        or {r['field'] for r in runs}!=FIELDS
        or {r['directory'] for r in runs}!=FIELDS|{'area20_ambient_pressure','area40_ambient_pressure'}):
        raise ValueError('Research axes incomplete')
    for run in manifest['runs']:
        path=local_path(folder,run['directory'])
        if run['directory'] not in {run['field'],'area20_ambient_pressure','area40_ambient_pressure'}: raise ValueError('Research directory/axis mismatch')
        result=read_json(path/'result.json'); text=(path/'input.ini').read_text(encoding='utf-8-sig')
        if validate_study(result,text,run['field'],run['values'],root)!=run['validation']: raise ValueError('Research validation mismatch')
        record=read_json(path/'run-manifest.json');build=read_json(path/'build-manifest.json');test=read_json(path/'test-report.json')
        from pipeline import verify_test_report
        verify_test_report(test,build,digest(path/'build-manifest.json'))
        if (record['status']!='SUCCESS' or record['output_sha256']!=digest(path/'result.json')
            or record['input_sha256']!=digest(path/'input.ini') or record['executable_sha256']!=build['application']['sha256']
            or record['test_report_sha256']!=digest(path/'test-report.json')
            or (path/'stdout.txt').read_bytes()!=(path/'result.json').read_bytes() or (path/'stderr.txt').read_bytes()):
            raise ValueError('Research run provenance mismatch')
        if record['requested_axis']!={'field':run['field'],'values':run['values']}:
            raise ValueError('Research run/manifest axis mismatch')
    # Cross-run checks prove the single baseline and dataset were not silently
    # changed between scans. Only two documented grid cases change area ratio.
    reference=read_json(folder/'main_area_ratio/result.json')['baseline']
    for run in runs:
        base=read_json(local_path(folder,run['directory'])/'result.json')['baseline']
        expected=dict(reference['inputs'])
        if run['directory'].startswith('area20_'): expected['main_area_ratio']=20
        if run['directory'].startswith('area40_'): expected['main_area_ratio']=40
        if base['inputs']!=expected or any(base[key]!=reference[key] for key in ('dataset_id','model','boundary','case')):
            raise ValueError('Research baseline/data version changed across scans')
    return len(manifest['runs'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['archive','verify']);parser.add_argument('directory')
    args=parser.parse_args();sys.stdout.reconfigure(encoding='utf-8')
    try:
        print(archive(args.directory) if args.action=='archive' else 'Research verified: '+str(verify(local_path(ROOT,args.directory)))+' axes')
    except (ValueError,OSError,KeyError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(1)
