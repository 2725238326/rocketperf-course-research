"""Single quality entry point. Always replaces RUNNING with PASS or FAIL."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from projectlib import ROOT, atomic_json, atomic_text, fingerprint, now, subprocess_env


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',default='build/quality/latest.json')
    args=parser.parse_args()
    from projectlib import local_path
    path=local_path(ROOT,args.report)
    folder=path.parent
    folder.mkdir(parents=True,exist_ok=True)
    before=fingerprint(ROOT)
    report={"schema_version":1,"kind":"quality","status":"RUNNING","started_at":now(),"input_fingerprint":before,"checks":[]}
    atomic_json(path,report)
    steps=[('project',[sys.executable,'tools/project.py','check']),
           ('governance',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_governance.py','-v']),
           ('debug',[sys.executable,'tools/pipeline.py','test','--configuration','Debug']),
           ('release',[sys.executable,'tools/pipeline.py','test','--configuration','Release']),
           ('runner',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_runner.py','-v'])]
    try:
        for name,command in steps:
            print(f'Quality: {name}',flush=True)
            completed=subprocess.run(command,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=240,check=False,env=subprocess_env())
            atomic_text(folder/(name+'.log'),completed.stdout+completed.stderr)
            report['checks'].append({'name':name,'status':'PASS' if completed.returncode==0 else 'FAIL','command':command,'log':(folder/(name+'.log')).relative_to(ROOT).as_posix()})
            atomic_json(path,report)
            if completed.returncode:
                raise ValueError(f'{name} failed; see {folder/(name+".log")}\n'+(completed.stdout+completed.stderr)[-2500:])
        if fingerprint(ROOT)!=before: raise ValueError('Project inputs changed during quality run; evidence is not current')
        report['status']='PASS'
    except Exception as exc:
        report.update(status='FAIL',error=str(exc));print(str(exc),file=sys.stderr)
    finally:
        report['finished_at']=now();atomic_json(path,report)
    print(json.dumps({'status':report['status'],'report':str(path),'checks':len(report['checks'])},ensure_ascii=False))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
