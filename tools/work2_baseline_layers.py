"""Fresh layered CLI checks and selected WBASE evidence verification (stdlib only)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from projectlib import ROOT, atomic_json, digest, now, read_json
from work2_baseline import ARCHIVE, IGNORED_OUTPUT, SPECIES, assess_gas, logged, verify as verify_base


def parsed_reference(output,card):
    from cea_reference import parse_output
    text=Path(card).read_text(encoding='ascii')
    match=re.search(r'\btrace\s*=\s*([0-9.eE+-]+)',text)
    if match is None: raise ValueError('Reference card has no trace threshold')
    rocket=bool(re.search(r'\brocket\b',text));frozen=bool(re.search(r'\bfrozen\b',text))
    return parse_output(Path(output).read_bytes(),rocket=rocket,frozen=frozen,trace_threshold=float(match[1]))


def execute(run_id, base_folder):
    from pipeline import verified_build
    from combustion_reference import run_reference, compare_report
    from cea_reference import parse_output
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',run_id): raise ValueError('Unsafe RunId')
    base_folder=Path(base_folder).resolve()
    verify_base(base_folder)
    folder=ROOT/'build/work2/baseline'/run_id;folder.mkdir(parents=True,exist_ok=False)
    build_path=verified_build(ROOT,'Debug',require_tests=True);build=read_json(build_path)
    binary=ROOT/build['application']['path']
    record=dict(schema_version=1,kind='work2-baseline-layers',status='RUNNING',run_id=run_id,started_at=now(),
                base_manifest_sha256=digest(base_folder/'manifest.json'),binary_sha256=digest(binary),
                inlet_cases=[],rejections=[],issues=[],source_snapshots=[])
    atomic_json(folder/'manifest.json',record)
    try:
        for name in ('build-manifest.json','test-report.json','core-test.log','thermo-test.log','combustion-test.log','cycle-test.log','cli-test.log','thermo-data-test.log','cea-reference-test.log'):
            shutil.copy2(build_path.parent/name,folder/name)
        for source in read_json(base_folder/'manifest.json')['research_tool_inputs']:
            if digest(ROOT/source['path'])!=source['sha256']: raise ValueError('Original research tool changed before source capture')
            target=folder/'source-snapshots'/Path(source['path']).name;target.parent.mkdir(exist_ok=True)
            shutil.copy2(ROOT/source['path'],target);record['source_snapshots'].append(source)
        layer_tool='tools/work2_baseline_layers.py'
        shutil.copy2(ROOT/layer_tool,folder/'source-snapshots'/Path(layer_tool).name)
        record['source_snapshots'].append(dict(path=layer_tool,sha256=digest(ROOT/layer_tool)))
        record['gas_cea']=run_reference(binary,folder/'gas-cea')
        for group,selected,collection,suffix,rocket in [
            ('liquid_anchor_v1',['base_hp','base_A10','base_A40'],'runs','-stdout.txt','base_rocket'),
            ('liquid_combustion_v1',['base_hp','base_A10','base_A40'],'runs','-stdout.txt','base_rocket'),
            ('kerosene_anchor_v1',['of_2_6_hp','of_2_6_A10','of_2_6_A40'],'recipes','-c-stdout.json','of_2_6_rocket')]:
            old=ROOT/'results/validation'/group;manifest=read_json(old/'manifest.json')
            recipes={r['id']:r for r in manifest[collection]}
            for identity in selected:
                arguments=recipes[identity]['arguments'];mode=arguments[1]
                reference_id=identity if identity.endswith('_hp') else rocket
                ref=old/(reference_id+'.out');card=old/(reference_id+'.inp')
                expected=read_json(old/(identity+suffix))['inputs']
                area=None if identity.endswith('_hp') else 10 if identity.endswith('A10') else 40
                name=group+'-'+identity
                run, process=logged([binary,*arguments],folder,name,30)
                if run.returncode or run.stderr: raise ValueError('Layered inlet CLI failed: '+name)
                report=json.loads(run.stdout)
                comparisons=compare_report(report,{'summary':parsed_reference(ref,card)},mode,area,expected_inputs=expected)
                local_ref=folder/(group+'-'+reference_id+'.out');local_card=folder/(group+'-'+reference_id+'.inp')
                if not local_ref.exists(): shutil.copy2(ref,local_ref)
                if not local_card.exists(): shutil.copy2(card,local_card)
                record['inlet_cases'].append(dict(id=name,arguments=arguments,mode=mode,area=area,expected_inputs=expected,
                    reference_file=local_ref.name,reference_card=local_card.name,original_reference=ref.relative_to(ROOT).as_posix(),
                    original_reference_sha256=digest(ref),process=process,comparisons=comparisons))
        negative=[
            ('nozzle-overexpanded',['combustion','frozen','10000000','3.4','298.15','298.15','40','100000'],'out_of_domain'),
            ('nozzle-area-invalid',['combustion','frozen','10000000','3.4','298.15','298.15','0','0'],'invalid_argument'),
            ('nozzle-tp-invalid',['combustion','frozen-tp','199','10000000','3.4','298.15','298.15','10','0','0.01'],'out_of_domain'),
        ]
        for name,args,status_name in negative:
            run,process=logged([binary,*args],folder,name,30)
            passed=run.returncode==4 and not run.stdout and run.stderr.startswith(status_name+':')
            record['rejections'].append(dict(id=name,arguments=args,expected_exit=4,expected_status_name=status_name,process=process,passed=passed))
            if not passed: record['issues'].append('CLI rejection: '+name)
        origin=folder/'u015-origin';origin.mkdir()
        for name in ('failed-quality-20261024.json','cycle-crash-probe.json','cycle-repeat-probes.json'):
            shutil.copy2(ROOT/'build/work2/architecture'/name,origin/name)
        original=read_json(origin/'cycle-crash-probe.json')
        cleanup=read_json(ROOT/'Work2/results/cleanup_v1/manifest.json')
        old_build='build/artifacts/debug/85a23407c5174bc8b7e53e2ba7f6f8fa'
        record['u015']=dict(root_cause='unresolved',historical_exception='0xC0000005',
            original_binary_sha256=original['sha256'],original_binary_available=(ROOT/old_build/'test_cycle.exe').is_file(),
            original_build=old_build,cleanup_manifest='Work2/results/cleanup_v1/manifest.json',
            cleanup_manifest_sha256=digest(ROOT/'Work2/results/cleanup_v1/manifest.json'),
            cleanup_lists_original_build_deleted=old_build in cleanup.get('execution',{}).get('deleted_paths',[]),
            limitation='No exact original-binary rerun possible if deleted. Sixty new-build successes do not identify or fix the historical access violation.')
        # The cleanup schema uses a named result object; locate its explicit list without inference.
        record['u015']['cleanup_lists_original_build_deleted']=any(isinstance(v,dict) and old_build in v.get('deleted_paths',[]) for v in cleanup.values())
        hardware, _=logged(['pwsh','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress'],folder,'cpu',30)
        record['hardware']=json.loads(hardware.stdout)
        record['status']='PASS' if not record['issues'] else 'FAIL'
    except Exception as exc:
        record.update(status='FAIL',error=str(exc));raise
    finally:
        record['finished_at']=now()
        record['files']=[dict(path=p.relative_to(folder).as_posix(),sha256=digest(p),bytes=p.stat().st_size)
            for p in sorted(folder.rglob('*')) if p.is_file() and p!=folder/'manifest.json' and p.suffix!='.exe']
        atomic_json(folder/'manifest.json',record)
    return folder


def verify_layers(folder):
    from combustion_reference import compare_report
    from cea_reference import parse_output
    from pipeline import verify_test_report
    folder=Path(folder);record=read_json(folder/'manifest.json')
    if record.get('kind')!='work2-baseline-layers' or record.get('status')!='PASS': raise ValueError('Layered evidence is not PASS')
    declared={f['path'] for f in record['files']}
    actual={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p!=folder/'manifest.json' and p.suffix!='.exe'}
    if actual!=declared or len(declared)!=len(record['files']): raise ValueError('Layered file inventory differs')
    for entry in record['files']:
        path=(folder/entry['path']).resolve()
        if not path.is_relative_to(folder.resolve()) or digest(path)!=entry['sha256'] or path.stat().st_size!=entry['bytes']:
            raise ValueError('Layered file bytes differ')
    build=read_json(folder/'build-manifest.json');tests=read_json(folder/'test-report.json')
    verify_test_report(tests,build,digest(folder/'build-manifest.json'))
    if record['binary_sha256']!=build['application']['sha256']: raise ValueError('Layered build identity differs')
    gas=record['gas_cea']
    if gas['status']!='PASS' or len(gas['cases'])!=4: raise ValueError('Gas CEA comparison incomplete')
    references={r['id']:r for r in read_json(folder/'gas-cea/cea-manifest.json')['cases']}
    for case in gas['cases']:
        mode='frozen' if case['id'].startswith('frozen') else case['id'];area=int(case['id'][6:]) if mode=='frozen' else None
        raw=json.loads((folder/'gas-cea'/(case['id']+'-stdout.json')).read_text(encoding='utf-8'))
        if compare_report(raw,references[case['reference']],mode,area)!=case['comparisons']: raise ValueError('Gas CEA comparison differs')
    if len(record['inlet_cases'])!=9 or len(record['rejections'])!=3: raise ValueError('Layered matrix incomplete')
    for case in record['inlet_cases']:
        raw=json.loads((folder/(case['id']+'.stdout.txt')).read_text(encoding='utf-8'))
        ref=folder/case['reference_file']
        if digest(ref)!=case['original_reference_sha256'] or compare_report(raw,{'summary':parsed_reference(ref,folder/case['reference_card'])},case['mode'],case['area'],expected_inputs=case['expected_inputs'])!=case['comparisons']:
            raise ValueError('Inlet reference comparison differs')
    for case in record['rejections']:
        if not case['passed'] or case['process']['exit_code']!=case['expected_exit'] or (folder/(case['id']+'.stdout.txt')).read_bytes() or not (folder/(case['id']+'.stderr.txt')).read_text(encoding='utf-8').startswith(case['expected_status_name']+':'):
            raise ValueError('CLI rejection evidence differs')
    if record['u015']['root_cause']!='unresolved': raise ValueError('U-015 must not be closed by successful retries')
    return dict(cea_gas_cases=4,inlet_cases=9,cli_rejections=3)


def verify_bundle(folder,root=ROOT):
    folder=Path(folder);result=verify_base(folder,root);base=read_json(folder/'manifest.json')
    layers=read_json(folder/'layers/manifest.json')
    if layers['base_manifest_sha256']!=digest(folder/'manifest.json'): raise ValueError('Layer/base manifest linkage differs')
    result.update(verify_layers(folder/'layers'))
    declared={f['path'] for f in base['files']}
    actual={p.name for p in folder.iterdir() if p.is_file() and p.name!='manifest.json'}
    if declared!=actual-{'selection-manifest.json'}: raise ValueError('Base file inventory differs')
    selection=read_json(folder/'selection-manifest.json')
    expected_files={f['path'] for f in selection['files']}
    actual_files={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p!=folder/'selection-manifest.json'}
    if expected_files!=actual_files or len(expected_files)!=len(selection['files']): raise ValueError('Selected bundle inventory differs')
    for entry in selection['files']:
        path=(folder/entry['path']).resolve()
        if not path.is_relative_to(folder.resolve()) or digest(path)!=entry['sha256'] or path.stat().st_size!=entry['bytes']:
            raise ValueError('Selected bundle bytes differ')
    for source in layers['source_snapshots']:
        if digest(folder/'layers/source-snapshots'/Path(source['path']).name)!=source['sha256']: raise ValueError('Original research tool snapshot differs')
    verify_independent_record(base)
    return result


def verify_independent_record(base):
    by_id={c['input']['id']:c for c in base['cases']}
    for reference in base['independent_references']:
        case=by_id[reference['id']];gas=case['output']['gas'];ref=reference['reference']
        dy=max(abs(a-b) for a,b in zip(gas['mole_fractions'],ref['mole_fractions']))
        if abs(dy-reference['max_fraction_absolute_difference'])>1e-16 or dy>1e-8: raise ValueError('Independent composition comparison differs')
        if reference['kind'].startswith('HP-'):
            dt=abs(gas['temperature_k']-ref['temperature_k'])
            if abs(dt-reference['temperature_absolute_difference_k'])>1e-12 or dt>1e-4: raise ValueError('Independent HP comparison differs')
        # Recompute reference chemistry from saved fractions; do not trust its success label alone.
        synthetic={'gas':dict(ref), 'equilibrium_residual':ref['residual_norm'],
                   'enthalpy_residual_j_per_kg':ref['h_j_per_kg']-reference.get('inlet_h_j_per_kg',ref['h_j_per_kg'])}
        if not assess_gas(case['input'],synthetic)['accepted']: raise ValueError('Independent reference physical checks failed')


def archive(base_folder,layers_folder,failed_folders=()):
    from work2_baseline import archive as archive_base
    base_folder=Path(base_folder).resolve();layers_folder=Path(layers_folder).resolve()
    verify_base(base_folder);verify_layers(layers_folder)
    if read_json(layers_folder/'manifest.json')['base_manifest_sha256']!=digest(base_folder/'manifest.json'): raise ValueError('Selected run linkage differs')
    target=archive_base(base_folder);destination=target/'layers';destination.mkdir()
    record=read_json(layers_folder/'manifest.json')
    for entry in record['files']:
        path=destination/entry['path'];path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(layers_folder/entry['path'],path)
    shutil.copy2(layers_folder/'manifest.json',destination/'manifest.json')
    failed=[]
    for failed_folder in failed_folders:
        failed_folder=Path(failed_folder).resolve();attempt=read_json(failed_folder/'manifest.json')
        if attempt['status']!='FAIL': raise ValueError('Only failed prior attempts go in the failure inventory')
        destination=target/'attempts'/failed_folder.name;destination.mkdir(parents=True)
        for entry in attempt['files']:
            path=destination/entry['path'];path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(failed_folder/entry['path'],path)
        shutil.copy2(failed_folder/'manifest.json',destination/'manifest.json')
        failed.append(dict(run_id=attempt['run_id'],status='FAIL',manifest=(destination/'manifest.json').relative_to(target).as_posix()))
    selection=dict(schema_version=1,kind='work2-baseline-selection',created_at=now(),
        selected_runs=[read_json(base_folder/'manifest.json')['run_id'],record['run_id']],prior_failed_attempts=failed,
        files=[dict(path=p.relative_to(target).as_posix(),sha256=digest(p),bytes=p.stat().st_size)
               for p in sorted(target.rglob('*')) if p.is_file()])
    atomic_json(target/'selection-manifest.json',selection)
    verify_bundle(target)
    return target


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    run=sub.add_parser('execute');run.add_argument('--run-id',required=True);run.add_argument('--base-folder',required=True)
    check=sub.add_parser('verify');check.add_argument('folder')
    save=sub.add_parser('archive');save.add_argument('base_folder');save.add_argument('layers_folder')
    save.add_argument('--failed-folder',action='append',default=[])
    args=parser.parse_args()
    try:
        if args.action=='execute':
            folder=execute(args.run_id,args.base_folder)
            if read_json(folder/'manifest.json')['status']!='PASS': raise ValueError('Layered run failed; see '+str(folder/'manifest.json'))
            print(folder)
        elif args.action=='archive': print(archive(args.base_folder,args.layers_folder,args.failed_folder))
        else: print(json.dumps(verify_bundle(args.folder),ensure_ascii=False))
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        print('work2-baseline-layers: '+str(exc),file=sys.stderr);sys.exit(1)
