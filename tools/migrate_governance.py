"""One-time migration of the reviewed manual task board; never overwrites state."""
import hashlib
import re
from projectlib import ROOT, atomic_json, canonical, now

if __name__ == "__main__":
    target = ROOT / "project/tasks.json"
    if target.exists():
        raise SystemExit("Task registry already exists; migration refused")
    requirements = {
        "ORG-001":["AGENTS.md","taskshot/2026-10-01_001_project-foundation.md"],
        "PLAN-001":["docs/project-plan.md","taskshot/2026-10-01_002_project-plan.md"],
        "ENG-001":["docs/engineering.md","taskshot/2026-10-01_003_engineering-foundation.md"],
        "OPS-001":["scripts/build.ps1","docs/environment.md"],
        "IMP-000":["src/nozzle/ideal.c","docs/benchmarks.md","tests/test_core.c"],
        "RES-001":["调研/专题/RES-001_型号版本与参数缺口.md"],
        "RES-002":["调研/专题/RES-002_C移植评估.md"],
        "RES-003":["调研/专题/RES-003_公式与基准.md"],
        "RES-004":["调研/专题/RES-004_热化学与循环范围.md"],
        "RES-005":["调研/专题/RES-005_复用约束与改进候选.md"],
        "DATA-001":["data/parameters/baseline.json"],
        "DES-001":["docs/model-design.md"],
        "IMP-001":["docs/model-implementation.md"],
        "VAL-001":["docs/model-validation.md"],
        "ANA-001":["docs/study-results.md"],
        "DOC-001":["deliverables/README.md"],
        "REL-001":["deliverables/release-manifest.json"]
    }
    deps = {"PLAN-001":["ORG-001"],"ENG-001":["PLAN-001"],"OPS-001":["ORG-001"],
            "IMP-000":["OPS-001"],"RES-004":["RES-001","RES-002","RES-003"],
            "DATA-001":["RES-001","RES-003"],"DES-001":["RES-002","RES-003","RES-004","RES-005"],
            "IMP-001":["DES-001","IMP-000","DATA-001"],"VAL-001":["IMP-001"],
            "ANA-001":["VAL-001","DATA-001"],"DOC-001":["ANA-001"],"REL-001":["IMP-001","VAL-001","DOC-001"]}
    tasks = []
    for line in (ROOT / "docs/tasks.md").read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| [A-Z]+-\d{3} \|", line):
            continue
        columns = [x.strip() for x in line.strip("|").split("|")]
        task_id, title, status = columns[:3]
        tasks.append({"id":task_id,"title":title,"status":status,"priority":1 if task_id.startswith("RES") else 2,
                      "depends_on":deps.get(task_id,[]),"required_artifacts":requirements[task_id],
                      "acceptance":[columns[-1]],"owner":None,"note":"从已审阅手工任务板迁移；不是重新执行任务。",
                      "verification":{"kind":"historical","reference":"taskshot/2026-10-01_003_engineering-foundation.md"} if status=="DONE" else None})
    tasks.append({"id":"GOV-001","title":"任务、文档、Git、目录与架构视图重构","status":"ACTIVE","priority":0,
                  "depends_on":["ENG-001"],"required_artifacts":["docs/governance.md","docs/architecture/README.md","docs/architecture/index.html","tools/project.py","tools/quality.py","tests/test_governance.py"],
                  "acceptance":["状态流转、依赖、验收和生成视图可自动核对","Git有可恢复基线及经过检查的治理提交，无外部推送","三张架构视图与代码/模块登记一致并经视觉检查","构建测试/运行证据不接受过期通过状态，失败和并发有明确行为"],
                  "owner":"root","note":"用户已要求全面优化；本轮主任务。","verification":None})
    events = []
    for task in tasks:
        event = {"seq":len(events)+1,"at":now(),"task":task["id"],"from":None,"to":task["status"],
                 "actor":"migration","owner_after":task["owner"],"note":task["note"],
                 "previous_hash":events[-1]["hash"] if events else "0"*64}
        event["hash"] = hashlib.sha256(canonical(event)).hexdigest()
        events.append(event)
    atomic_json(target,{"schema_version":1,"revision":1,"context":{"phase":"C17教学基线可用；真实型号研究待深化", "evidence_cutoff":"2026-09-29", "next_tasks":["RES-001","RES-002","RES-003"],"facts":["核心为定比热理想喷管，不能作为真实发动机性能预测","本机GCC Debug/Release已验证；CMake/远端CI/Linux验证状态须据实际报告","已有43份来源快照与5份PDF，来源新鲜度与文件完整性分别核验"]},"tasks":tasks,"events":events})
    print(f"Migrated {len(tasks)} tasks; GOV-001 is ACTIVE")
