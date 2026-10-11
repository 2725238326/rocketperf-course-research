"""Run GCC's analyzer on every registered production C translation unit."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from projectlib import ROOT, atomic_json, atomic_text, digest, local_path, now, read_json, subprocess_env


def analyze(destination: Path, compiler: str = "gcc"):
    if destination.exists() or not destination.resolve().is_relative_to((ROOT / "build").resolve()):
        raise ValueError("Choose an unused analysis directory under build/")
    executable = shutil.which(compiler)
    if not executable:
        raise ValueError("GCC compiler not found")
    registry = read_json(ROOT / "project/modules.json")
    sources = [source for module in registry["modules"] for source in module["sources"]]
    inputs = sorted(set(sources + ["project/modules.json", "tools/static_analysis.py"] +
                        [p.relative_to(ROOT).as_posix() for base in ("include", "src")
                         for p in (ROOT / base).rglob("*.h")]))
    identities = {name: digest(ROOT / name) for name in inputs}
    destination.mkdir(parents=True)
    version = subprocess.run([executable, "--version"], capture_output=True, text=True,
                             check=True, timeout=20, env=subprocess_env()).stdout
    record = dict(schema_version=1, status="RUNNING", started_at=now(), compiler=executable,
                  compiler_version=version, inputs=identities, checks=[])
    report = destination / "analysis.json"
    atomic_json(report, record)
    flags = ["-std=c17", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
             "-Wconversion", "-Wshadow", "-Wstrict-prototypes", "-Wmissing-prototypes",
             "-fno-common", "-fanalyzer", "-Iinclude", "-Isrc/adapters"]
    try:
        for index, source in enumerate(sources):
            command = [executable, *flags, "-c", source, "-o", str(destination / f"{index:02d}.o")]
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=120, env=subprocess_env())
            log = destination / f"{index:02d}.log"
            atomic_text(log, run.stdout + run.stderr)
            record["checks"].append(dict(source=source, command=command, exit_code=run.returncode,
                                         log=log.relative_to(ROOT).as_posix(), log_sha256=digest(log)))
            atomic_json(report, record)
            print(f"Analyzer {index + 1}/{len(sources)}: {source}", flush=True)
            if run.returncode:
                raise ValueError(f"Analyzer failed: {source}; see {log}")
        if identities != {name: digest(ROOT / name) for name in inputs}:
            raise ValueError("Analysis inputs changed during execution")
        record["status"] = "PASS"
    except Exception as exc:
        record.update(status="FAIL", error=str(exc))
        raise
    finally:
        record["finished_at"] = now()
        atomic_json(report, record)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--compiler", default="gcc")
    args = parser.parse_args()
    try:
        print(analyze(local_path(ROOT, args.destination), args.compiler))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
