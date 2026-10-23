"""Capture and verify the immutable, user-supplied Work2 source files."""
from __future__ import annotations

import argparse
import re
import sys

from projectlib import ROOT, atomic_json, digest, local_path, read_json

MANIFEST = "Work2/project/sources-20261023.json"
RAW_PATHS = (
    "Work2/作业要求.png",
    "Work2/参考内容.png",
    "Work2/提示词/start0.md",
)
COURSE_DIR = "Work2/火箭发动机原理-第五章推力室的热力计算"


def source_paths(root):
    return sorted((*RAW_PATHS, *(p.relative_to(root).as_posix()
                  for p in (root/COURSE_DIR).rglob("*") if p.is_file())))


def capture(root=ROOT):
    target=root/MANIFEST
    if target.exists():
        raise ValueError("Source snapshot exists; preserve it and add a dated revision for new sources")
    rows=[]
    for index,relative in enumerate(source_paths(root),1):
        path=local_path(root,relative)
        rows.append({"id":f"W2SRC-{index:03}","path":relative,
                     "bytes":path.stat().st_size,"sha256":digest(path)})
    atomic_json(target,{"schema_version":1,"captured_on":"2026-10-23",
                        "scope":"User-supplied originals; paths and bytes are immutable",
                        "files":rows})
    return {"manifest":MANIFEST,"files":len(rows)}


def check_sources(root=ROOT, *, skip_hashes=False):
    target=root/MANIFEST
    if not target.is_file():
        # Legacy clones and isolated governance test fixtures have no Work2 sources.
        exists=any((root/p).is_file() for p in RAW_PATHS) or (root/COURSE_DIR).exists()
        return {"checked":0,"issues":["Work2 source manifest missing"] if exists else []}
    issues=[]; checked=0; seen=set()
    try:
        data=read_json(target)
        if data.get("schema_version")!=1 or not isinstance(data.get("files"),list) or not data["files"]:
            raise ValueError("Invalid Work2 source manifest")
        for row in data["files"]:
            relative=row["path"]
            if relative in seen or not re.fullmatch(r"[0-9a-f]{64}",row["sha256"]):
                raise ValueError("Duplicate path or invalid digest in Work2 source manifest")
            seen.add(relative)
            path=local_path(root,relative)
            if not path.is_file():
                issues.append("Work2 original missing: "+relative)
            elif path.stat().st_size!=row["bytes"]:
                issues.append("Work2 original size changed: "+relative)
            elif not skip_hashes:
                checked+=1
                if digest(path)!=row["sha256"]:
                    issues.append("Work2 original bytes changed: "+relative)
        if seen!=set(source_paths(root)):
            issues.append("Work2 original coverage changed; retain the baseline and register a dated source revision")
    except (ValueError,KeyError,TypeError,OSError) as exc:
        issues.append("Work2 source verification failed: "+str(exc))
    return {"checked":checked,"issues":issues}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("capture","verify"))
    args=parser.parse_args()
    import json
    result=capture() if args.command=="capture" else check_sources()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if result.get("issues") else 0


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
