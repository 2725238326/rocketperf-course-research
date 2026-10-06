"""Task state machine, generated views, architecture and repository checks."""
from __future__ import annotations

import argparse
import copy
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

from projectlib import (ROOT, QUALITY_CHECKS, atomic_json, atomic_text, canonical, digest, fingerprint,
                       git, local_path, lock, now, project_files, read_json)

STATES = {"PLANNED", "READY", "ACTIVE", "REVIEW", "BLOCKED", "DONE", "CANCELLED"}
TASK_FIELDS = {"id","title","status","priority","depends_on","required_artifacts","acceptance","owner","note","verification"}
SECRET = re.compile(r"(?<![A-Za-z0-9_-])(?:sk-|xai-)[A-Za-z0-9_-]{24,}|(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


def validate_registry(root: Path, state: dict, check_files=True) -> list[str]:
    problems = []
    if not isinstance(state,dict) or state.get("schema_version") != 1 or type(state.get("revision")) is not int:
        return ["Unsupported task registry schema/revision"]
    tasks = state.get("tasks", [])
    if not isinstance(tasks,list) or any(not isinstance(t,dict) for t in tasks) or not isinstance(state.get('events'),list) or any(not isinstance(e,dict) for e in state['events']):
        return ["Task records and events must be arrays of objects"]
    for task in tasks:
        if set(task)!=TASK_FIELDS or any(not isinstance(task.get(key),list) or any(not isinstance(x,str) for x in task[key]) for key in ('depends_on','required_artifacts','acceptance')):
            return ["Invalid task record shape"]
        if not isinstance(task.get('id'),str) or not isinstance(task.get('title'),str) or not task['title'].strip() or not isinstance(task.get('status'),str) or (task.get('owner') is not None and not isinstance(task['owner'],str)):
            return ["Invalid task identity/title/status/owner"]
    mapping = {}
    for task in tasks:
        tid = task.get("id", "")
        if set(task) != TASK_FIELDS:
            problems.append(f"{tid}: task fields differ from v1 contract")
        if not re.fullmatch(r"[A-Z]+-\d{3}", tid) or tid in mapping:
            problems.append(f"Invalid/duplicate task ID: {tid}")
        mapping[tid] = task
        if task.get("status") not in STATES:
            problems.append(f"{tid}: invalid status")
        if type(task.get("priority")) is not int or task["priority"] not in range(4):
            problems.append(f"{tid}: priority must be 0..3")
        for key in ("depends_on", "required_artifacts", "acceptance"):
            if not isinstance(task.get(key), list) or any(not isinstance(x,str) or not x.strip() for x in task[key]):
                problems.append(f"{tid}: invalid {key}")
        if not task.get("acceptance") or not task.get("required_artifacts"):
            problems.append(f"{tid}: acceptance and deliverable contracts required")
        if task.get("status") in {"ACTIVE", "REVIEW"} and not task.get("owner"):
            problems.append(f"{tid}: active/review task requires an owner")
        for artifact in task.get("required_artifacts", []):
            try:
                path = local_path(root, artifact)
                if check_files and task.get("status") in {"DONE", "REVIEW"} and (not path.is_file() or path.stat().st_size == 0):
                    problems.append(f"{tid}: missing/empty deliverable {artifact}")
            except ValueError as exc:
                problems.append(str(exc))
        proof = task.get("verification")
        if task.get("status") in {"DONE", "REVIEW"} and not proof:
            problems.append(f"{tid}: no verification record")
        if proof and check_files:
            try:
                if proof.get("kind") == "historical":
                    if not local_path(root, proof["reference"]).is_file():
                        problems.append(f"{tid}: missing historical record")
                elif proof.get("kind") == "quality":
                    path = local_path(root, proof["path"])
                    if not path.is_file() or digest(path) != proof["sha256"]:
                        problems.append(f"{tid}: verification snapshot missing/changed")
                else:
                    problems.append(f"{tid}: unknown verification kind")
            except (ValueError, KeyError) as exc:
                problems.append(f"{tid}: bad verification: {exc}")
    for task in tasks:
        for dep in task.get("depends_on", []):
            if dep not in mapping:
                problems.append(f"{task['id']}: unknown dependency {dep}")
        if task.get("status") in {"READY", "ACTIVE", "REVIEW", "DONE"}:
            if any(mapping.get(dep,{}).get("status") != "DONE" for dep in task.get("depends_on",[])):
                problems.append(f"{task['id']}: prerequisites are not DONE")
    seen, visiting = set(), set()
    def visit(tid):
        if tid in visiting:
            problems.append(f"Dependency cycle includes {tid}")
            return
        if tid in seen or tid not in mapping: return
        visiting.add(tid)
        for dep in mapping[tid].get("depends_on",[]): visit(dep)
        visiting.remove(tid)
        seen.add(tid)
    for tid in mapping: visit(tid)
    policy = read_json(root / "project/policy.json")
    if sum(t.get("status") in {"ACTIVE", "REVIEW"} for t in tasks) > policy["wip_limit"]:
        problems.append("WIP limit exceeded (ACTIVE + REVIEW)")
    previous = "0" * 64
    latest = {}
    for sequence, event in enumerate(state.get("events",[]), 1):
        if not isinstance(event.get('actor'),str) or not event['actor'].strip(): problems.append(f'Missing event actor at {sequence}')
        payload = {k:v for k,v in event.items() if k != "hash"}
        if event.get("seq") != sequence or event.get("previous_hash") != previous or hashlib.sha256(canonical(payload)).hexdigest() != event.get("hash"):
            problems.append(f"Event chain integrity failure at {sequence}")
        if event.get("task") not in mapping:
            problems.append(f"Unknown task in event {sequence}")
        prior = latest.get(event.get("task"))
        if prior is not None and event.get("from") != prior["to"]:
            problems.append(f"Event transition history mismatch at {sequence}")
        latest[event.get("task")] = event
        previous = event.get("hash")
    for tid, task in mapping.items():
        event = latest.get(tid)
        if event is None or event.get("to") != task["status"] or event.get("owner_after") != task["owner"]:
            problems.append(f"{tid}: state/owner does not match event history")
    return problems


def event_for(state, task, before, actor, note, metadata=None):
    event = {"seq":len(state["events"])+1,"at":now(),"task":task["id"],"from":before,
             "to":task["status"],"actor":actor,"owner_after":task["owner"],"note":note,
             "previous_hash":state["events"][-1]["hash"] if state["events"] else "0"*64}
    if metadata: event['details']=metadata
    event["hash"] = hashlib.sha256(canonical(event)).hexdigest()
    state["events"].append(event)
    state["revision"] += 1


def quality_proof(root: Path, relative: str):
    report = read_json(local_path(root, relative))
    if (not isinstance(report,dict) or type(report.get('schema_version')) is not int or report['schema_version'] != 1
        or report.get("kind") != "quality" or report.get("status") != "PASS"):
        raise ValueError("A PASS report from tools/quality.py is required")
    if report.get("input_fingerprint") != fingerprint(root):
        raise ValueError("Quality proof is stale; run quality again after code/docs changes")
    checks=report.get('checks')
    if (not isinstance(checks,list) or len(checks)!=len(QUALITY_CHECKS)
        or any(not isinstance(c,dict) or not isinstance(c.get('name'),str) or c.get('status')!='PASS' for c in checks)
        or {c['name'] for c in checks}!=QUALITY_CHECKS):
        raise ValueError("Quality report contains missing/failed checks")
    return report


def transition(root: Path, tid: str, action: str, actor: str, note: str,
               evidence: str | None = None, new_owner: str | None = None):
    if not actor.strip() or not note.strip(): raise ValueError("Actor and explanatory note are required")
    with lock(root):
        state = read_json(root / "project/tasks.json")
        existing = validate_registry(root, state)
        if existing: raise ValueError("Registry invalid: " + "; ".join(existing))
        task = next((t for t in state["tasks"] if t["id"] == tid), None)
        if task is None: raise ValueError("Task not found")
        before = task["status"]
        if before in {"ACTIVE", "REVIEW", "BLOCKED"} and task["owner"] != actor:
            raise ValueError("Only the current owner may change this task; use explicit handoff")
        allowed = {"start":{"READY"},"submit":{"ACTIVE"},"complete":{"REVIEW"},
                   "block":{"ACTIVE","REVIEW"},"unblock":{"BLOCKED"},
                   "reopen":{"DONE","REVIEW"},"cancel":{"PLANNED","READY","ACTIVE","BLOCKED"},
                   "handoff":{"ACTIVE","REVIEW","BLOCKED"}}
        if action not in allowed or before not in allowed[action]:
            raise ValueError(f"Cannot {action} a {before} task")
        if action == "start":
            task["status"], task["owner"] = "ACTIVE", actor
        elif action == "submit":
            if not evidence: raise ValueError("submit requires --evidence")
            report = quality_proof(root, evidence)
            for artifact in task["required_artifacts"]:
                path = local_path(root, artifact)
                if not path.is_file() or path.stat().st_size == 0: raise ValueError(f"Deliverable missing: {artifact}")
            relative = f"project/evidence/{tid}_{uuid.uuid4().hex[:12]}.json"
            # Snapshot is immutable; task state is committed only after all checks below.
            task["verification"] = {"kind":"quality","path":relative,
                                    "sha256":hashlib.sha256((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode()).hexdigest()}
            task["status"] = "REVIEW"
        elif action == "complete":
            if task["verification"]["kind"] != "quality": raise ValueError("Fresh quality proof required")
            quality_proof(root, task["verification"]["path"])
            task["status"] = "DONE"
        elif action == "block":
            task["status"] = "BLOCKED"
        elif action == 'reopen' and before == 'REVIEW':
            task['status'],task['verification']='ACTIVE',None
        elif action in {"unblock","reopen"}:
            done = {t["id"] for t in state["tasks"] if t["status"] == "DONE"}
            task["status"] = "READY" if set(task["depends_on"]) <= done else "PLANNED"
            task["owner"], task["verification"] = None, None
        elif action == "cancel": task["status"] = "CANCELLED"
        elif action == "handoff":
            if not new_owner or not new_owner.strip(): raise ValueError("handoff requires --to")
            task["owner"] = new_owner
        task["note"] = note
        event_for(state, task, before, actor, note)
        if action == 'reopen' and before == 'DONE':
            done = {t['id'] for t in state['tasks'] if t['status']=='DONE'}
            for candidate in state['tasks']:
                if candidate['status']=='READY' and not set(candidate['depends_on']) <= done:
                    candidate['status']='PLANNED'
                    event_for(state,candidate,'READY',actor,'Upstream reopened; prerequisite readiness revoked')
        if action == "complete":
            done = {t["id"] for t in state["tasks"] if t["status"] == "DONE"}
            for candidate in state["tasks"]:
                if candidate["status"] == "PLANNED" and set(candidate["depends_on"]) <= done:
                    candidate["status"] = "READY"
                    event_for(state,candidate,"PLANNED",actor,"Prerequisites completed; task is now ready")
        problems = validate_registry(root,state,check_files=False)
        if problems: raise ValueError("Transition rejected: " + "; ".join(problems))
        if action == "submit": atomic_json(local_path(root,relative),report)
        atomic_json(root / "project/tasks.json",state)
        render_views(root,state)
        return task


def add_task(root, tid, title, actor, deps, artifacts, acceptance, priority):
    if not actor.strip(): raise ValueError('Actor is required')
    with lock(root):
        state = read_json(root / "project/tasks.json")
        done = {t["id"] for t in state["tasks"] if t["status"] == "DONE"}
        task = {"id":tid,"title":title,"status":"READY" if set(deps)<=done else "PLANNED",
                "priority":priority,"depends_on":deps,"required_artifacts":artifacts,"acceptance":acceptance,
                "owner":None,"note":"Created with an explicit acceptance contract","verification":None}
        state["tasks"].append(task)
        event_for(state,task,None,actor,task["note"])
        problems=validate_registry(root,state)
        if problems: raise ValueError("; ".join(problems))
        atomic_json(root/"project/tasks.json",state)
        render_views(root,state)


def amend_task(root,tid,actor,note,**changes):
    if not actor.strip() or not note.strip(): raise ValueError('Actor and reason required')
    with lock(root):
        state=read_json(root/'project/tasks.json')
        task=next((t for t in state['tasks'] if t['id']==tid),None)
        if task is None: raise ValueError('Task not found')
        if task['status'] in {'DONE','REVIEW','CANCELLED'}: raise ValueError('Reopen before changing a frozen task contract')
        if task['owner'] is not None and task['owner']!=actor: raise ValueError('Only the current owner may amend this task')
        before=copy.deepcopy(task); old_status=task['status']
        for field,value in changes.items():
            if field not in {'title','depends_on','required_artifacts','acceptance','priority'}: raise ValueError('Unknown contract field')
            if value is not None: task[field]=value
        done={t['id'] for t in state['tasks'] if t['status']=='DONE'}
        if task['status'] in {'READY','PLANNED'}: task['status']='READY' if set(task['depends_on'])<=done else 'PLANNED'
        task['note']=note
        event_for(state,task,old_status,actor,note,{'contract_before':before,'contract_after':copy.deepcopy(task)})
        problems=validate_registry(root,state)
        if problems: raise ValueError('; '.join(problems))
        atomic_json(root/'project/tasks.json',state);render_views(root,state)


def amend_context(root,tid,actor,note,**changes):
    if not actor.strip() or not note.strip(): raise ValueError('Actor and reason required')
    with lock(root):
        state=read_json(root/'project/tasks.json')
        problems=validate_registry(root,state)
        if problems: raise ValueError('; '.join(problems))
        task=next((t for t in state['tasks'] if t['id']==tid),None)
        if task is None or task['status']!='ACTIVE' or task['owner']!=actor: raise ValueError('Context edit requires an active task owned by the actor')
        before=copy.deepcopy(state['context'])
        candidate=copy.deepcopy(before)
        for field,value in changes.items():
            if field not in {'phase','facts','next_tasks','evidence_cutoff'}: raise ValueError('Unknown context field')
            if value is not None: candidate[field]=value
        mapping={t['id']:t for t in state['tasks']}
        if not isinstance(candidate['phase'],str) or not candidate['phase'].strip(): raise ValueError('Nonempty phase required')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',candidate['evidence_cutoff']): raise ValueError('Cutoff requires ISO date')
        if not isinstance(candidate['facts'],list) or any(not isinstance(x,str) or not x.strip() for x in candidate['facts']): raise ValueError('Nonempty factual statements required')
        if not isinstance(candidate['next_tasks'],list) or any(tid not in mapping or mapping[tid]['status'] in {'DONE','CANCELLED'} for tid in candidate['next_tasks']): raise ValueError('Next tasks must reference unfinished tasks')
        state['context']=candidate
        event_for(state,task,task['status'],actor,note,{'context_before':before,'context_after':candidate})
        atomic_json(root/'project/tasks.json',state);render_views(root,state)


def expected_views(state):
    tasks=state["tasks"]
    def cell(text): return str(text).replace("|","／").replace("\n"," ")
    lines=["<!-- GENERATED by tools/project.py render. Edit project/tasks.json via task commands. -->",
           "# 任务板", "",f"唯一状态来源：`project/tasks.json`，修订 {state['revision']}。状态、依赖、负责人和验收通过工具维护。",
           "", "| ID | 任务 | 状态 | 优先级 | 负责人 | 前置任务 |", "|---|---|---|---|---|---|"]
    for task in tasks:
        lines.append("| "+" | ".join(cell(x) for x in [task["id"],task["title"],task["status"],f"P{task['priority']}",task["owner"] or "未领取",", ".join(task["depends_on"]) or "无"])+" |")
    lines += ["", "## 产物和验收", ""]
    for task in tasks:
        lines += [f"### {task['id']} · {task['title']}", "", "产物："+"、".join(f"`{p}`" for p in task["required_artifacts"]), ""]
        lines += [f"- {cell(item)}" for item in task["acceptance"]]
        lines += ["", "备注："+cell(task["note"]), ""]
    lines += ["流程与命令见[治理说明](governance.md)。教学基线完成不等于真实发动机模型完成。", ""]
    current=[t for t in tasks if t["status"] in {"ACTIVE","REVIEW"}]
    ready=sorted((t for t in tasks if t["status"]=="READY"),key=lambda t:(t["priority"],t["id"]))
    head=["<!-- GENERATED by tools/project.py render. Do not hand-edit task status. -->",
          "# Worknow：当前工作面","",f"阶段：{state['context']['phase']}。登记修订：{state['revision']}。",
          "", "## 正在执行", ""]
    head += [f"- **{t['id']} {t['title']}** · {t['status']} · 负责人：{t['owner']}\n  {t['note']}" for t in current] or ["当前无已领取任务。"]
    head += ["", "## 可领取任务", ""]+[f"- {t['id']}：{t['title']}（P{t['priority']}）" for t in ready]
    pending={t['id'] for t in tasks if t['status'] not in {'DONE','CANCELLED'}}
    next_tasks=[tid for tid in state['context']['next_tasks'] if tid in pending]
    head += ["", "建议接续顺序："+(" → ".join(next_tasks) if next_tasks else "按可领取任务和依赖推进")+"。", "", "## 事实与边界", ""]
    head += ["- "+x for x in state["context"]["facts"]]
    head += [f"- 已有在线证据截止：{state['context']['evidence_cutoff']}；文档/代码更新不自动刷新在线事实。",
             "- Git和环境实况用 `python tools/project.py doctor` 查看，不把易过时的提交状态复制到多份文档。",
             "", "完整验收：[任务板](docs/tasks.md)。执行规则：[rules](rules.md)。接手：[handoff](handoff.md)。",
             "架构：[作业对接与三视图](docs/architecture/README.md)。统一检查：`python tools/quality.py`。", ""]
    return {"docs/tasks.md":"\n".join(lines),"worknow.md":"\n".join(head)}


def render_views(root,state=None):
    for relative,text in expected_views(state or read_json(root/"project/tasks.json")).items():
        atomic_text(root/relative,text)


def architecture_checks(root):
    modules=read_json(root/"project/modules.json")["modules"]
    by_id={m["id"]:m for m in modules}
    issues=[]
    def owner(relative):
        matches=[m["id"] for m in modules if any(fnmatch.fnmatchcase(relative,p) for p in m["paths"])]
        if len(matches)!=1: raise ValueError(f"Ambiguous/unowned module path: {relative}")
        return matches[0]
    for module in modules:
        if any(dep not in by_id for dep in module["allowed_dependencies"]): issues.append(f"Unknown module dependency: {module['id']}")
        for relative in module["sources"]:
            if not local_path(root,relative).is_file(): issues.append(f"Missing registered source: {relative}")
        if module['state']=='implemented':
            for relative in module['checks']:
                if not local_path(root,relative).is_file(): issues.append(f"Registered validation missing: {relative}")
    for folder in ("src","include"):
        for path in (root/folder).rglob("*"):
            if path.suffix not in {".c",".h"}: continue
            relative=path.relative_to(root).as_posix()
            try: source_owner=owner(relative)
            except ValueError as exc: issues.append(str(exc)); continue
            text=path.read_text(encoding="utf-8")
            stripped=re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
            if source_owner in {"core","nozzle","thermo","cycle"} and re.search(r"\b(?:printf|fprintf|puts|fopen|fread|fwrite|malloc|calloc|realloc|free|system|exit|setlocale)\s*\(",stripped):
                issues.append(f"Core purity boundary violated: {relative}")
            for include in re.findall(r'^\s*#include\s+"([^"]+)"',text,re.M):
                candidates=[path.parent/include,root/"include"/include,root/"src/adapters"/include]
                target=next((p.resolve() for p in candidates if p.is_file()),None)
                if target is None: issues.append(f"Unresolved include in {relative}: {include}"); continue
                try: target_owner=owner(target.relative_to(root).as_posix())
                except ValueError as exc: issues.append(str(exc)); continue
                if target_owner!=source_owner and target_owner not in by_id[source_owner]["allowed_dependencies"]:
                    issues.append(f"Forbidden dependency: {source_owner} -> {target_owner} ({relative})")
    registered={s for m in modules for s in m["sources"]}
    actual={p.relative_to(root).as_posix() for p in (root/"src").rglob("*.c")}
    if registered != actual: issues.append("Production C source list and module registry differ")
    return issues


def check(root=ROOT, skip_hashes=False):
    policy=read_json(root/"project/policy.json")
    state=read_json(root/"project/tasks.json")
    issues=validate_registry(root,state)
    for relative,expected in expected_views(state).items():
        if not (root/relative).is_file() or (root/relative).read_text(encoding="utf-8")!=expected:
            issues.append(f"Generated task view drift: {relative}; run project.py render")
    paths=list(project_files(root))
    link_count=0
    module_ids={m["id"] for m in read_json(root/"project/modules.json")["modules"]}
    for document in policy["canonical_documents"]:
        if not local_path(root,document["path"]).is_file(): issues.append(f"Canonical document missing: {document['path']}")
        if document["owner"] not in module_ids: issues.append(f"Unknown document owner: {document['path']}")
    for path in paths:
        relative=path.relative_to(root).as_posix()
        if relative.split('/')[0] not in policy["allowed_roots"]: issues.append(f"Unclassified root entry: {relative}")
        if any(relative.startswith(p) for p in policy["archive_prefixes"]): continue
        if path.suffix in {".py",".ps1",".c",".h",".md",".json",".yml",".yaml",".txt"}:
            text=path.read_text(encoding="utf-8-sig")
            if SECRET.search(text): issues.append(f"Credential-like value in {relative} (value withheld)")
            if path.suffix==".md":
                text=re.sub(r"```.*?```","",text,flags=re.S)
                for target in re.findall(r"\]\(([^)\n]+)\)",text):
                    if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:|#",target): continue
                    from urllib.parse import unquote
                    target=unquote(target.strip('<>').split('#')[0])
                    link_count+=1
                    if target and not (path.parent/target).exists(): issues.append(f"Broken document link: {relative} -> {target}")
    source_index=read_json(root/"调研/原始来源/来源文件索引.json")
    source_ids=[source["id"] for source in source_index]
    if len(source_ids)!=len(set(source_ids)):
        issues.append("Archived source index contains duplicate IDs")
    hashes=0
    for source in source_index:
        if not source["available"]: continue
        path=local_path(root,"调研/原始来源/"+source["file"])
        if not path.is_file(): issues.append(f"Missing archived source: {source['id']}")
        elif not skip_hashes:
            if digest(path).lower()!=source["sha256"].lower(): issues.append(f"Archived bytes changed: {source['id']}")
            hashes+=1
    issues+=architecture_checks(root)
    import shutil, subprocess
    powershell=shutil.which('pwsh')
    ps_scripts=None
    if powershell:
        parsed=subprocess.run([powershell,'-NoProfile','-File',str(root/'scripts/check-powershell.ps1')],cwd=root,capture_output=True,encoding='utf-8',errors='replace',timeout=30)
        if parsed.returncode: issues.append('PowerShell syntax check failed: '+parsed.stdout+parsed.stderr)
        else: ps_scripts=json.loads(parsed.stdout)['scripts']
    from render_architecture import expected_architecture
    for relative,expected in expected_architecture(root).items():
        if not (root/relative).is_file() or (root/relative).read_text(encoding="utf-8")!=expected:
            issues.append(f"Generated architecture drift: {relative}; run render_architecture.py")
    return {"kind":"project-check","status":"PASS" if not issues else "FAIL", "tasks":len(state["tasks"]),
            "local_links":link_count,"powershell_scripts":ps_scripts,"source_hashes_checked":hashes,"known_unavailable_sources":[r['id'] for r in source_index if not r['available']],"issues":issues}


def staged_check(root=ROOT):
    problems=[]
    policy=read_json(root/"project/policy.json")
    paths=git(root,"diff","--cached","--name-only","--diff-filter=ACMR","-z",check=True).stdout.split('\0')
    for relative in filter(None,paths):
        blob=git(root,"show",":"+relative,check=True).stdout
        if SECRET.search(blob): problems.append(f"Staged credential-like value: {relative} (withheld)")
        size=git(root,"cat-file","-s",":"+relative,check=True)
        if int(size.stdout)>policy["max_new_blob_bytes"]:
            previous=git(root,"cat-file","-e","HEAD:"+relative)
            if previous.returncode: problems.append(f"New large blob requires an artifact storage decision: {relative}")
        protected=any(relative.startswith(p) for p in policy["archive_prefixes"]) or relative==policy["protected_file"]
        if protected and relative!="调研/原始来源/来源文件索引.json" and git(root,"cat-file","-e","HEAD:"+relative).returncode==0:
            old=git(root,"rev-parse","HEAD:"+relative).stdout.strip()
            new=git(root,"rev-parse",":"+relative).stdout.strip()
            if old!=new: problems.append(f"Immutable archive modified: {relative}; add a dated revision instead")
        if relative.startswith(("build/","results/local/")): problems.append(f"Generated local artifact staged: {relative}")
    deleted=git(root,"diff","--cached","--name-only","--diff-filter=D","-z",check=True).stdout.split('\0')
    for relative in filter(None,deleted):
        if any(relative.startswith(p) for p in policy["archive_prefixes"]) or relative==policy["protected_file"]:
            problems.append(f"Immutable archive deletion staged: {relative}")
    unstaged=git(root,"diff","--name-only","-z").stdout.split('\0')
    if any(p in set(paths) for p in filter(None,unstaged)):
        problems.append("Partially staged changed files: stage the reviewed complete file or separate the work before committing")
    indexed=set(filter(None,git(root,'ls-files','--cached','-z',check=True).stdout.split('\0')))
    state=read_json(root/'project/tasks.json')
    required=set(policy['generated_documents']) | {d['path'] for d in policy['canonical_documents']}
    for task in state['tasks']:
        if task['status'] in {'DONE','REVIEW'}:
            required.update(task['required_artifacts'])
            proof=task.get('verification')
            if proof and proof['kind']=='quality': required.add(proof['path'])
    for path in project_files(root):
        rel=path.relative_to(root).as_posix()
        if rel.startswith(('src/','include/','tools/','scripts/','project/','docs/architecture/','tests/')): required.add(rel)
    for rel in sorted(required-indexed): problems.append(f'Required project artifact not staged/tracked: {rel}')
    report=check(root)
    problems+=report["issues"]
    return {"kind":"staged-check","status":"PASS" if not problems else "FAIL","issues":problems}


def inventory(root):
    groups={};large=[]
    for path in project_files(root):
        rel=path.relative_to(root).as_posix();category=rel.split('/')[0];size=path.stat().st_size
        item=groups.setdefault(category,{'files':0,'bytes':0});item['files']+=1;item['bytes']+=size
        if size>10_000_000: large.append({'path':rel,'bytes':size})
    protected=set()
    for pointer in (root/'build').glob('*/latest.json'):
        try: protected.add(local_path(root,read_json(pointer)['manifest']).parent)
        except (ValueError,OSError,KeyError): pass
    older=[]
    for manifest in (root/'build/artifacts').glob('*/*/build-manifest.json'):
        try:
            data=read_json(manifest)
            if manifest.parent not in protected and data.get('status') in {'PASS','FAIL'}:
                older.append(manifest.parent.relative_to(root).as_posix())
        except (ValueError,OSError): pass
    return {'kind':'inventory','groups':groups,'large_files':large,'old_build_candidates':older,
            'cleanup_performed':False,'note':'Read-only candidates. Retain referenced evidence and inspect exact paths before any explicit cleanup; original archives are excluded from cleanup.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT)
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("render")
    checking=sub.add_parser("check"); checking.add_argument("--staged",action="store_true"); checking.add_argument("--skip-hashes",action="store_true")
    sub.add_parser("doctor")
    sub.add_parser('inventory')
    showing=sub.add_parser("show"); showing.add_argument("id")
    task=sub.add_parser("task"); task.add_argument("action",choices=["start","submit","complete","block","unblock","reopen","cancel","handoff"]); task.add_argument("id"); task.add_argument("--actor",required=True); task.add_argument("--note",required=True); task.add_argument("--evidence"); task.add_argument("--to")
    create=sub.add_parser("add"); create.add_argument("id"); create.add_argument("--title",required=True); create.add_argument("--actor",required=True); create.add_argument("--depends",action="append",default=[]); create.add_argument("--artifact",action="append",required=True); create.add_argument("--acceptance",action="append",required=True); create.add_argument("--priority",type=int,default=1)
    amend=sub.add_parser('amend');amend.add_argument('id');amend.add_argument('--actor',required=True);amend.add_argument('--note',required=True);amend.add_argument('--title');amend.add_argument('--depends',action='append');amend.add_argument('--artifact',action='append');amend.add_argument('--acceptance',action='append');amend.add_argument('--priority',type=int)
    context=sub.add_parser('context');context.add_argument('--task',required=True);context.add_argument('--actor',required=True);context.add_argument('--note',required=True);context.add_argument('--phase');context.add_argument('--evidence-cutoff');context.add_argument('--next',action='append');context.add_argument('--fact',action='append')
    args=parser.parse_args(); root=args.root.resolve()
    if args.command=="render":
        render_views(root); print("Rendered worknow.md and docs/tasks.md from task registry")
    elif args.command=="check":
        result=staged_check(root) if args.staged else check(root,args.skip_hashes)
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result["status"]=="PASS" else 1
    elif args.command=="doctor":
        print(json.dumps({"root":str(root),"branch":git(root,"branch","--show-current").stdout.strip(),"head":git(root,"rev-parse","--short","HEAD").stdout.strip(),"dirty":bool(git(root,"status","--porcelain").stdout),"remotes":git(root,"remote").stdout.splitlines(),"task_revision":read_json(root/"project/tasks.json")["revision"]},ensure_ascii=False,indent=2))
    elif args.command=='inventory': print(json.dumps(inventory(root),ensure_ascii=False,indent=2))
    elif args.command=="show":
        record=next((t for t in read_json(root/"project/tasks.json")["tasks"] if t["id"]==args.id),None)
        if record is None: raise ValueError("Task not found")
        print(json.dumps(record,ensure_ascii=False,indent=2))
    elif args.command=="task":
        print(json.dumps(transition(root,args.id,args.action,args.actor,args.note,args.evidence,args.to),ensure_ascii=False,indent=2))
    elif args.command=='amend':
        amend_task(root,args.id,args.actor,args.note,title=args.title,depends_on=args.depends,required_artifacts=args.artifact,acceptance=args.acceptance,priority=args.priority)
        print('Task contract amended with before/after history')
    elif args.command=='context':
        amend_context(root,args.task,args.actor,args.note,phase=args.phase,evidence_cutoff=args.evidence_cutoff,next_tasks=args.next,facts=args.fact)
        print('Work context amended with before/after history')
    else:
        add_task(root,args.id,args.title,args.actor,args.depends,args.artifact,args.acceptance,args.priority)
        print("Task added with dependencies and acceptance contract")
    return 0


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try: sys.exit(main())
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as exc:
        print(f"project: {exc}",file=sys.stderr); sys.exit(2)
