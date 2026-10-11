"""Compare frozen-nozzle CPU time against a fixed Git version, using identical inputs."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

from projectlib import ROOT, atomic_json, atomic_text, digest, git, local_path, now, read_json, strict_json, subprocess_env


def benchmark(destination: Path, baseline: str, samples: int):
    if destination.exists() or not destination.resolve().is_relative_to((ROOT / "build").resolve()):
        raise ValueError("Choose an unused benchmark directory under build/")
    if not 3 <= samples <= 31:
        raise ValueError("Use 3..31 alternating samples")
    compiler = shutil.which("gcc")
    if not compiler:
        raise ValueError("GCC compiler not found")
    head = git(ROOT, "rev-parse", baseline + "^{commit}", check=True).stdout.strip()
    modules = read_json(ROOT / "project/modules.json")["modules"]
    sources = [source for module in modules if module["id"] in {"core", "thermo", "nozzle", "cycle"}
               for source in module["sources"]]
    destination.mkdir(parents=True)
    binaries = {}
    identities = {}
    flags = ["-std=c17", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
             "-Wconversion", "-Wshadow", "-Wstrict-prototypes", "-Wmissing-prototypes", "-Iinclude"]
    for label in ("before", "after"):
        folder = destination / label
        folder.mkdir()
        names = sources + [p.relative_to(ROOT).as_posix() for base in ("include", "src")
                           for p in (ROOT / base).rglob("*.h")]
        for name in names:
            data = ((ROOT / name).read_bytes() if label == "after" else
                    subprocess.run(["git", "show", head + ":" + name], cwd=ROOT,
                                   capture_output=True, check=True, timeout=20).stdout)
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        driver = folder / "benchmark_frozen.c"
        driver.write_bytes((ROOT / "tools/benchmark_frozen.c").read_bytes())
        identities[label] = {name: digest(folder / name) for name in names}
        binary = folder / ("benchmark.exe" if sys.platform == "win32" else "benchmark")
        command = [compiler, *flags, *sources, driver.name, "-lm", "-o", str(binary)]
        run = subprocess.run(command, cwd=folder, capture_output=True, encoding="utf-8",
                             errors="replace", timeout=120, env=subprocess_env())
        atomic_text(destination / (label + "-build.log"), run.stdout + run.stderr)
        if run.returncode:
            raise ValueError("Benchmark build failed: " + label)
        binaries[label] = binary
    measurements = {label: [] for label in binaries}
    for index in range(samples):
        order = ("before", "after") if index % 2 == 0 else ("after", "before")
        for label in order:
            run = subprocess.run([str(binaries[label])], capture_output=True, encoding="utf-8",
                                 check=True, timeout=30, env=subprocess_env())
            value = strict_json(run.stdout)
            if value["runs"] != 2000 or value["cpu_seconds"] <= 0:
                raise ValueError("Invalid benchmark output")
            measurements[label].append(value)
    checksums = {item["checksum_thrust_n"] for items in measurements.values() for item in items}
    if len(checksums) != 1:
        raise ValueError("Benchmark numeric checksum changed")
    medians = {label: statistics.median(item["cpu_seconds"] for item in items)
               for label, items in measurements.items()}
    record = dict(schema_version=1, status="PASS", finished_at=now(), baseline_head=head,
                  compiler=compiler, flags=flags, driver_sha256=digest(ROOT / "tools/benchmark_frozen.c"),
                  source_hashes=identities, binary_hashes={label: digest(path) for label, path in binaries.items()},
                  samples=measurements, median_cpu_seconds=medians,
                  reduction_fraction=1 - medians["after"] / medians["before"],
                  note="Single-machine CPU benchmark for 2000 fixed-composition A10/A40 solves; not engine accuracy or a universal speed claim")
    report = destination / "benchmark.json"
    atomic_json(report, record)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--samples", type=int, default=9)
    args = parser.parse_args()
    try:
        print(benchmark(local_path(ROOT, args.destination), args.baseline, args.samples))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
