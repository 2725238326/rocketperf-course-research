"""Build a compact, verified Windows handoff package from an existing tested build."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import os
import re
import sys
import uuid

from pipeline import test_records, verify_test_report, verified_build
from projectlib import QUALITY_CHECKS, ROOT, atomic_json, atomic_text, canonical, digest, git, local_path, now, read_json, subprocess_env

HANDOFF_VERSION = 3
BASE_FILES = ('README.md', 'AGENTS.md', 'rules.md', 'handoff.md', 'worknow.md',
              'docs/governance.md', 'docs/receiving.md', 'docs/cycle-validation.md')
FILES = BASE_FILES + ('project/tasks.json',)


def select_next_task(state):
    """Follow the saved work context; never replace a blocked plan with a report."""
    if (not isinstance(state, dict) or not isinstance(state.get('tasks'), list)
        or not isinstance(state.get('context'), dict)
        or not isinstance(state['context'].get('next_tasks'), list)):
        raise ValueError('Invalid task selection snapshot')
    mapping = {}
    for task in state['tasks']:
        if (not isinstance(task, dict) or not isinstance(task.get('id'), str)
            or not task['id'] or task['id'] in mapping
            or not isinstance(task.get('status'), str)
            or task['status'] not in {'PLANNED','READY','ACTIVE','REVIEW','BLOCKED','DONE','CANCELLED'}
            or type(task.get('priority')) is not int or task['priority'] < 0):
            raise ValueError('Invalid task selection record')
        mapping[task['id']] = task
    preferred = state['context']['next_tasks']
    if (any(not isinstance(tid, str) or tid not in mapping for tid in preferred)
        or len(preferred) != len(set(preferred))):
        raise ValueError('Invalid preferred task references')
    for tid in preferred:
        if mapping[tid]['status'] not in {'DONE','CANCELLED'}:
            return mapping[tid]
    ready = sorted((task for task in state['tasks'] if task['status'] == 'READY'),
                   key=lambda task: (task['priority'], task['id']))
    return ready[0] if ready else None


def create(root=ROOT, destination=None, configuration='Release', fixture=False):
    quality = None
    if not fixture:
        if git(root,'status','--porcelain',check=True).stdout.strip():
            raise ValueError('Commit reviewed changes before creating a delivery package')
        from project import quality_proof
        quality = quality_proof(root,'build/quality/latest.json')
    build_path = verified_build(root, configuration, require_tests=True)
    build = read_json(build_path)
    tests = read_json(build_path.parent / 'test-report.json')
    verify_test_report(tests, build, digest(build_path))
    destination = Path(destination) if destination else root / 'build' / ('handoff-' + uuid.uuid4().hex[:8])
    destination = destination if destination.is_absolute() else root / destination
    destination=destination.resolve()
    if destination.exists(): raise FileExistsError('Handoff destination already exists')
    if destination.is_relative_to(root.resolve()) and not destination.is_relative_to((root/'build').resolve()):
        raise ValueError('Project-local handoff outputs belong under build/')
    destination.mkdir(parents=True, exist_ok=False)
    state={'schema_version':HANDOFF_VERSION,'kind':'windows-project-handoff','status':'PREPARING','created_at':now()}
    atomic_json(destination/'handoff-manifest.json',state)
    try:
        return _populate(root,destination,configuration,build_path,build,tests,fixture,quality)
    except Exception as exc:
        state.update(status='FAILED',error=str(exc))
        atomic_json(destination/'handoff-manifest.json',state)
        raise


def _populate(root,destination,configuration,build_path,build,tests,fixture,quality):
    for relative in FILES:
        source = root / relative
        if not source.is_file(): raise ValueError(f'Missing handoff document: {relative}')
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for relative in ('tools/handoff.py','tools/pipeline.py','tools/projectlib.py','tools/cycle_validation.py',
                     'tools/gas_checks.py','data/thermo/manifest.json','cases/benchmarks/prescribed_cycle.ini',
                     'cases/benchmarks/air_mach2_vacuum.ini','tests/fixtures/overexpanded.ini'):
        target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/relative,target)
    raw=root/'调研/原始来源/20261003_cea_v3.3.4'
    for filename in ('LICENSE.txt','NOTICE.txt'):
        target=destination/'third_party/cea'/filename;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(raw/filename,target)
    source_binary = root / build['application']['path']
    shutil.copy2(source_binary, destination / source_binary.name)
    shutil.copy2(build_path, destination / 'build-manifest.json')
    shutil.copy2(build_path.parent / 'test-report.json', destination / 'test-report.json')
    if not fixture: shutil.copy2(root/'build/quality/latest.json',destination/'quality-report.json')
    # Fail closed rather than silently delivering uncollected MinGW runtime DLLs.
    imports=[]
    if os.name == 'nt':
        objdump=Path(build['compiler']).with_name('objdump.exe')
        output=subprocess.run([str(objdump),'-p',str(source_binary)],cwd=root,capture_output=True,
                              encoding='utf-8',errors='replace',timeout=30,check=True).stdout
        imports=re.findall(r'DLL Name:\s+(\S+)',output)
        if not imports: raise ValueError('No Windows import evidence')
        if any(name.lower() not in {'kernel32.dll','msvcrt.dll','ucrtbase.dll'} and not name.lower().startswith('api-ms-win-') for name in imports):
            raise ValueError('External runtime DLLs require explicit packaging and license review')
    source_bundle=None
    if not fixture:
        source_bundle='source.bundle'
        subprocess.run(['git','bundle','create',str(destination/source_bundle),'HEAD',git(root,'branch','--show-current').stdout.strip()],
                       cwd=root,capture_output=True,encoding='utf-8',errors='replace',timeout=120,check=True)
    checks=[]
    for label,arguments,expected_exit in (
        ('cycle',['cycle','prescribed','cases/benchmarks/prescribed_cycle.ini'],0),
        ('domain-rejection',['run','tests/fixtures/overexpanded.ini'],4)):
        clean_env=subprocess_env()
        if os.name == 'nt': clean_env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
        run=subprocess.run([str(destination/source_binary.name),*arguments],cwd=destination,
                           capture_output=True,encoding='utf-8',errors='strict',env=clean_env,timeout=15)
        if run.returncode != expected_exit or (expected_exit == 0 and run.stderr) or (expected_exit != 0 and (run.stdout or not run.stderr)):
            raise ValueError('Handoff receiving check failed: '+label)
        if label == 'cycle':
            from cycle_validation import validate_cycle
            from projectlib import strict_json
            count=len(validate_cycle(strict_json(run.stdout),(destination/arguments[-1]).read_text(encoding='utf-8-sig')))
        else: count=0
        atomic_text(destination/(label+'-stdout.json'),run.stdout)
        atomic_text(destination/(label+'-stderr.txt'),run.stderr)
        checks.append({'id':label,'command':[source_binary.name,*arguments],'exit_code':run.returncode,'checks':count})
    atomic_text(destination/'START-HERE.md', '\n'.join([
        '# Windows 阶段交接包', '',
        '这是研究方法和软件基底的阶段交接，不是最终课程交付或真实发动机性能认证。', '',
        '先在本目录核验：`python tools/handoff.py verify --package .`。',
        '演示成功：`./rocketperf.exe cycle prescribed cases/benchmarks/prescribed_cycle.ini`。',
        '演示预期失败：`./rocketperf.exe run tests/fixtures/overexpanded.ini`（退出码 4）。',
        '接收检查输出是在隔离 PATH、包自身目录里运行并核验的结果，仍需接手者在另一台 Windows 机器复验。', '',
        '维护代码：`git clone source.bundle rocketperf-source`，进入源码目录后按 docs/receiving.md 重建、验收。',
        '包内 doctor/quality 等源码工作区命令，应在克隆的源码目录运行；此运行包不是源码工作区。',
        '完整源码/原始资料/历史/许可在 source.bundle；文档的外部项目内链接在克隆后使用。',
        '不带项目对外发布许可证，不自行公开上传。',
    ])+'\n')
    record = {
        'schema_version': HANDOFF_VERSION, 'kind': 'windows-project-handoff', 'status': 'PASS',
        'created_at': now(), 'project_head': git(root, 'rev-parse', 'HEAD').stdout.strip(),
        'branch': git(root, 'branch', '--show-current').stdout.strip(),
        'configuration': configuration, 'build_manifest_sha256': digest(build_path),
        'test_report_sha256': digest(build_path.parent / 'test-report.json'),
        'binary': {'path': source_binary.name, 'sha256': digest(source_binary)},
        'tracked_inputs': test_records(root),
        'next_task': select_next_task(read_json(destination/'project/tasks.json')),
        'source_bundle':source_bundle,'source_fingerprint':quality['input_fingerprint'] if quality else None,
        'test_fixture':fixture,'windows_imports':imports,'checks':checks,
        'scope': 'Windows handoff for code, tests, and the prescribed thermal cycle boundary; not a flight-engine claim.',
    }
    if read_json(destination/'build-manifest.json') != build or read_json(destination/'test-report.json') != tests or digest(destination/source_binary.name) != build['application']['sha256']:
        raise ValueError('Build/test/binary changed during handoff snapshot')
    if test_records(root) != tests['validation_inputs']:
        raise ValueError('Validation inputs changed during handoff snapshot')
    if not fixture:
        from project import quality_proof
        if quality_proof(root,'build/quality/latest.json') != quality or read_json(destination/'quality-report.json') != quality:
            raise ValueError('Quality evidence changed during handoff snapshot')
        if git(root,'status','--porcelain',check=True).stdout.strip(): raise ValueError('Source tree changed during packaging')
    atomic_text(destination / 'VERIFY.txt', '\n'.join([
        '1. Read START-HERE.md and docs/receiving.md.',
        '2. Run: python tools/handoff.py verify --package .',
        '3. Clone source.bundle before using project.py doctor.',
        '4. In the source clone, run tools/quality.py for code changes.',
        '5. Discuss semantic model scope separately from mechanical PASS evidence.',
    ]) + '\n')
    record['files']=[{'path':p.relative_to(destination).as_posix(),'sha256':digest(p)}
                     for p in sorted(destination.rglob('*')) if p.is_file() and p != destination/'handoff-manifest.json' and '__pycache__' not in p.parts]
    atomic_json(destination / 'handoff-manifest.json', record)
    verify(destination)
    return destination


def verify(package):
    package = Path(package).resolve()
    record = read_json(package / 'handoff-manifest.json')
    if (not isinstance(record,dict) or type(record.get('schema_version')) is not int or record['schema_version'] not in {1, 2, HANDOFF_VERSION}
        or type(record.get('test_fixture')) is not bool or record.get('kind') != 'windows-project-handoff' or record.get('status') != 'PASS'):
        raise ValueError('Invalid handoff manifest')
    binary=record.get('binary')
    if (not isinstance(binary,dict) or set(binary) != {'path','sha256'}
        or not isinstance(binary['path'],str) or not binary['path']
        or not isinstance(binary['sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',binary['sha256'])
        or not isinstance(record.get('project_head'),str) or not re.fullmatch(r'[a-f0-9]{40,64}',record['project_head'])
        or not isinstance(record.get('branch'),str) or not record['branch']
        or record.get('configuration') not in {'Debug','Release'}):
        raise ValueError('Invalid handoff identity')
    files=record.get('files',[])
    if (not isinstance(files,list) or not files or any(not isinstance(f,dict) or set(f) != {'path','sha256'}
        or not isinstance(f['path'],str) or not isinstance(f['sha256'],str)
        or not re.fullmatch(r'[a-f0-9]{64}',f['sha256']) for f in files)
        or len({f['path'] for f in files}) != len(files)):
        raise ValueError('Invalid handoff files')
    declared={f['path'] for f in files}
    required=set(FILES if record['schema_version'] in {2, HANDOFF_VERSION} else BASE_FILES)|{'START-HERE.md','VERIFY.txt','tools/handoff.py','tools/pipeline.py','tools/projectlib.py',
                         'tools/cycle_validation.py','tools/gas_checks.py','data/thermo/manifest.json',
                         'build-manifest.json','test-report.json','cases/benchmarks/prescribed_cycle.ini',
                         'tests/fixtures/overexpanded.ini','cases/benchmarks/air_mach2_vacuum.ini',binary['path'],
                         'third_party/cea/LICENSE.txt','third_party/cea/NOTICE.txt',
                         'cycle-stdout.json','cycle-stderr.txt','domain-rejection-stdout.json','domain-rejection-stderr.txt'}
    if not record.get('test_fixture'): required |= {'source.bundle','quality-report.json'}
    if not required <= declared: raise ValueError('Required handoff files missing from manifest')
    actual={p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()
            and p != package/'handoff-manifest.json' and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if actual != declared: raise ValueError('Handoff has undeclared or missing files')
    for item in files:
        if digest(local_path(package,item['path'])) != item['sha256']: raise ValueError('Handoff file hash mismatch: '+item['path'])
    if record['schema_version'] in {2, HANDOFF_VERSION}:
        expected_next = select_next_task(read_json(package/'project/tasks.json'))
        if 'next_task' not in record or canonical(record['next_task']) != canonical(expected_next):
            raise ValueError('Handoff next task differs from the saved work context')
    build = read_json(package / 'build-manifest.json')
    tests = read_json(package / 'test-report.json')
    if (not isinstance(build,dict) or build.get('kind') != 'build' or build.get('status') != 'PASS'
        or build.get('configuration') != record['configuration'] or not isinstance(build.get('application'),dict)
        or not isinstance(tests,dict)):
        raise ValueError('Invalid handoff build/test report')
    if digest(package/'build-manifest.json') != record['build_manifest_sha256']:
        raise ValueError('Handoff build manifest hash mismatch')
    if digest(package/'test-report.json') != record['test_report_sha256']:
        raise ValueError('Handoff test report hash mismatch')
    if digest(local_path(package,record['binary']['path'])) != record['binary']['sha256'] or record['binary']['sha256'] != build['application']['sha256']:
        raise ValueError('Handoff binary hash mismatch')
    verify_test_report(tests, build, record['build_manifest_sha256'])
    if tests.get('validation_inputs') != record.get('tracked_inputs'):
        raise ValueError('Handoff validation inputs differ from manifest')
    if not record['test_fixture']:
        if record.get('source_bundle') != 'source.bundle': raise ValueError('Source bundle required')
        quality=read_json(package/'quality-report.json')
        checks=quality.get('checks',[]) if isinstance(quality,dict) else []
        if (not isinstance(quality,dict) or type(quality.get('schema_version')) is not int or quality.get('schema_version') != 1 or quality.get('kind') != 'quality'
            or quality.get('status') != 'PASS' or not isinstance(checks,list) or len(checks) != len(QUALITY_CHECKS)
            or any(not isinstance(c,dict) or not isinstance(c.get('name'),str) or c.get('status') != 'PASS' for c in checks)
            or {c.get('name') for c in checks} != QUALITY_CHECKS
            or not isinstance(record.get('source_fingerprint'),str)
            or not re.fullmatch(r'[a-f0-9]{64}',record['source_fingerprint'])
            or quality.get('input_fingerprint') != record['source_fingerprint']):
            raise ValueError('Incomplete handoff quality evidence')
        heads=subprocess.run(['git','bundle','list-heads',str(package/'source.bundle')],cwd=package,
                             capture_output=True,encoding='utf-8',errors='strict',timeout=30,check=True).stdout.splitlines()
        identities=dict(line.split(' ',1)[::-1] for line in heads)
        if identities.get('HEAD') != record['project_head'] or identities.get('refs/heads/'+record['branch']) != record['project_head']:
            raise ValueError('Source bundle does not match handoff commit/branch')
    field = 'checks' if record['schema_version'] == HANDOFF_VERSION else 'smoke_tests'
    if ('checks' in record) == ('smoke_tests' in record):
        raise ValueError('Ambiguous or missing receiving checks field')
    checks = record.get(field)
    if (not isinstance(checks,list) or len(checks) != 2 or any(not isinstance(s,dict) for s in checks)
        or {s.get('id') for s in checks} != {'cycle','domain-rejection'}):
        raise ValueError('Missing handoff receiving checks')
    cycle=read_json(package/'cycle-stdout.json')
    from cycle_validation import validate_cycle
    equations=validate_cycle(cycle,(package/'cases/benchmarks/prescribed_cycle.ini').read_text(encoding='utf-8-sig'),root=package)
    expected={'cycle':(0,len(equations)),'domain-rejection':(4,0)}
    commands={'cycle':[binary['path'],'cycle','prescribed','cases/benchmarks/prescribed_cycle.ini'],
              'domain-rejection':[binary['path'],'run','tests/fixtures/overexpanded.ini']}
    for item in checks:
        if (type(item.get('exit_code')) is not int or type(item.get('checks')) is not int
            or (item['exit_code'],item['checks']) != expected[item['id']]
            or item.get('command') != commands[item['id']]): raise ValueError('Invalid receiving check result')
    if (package/'cycle-stderr.txt').stat().st_size or (package/'domain-rejection-stdout.json').stat().st_size or not (package/'domain-rejection-stderr.txt').read_text(encoding='utf-8').strip():
        raise ValueError('Invalid receiving check output protocol')
    return record


def receive(package, actor, role, output):
    """Receiver runs the binaries themselves; semantic conclusions remain separate."""
    if not actor.strip(): raise ValueError('Receiver name required')
    if role not in {'maintenance','research','presentation','acceptance'}: raise ValueError('Unsupported receiving role')
    record=verify(package); package=Path(package).resolve(); output=Path(output).resolve()
    if output.exists(): raise FileExistsError('Receipt already exists')
    if output.is_relative_to(package): raise ValueError('Save receipts outside the immutable package')
    checks=[]
    for label,args,code in (('cycle',['cycle','prescribed','cases/benchmarks/prescribed_cycle.ini'],0),
                            ('domain-rejection',['run','tests/fixtures/overexpanded.ini'],4)):
        run=subprocess.run([str(local_path(package,record['binary']['path'])),*args],cwd=package,
                           capture_output=True,encoding='utf-8',errors='strict',timeout=15,env=subprocess_env())
        if run.returncode != code or (code==0 and run.stderr) or (code!=0 and (run.stdout or not run.stderr)):
            raise ValueError('Receiver run failed: '+label)
        if code==0:
            from cycle_validation import validate_cycle
            from projectlib import strict_json
            validate_cycle(strict_json(run.stdout),(package/args[-1]).read_text(encoding='utf-8-sig'),root=package)
        checks.append({'id':label,'exit_code':run.returncode})
    receipt={'schema_version':1,'kind':'handoff-receipt','status':'PASS','received_at':now(),
             'actor':actor.strip(),'role':role,'project_head':record['project_head'],
             'package_manifest_sha256':digest(package/'handoff-manifest.json'),'checks':checks,
             'semantic_review':'Not included: flight parameters, model assumptions and scientific conclusions require named review.'}
    atomic_json(output,receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create_parser = sub.add_parser('create')
    create_parser.add_argument('--destination')
    create_parser.add_argument('--configuration', choices=('Debug','Release'), default='Release')
    verify_parser = sub.add_parser('verify')
    verify_parser.add_argument('--package', required=True)
    receive_parser=sub.add_parser('receive')
    receive_parser.add_argument('--package',required=True)
    receive_parser.add_argument('--actor',required=True)
    receive_parser.add_argument('--role',required=True,choices=('maintenance','research','presentation','acceptance'))
    receive_parser.add_argument('--output',required=True)
    args = parser.parse_args()
    if args.command == 'create': print(f'Handoff PASS: {create(ROOT,args.destination,args.configuration)}')
    elif args.command=='receive': print(json.dumps(receive(args.package,args.actor,args.role,args.output),ensure_ascii=False,indent=2))
    else:
        record=verify(args.package)
        print(json.dumps({k:record[k] for k in ('status','project_head','branch','configuration','scope','next_task','test_fixture')},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try: main()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(f'handoff: {exc}', file=sys.stderr); sys.exit(1)
