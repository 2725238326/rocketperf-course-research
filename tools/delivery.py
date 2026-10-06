"""Create reviewed C-source and Windows archives from one clean tested Git commit."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile
from xml.etree import ElementTree

from cea_reference import parse_output
from combustion_reference import compare_report
from cycle_validation import validate_cycle
from kerosene_validation import inputs as rp1_inputs
from pipeline import validate_result, verified_build, verify_test_report
from project import quality_proof
from projectlib import ROOT, atomic_json, atomic_text, canonical, digest, git, local_path, now, read_json, strict_json, subprocess_env
from research_tp_reference import run_logged

KINDS = {"c-source", "windows-x64"}
REPOSITORY = "https://github.com/2725238326/rocketperf-course-research"
ARCHIVES = {"c-source": "rocketperf-c-source.zip", "windows-x64": "rocketperf-windows-x64.zip"}
LICENSES = {
    "third_party/cea/LICENSE.txt": "调研/原始来源/20261003_cea_v3.3.4/LICENSE.txt",
    "third_party/cea/NOTICE.txt": "调研/原始来源/20261003_cea_v3.3.4/NOTICE.txt",
    "third_party/coolprop/LICENSE.txt": "调研/原始来源/F04_coolprop_license_7_1_0.txt",
    "third_party/coolprop/BIBLIOGRAPHY.txt": "调研/原始来源/F07_coolprop_bibliography_7_1_0.txt",
}
DEMO_ARGS = [
    ("ideal", ["run", "cases/benchmarks/air_mach2_vacuum.ini"], 0),
    ("cycle", ["cycle", "prescribed", "cases/benchmarks/prescribed_cycle.ini"], 0),
    ("rp1", ["combustion", "frozen-rp1", "cea-v3.3.4-rp1-o2l-assigned-v1", "liquid", "RP-1", "O2(L)",
             "10000000", "2.6", "298.15", "90.170", "10", "0", "0.01"], 0),
    ("rejection", ["run", "tests/fixtures/overexpanded.ini"], 4),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_member(name):
    if (not isinstance(name, str) or not name or "\\" in name or ":" in name
        or name.startswith("/") or any(part in {"", ".", ".."} for part in name.split("/"))):
        raise ValueError("Unsafe delivery member path")
    return name


def write_zip(path, kind, head, files):
    if path.exists():
        raise FileExistsError("Delivery archive already exists")
    if kind not in KINDS or not re.fullmatch("[a-f0-9]{40}", head):
        raise ValueError("Invalid delivery kind or commit")
    for name in files:
        safe_member(name)
    if "PACKAGE.json" in files:
        raise ValueError("Reserved delivery manifest path")
    manifest = dict(schema_version=1, kind=kind, source_head=head,
                    files={name: sha(data) for name, data in sorted(files.items())})
    payload = dict(files, **{"PACKAGE.json": canonical(manifest) + b"\n"})
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return inspect_zip(path, kind, head)


def inspect_zip(path, kind, head):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        if len(names) != len(set(names)) or "PACKAGE.json" not in names:
            raise ValueError("Ambiguous or missing ZIP manifest")
        for entry in entries:
            safe_member(entry.filename)
            if entry.is_dir() or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Delivery ZIP contains a directory or symbolic link entry")
            if entry.file_size > 25_000_000:
                raise ValueError("Unexpected oversized delivery member")
        if sum(item.file_size for item in entries) > 50_000_000:
            raise ValueError("Delivery ZIP exceeds the selected source/runtime scope")
        record = strict_json(archive.read("PACKAGE.json").decode("utf-8"))
        if (not isinstance(record, dict) or set(record) != {"schema_version", "kind", "source_head", "files"}
            or type(record["schema_version"]) is not int or record["schema_version"] != 1
            or kind not in KINDS or record["kind"] != kind or record["source_head"] != head
            or not isinstance(record["files"], dict) or not record["files"]):
            raise ValueError("Delivery manifest identity differs")
        if set(names) != set(record["files"]) | {"PACKAGE.json"}:
            raise ValueError("Delivery ZIP file declaration differs")
        for name, identity in record["files"].items():
            if not isinstance(identity, str) or not re.fullmatch("[a-f0-9]{64}", identity) or sha(archive.read(name)) != identity:
                raise ValueError("Delivery ZIP file hash differs")
        if any(Path(name).suffix.lower() in {".py", ".pyc", ".f", ".f90", ".dll", ".bundle"}
               or name.startswith(("tools/", ".git/")) for name in names):
            raise ValueError("Delivery ZIP contains excluded development/runtime files")
        required = {"README.md", "docs/project-guide.md", "third_party/cea/LICENSE.txt",
                    "third_party/cea/NOTICE.txt", "third_party/coolprop/LICENSE.txt"}
        required |= {"CMakeLists.txt", "project/modules.json", "src/cli/main.c"} if kind == "c-source" else {"rocketperf.exe"}
        if not required <= set(names):
            raise ValueError("Required delivery files missing")
        return record


def extract_checked(path, destination, kind, head):
    inspect_zip(path, kind, head)
    if destination.exists():
        raise FileExistsError("Delivery extraction target already exists")
    destination.mkdir(parents=True)
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            target = local_path(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))


def read_commit(root, head, path):
    safe_member(path)
    return subprocess.run(["git", "show", head + ":" + path], cwd=root, capture_output=True,
                          check=True, timeout=20).stdout


def diagram(data):
    root = ElementTree.fromstring(data)
    for item in root.iter():
        if item.tag.endswith("}a"):
            item.tag = "{http://www.w3.org/2000/svg}g"
            item.attrib.pop("href", None)
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def common_files(root, head):
    files = {"docs/project-guide.md": read_commit(root, head, "docs/project-guide.md")}
    if git(root, 'cat-file', '-e', head+':docs/propellant-method-comparison.md').returncode == 0:
        for path in ('docs/propellant-method-comparison.md', 'docs/propellant-comparison.svg'):
            files[path] = read_commit(root, head, path)
    for name in ("assignment", "business", "components", "workflow"):
        files["docs/architecture/" + name + ".svg"] = diagram(read_commit(root, head, "docs/architecture/" + name + ".svg"))
    for name, original in LICENSES.items():
        files[name] = read_commit(root, head, original)
    for name in ("air_mach2_vacuum", "prescribed_cycle"):
        relative = "cases/benchmarks/" + name + ".ini"
        files[relative] = read_commit(root, head, relative)
    files["tests/fixtures/overexpanded.ini"] = read_commit(root, head, "tests/fixtures/overexpanded.ini")
    files["DATA-SOURCES.md"] = (
        "# 数据与许可\n\n固定提交：" + head + "\n\n"
        "NASA9与指定CH4(L)/O2(L)/RP-1常量提取自NASA CEA v3.3.4；上游Apache-2.0 LICENSE/NOTICE随包。\n\n"
        "单相CH4/O2查表来自CoolProp7.1.0 HEOS离线参考，MIT和书目随包；C运行没有上游求解库依赖。\n\n"
        "完整参数、参考原文及哈希保留于私有仓库：" + REPOSITORY + "/tree/" + head + "\n\n"
        "项目自有代码尚未选择对外许可证。本包供授权小组维护和课程接收，未声明公开再分发许可。\n\n"
        "包内SVG保留布局/文字，移除了指向完整仓库的局部跳转；原图/生成源在仓库保留。\n"
    ).encode("utf-8")
    return files


def package_readme(kind, head):
    command = ("cmake -S . -B build/cmake -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_BUILD_TYPE=Release "
               "-DBUILD_TESTING=ON -DROCKETPERF_ENABLE_PYTHON_TESTS=OFF\ncmake --build build/cmake\n"
               "ctest --test-dir build/cmake --output-on-failure\n" if kind == "c-source" else
               "./rocketperf.exe run cases/benchmarks/air_mach2_vacuum.ini\n"
               "./rocketperf.exe combustion frozen-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 'O2(L)' 10000000 2.6 298.15 90.170 10 0 0.01\n"
               "./rocketperf.exe run tests/fixtures/overexpanded.ini\n$LASTEXITCODE\n")
    return ("# Rocketperf " + ("纯C源码包" if kind == "c-source" else "Windows x64运行包") +
            "\n\n固定Git提交：" + head + "\n\n"
            "项目详细解读：[docs/project-guide.md](docs/project-guide.md)。数据许可见DATA-SOURCES.md和third_party。\n\n"
            "源码构建需要Windows GCC/CMake/Ninja；exe运行只需Windows系统库。没有Python/Fortran生产依赖。\n\n"
            "```powershell\n" + command + "```\n\n"
            "拒绝算例退出4、stdout为空；成功输出JSON。阶段方法结果不可贴真实发动机性能标签。\n\n"
            "完整研究资料与维护记录见私有仓库。PACKAGE.json核对逐文件SHA256，Release外部SHA256SUMS.txt核对ZIP来源。\n").encode("utf-8")


def check_demo(name, stdout, stderr, code):
    expected = next(item[2] for item in DEMO_ARGS if item[0] == name)
    if code != expected or (code == 0 and stderr) or (code != 0 and (stdout or not stderr.startswith("out_of_domain:"))):
        raise ValueError("Delivery demonstration protocol differs: " + name)
    if code != 0:
        return
    report = strict_json(stdout)
    if name == "ideal":
        validate_result(report, (ROOT / "cases/benchmarks/air_mach2_vacuum.ini").read_text(encoding="utf-8"))
    elif name == "cycle":
        validate_cycle(report, (ROOT / "cases/benchmarks/prescribed_cycle.ini").read_text(encoding="utf-8"))
    elif name == "rp1":
        reference = ROOT / "results/validation/kerosene_anchor_v1/of_2_6_rocket.out"
        summary = parse_output(reference.read_bytes(), True, True, 1e-7)
        compare_report(report, dict(summary=summary), "frozen-rp1", 10, expected_inputs=rp1_inputs(2.6, 10))


def demos(binary, folder, logs, prefix):
    clean = subprocess_env()
    clean["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    results = []
    for name, arguments, code in DEMO_ARGS:
        stdout = logs / (prefix + "-" + name + "-stdout.json")
        stderr = logs / (prefix + "-" + name + "-stderr.txt")
        run = subprocess.run([str(binary), *arguments], cwd=folder, env=clean,
                             capture_output=True, encoding="utf-8", errors="strict", timeout=30)
        atomic_text(stdout, run.stdout)
        atomic_text(stderr, run.stderr)
        check_demo(name, run.stdout, run.stderr, run.returncode)
        results.append(dict(id=name, arguments=arguments, exit_code=code))
    return results


def create(destination, cmake=None, ninja=None):
    if os.name != "nt":
        raise ValueError("This delivery targets Windows only")
    if destination.exists():
        raise FileExistsError("Choose an unused delivery destination")
    if not destination.resolve().is_relative_to((ROOT / "build").resolve()):
        raise ValueError("Local delivery artifacts belong under build/")
    if git(ROOT, "status", "--porcelain", check=True).stdout.strip():
        raise ValueError("Commit reviewed changes before packaging")
    quality = quality_proof(ROOT, "build/quality/latest.json")
    build_path = verified_build(ROOT, "Release", require_tests=True)
    build = read_json(build_path)
    tests = read_json(build_path.parent / "test-report.json")
    verify_test_report(tests, build, digest(build_path))
    head = git(ROOT, "rev-parse", "HEAD", check=True).stdout.strip()
    cmake = Path(cmake or ROOT / "build/tooling/cmake/data/bin/cmake.exe").resolve(strict=True)
    ninja = Path(ninja or ROOT / "build/tooling/bin/ninja.exe").resolve(strict=True)
    destination.mkdir(parents=True)
    logs = destination / "verification"
    logs.mkdir()
    record = dict(schema_version=1, kind="windows-course-delivery", status="RUNNING", started_at=now(),
                  source_head=head, repository=REPOSITORY, quality_fingerprint=quality["input_fingerprint"])
    atomic_json(destination / "delivery-manifest.json", record)
    try:
        common = common_files(ROOT, head)
        tracked = git(ROOT, "ls-files", "-z", check=True).stdout.split("\0")
        selected = [name for name in tracked if name and
                    (name.startswith(("src/", "include/")) or name in {"CMakeLists.txt", "project/modules.json"}
                     or (name.startswith("tests/") and Path(name).suffix in {".c", ".h"}))]
        source = dict(common, **{name: read_commit(ROOT, head, name) for name in selected})
        source["README.md"] = package_readme("c-source", head)
        executable = local_path(ROOT, build["application"]["path"])
        objdump = Path(build["compiler"]).with_name("objdump.exe")
        imports = subprocess.run([str(objdump), "-p", str(executable)], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", check=True, timeout=30).stdout
        dependencies = re.findall(r"DLL Name:\s+(\S+)", imports)
        if not dependencies or any(name.lower() not in {"kernel32.dll", "msvcrt.dll", "ucrtbase.dll"}
                                   and not name.lower().startswith("api-ms-win-") for name in dependencies):
            raise ValueError("Windows delivery has uncollected non-system DLL dependencies")
        atomic_text(logs / "windows-imports.txt", imports)
        runtime = dict(common, **{"rocketperf.exe": executable.read_bytes(), "README.md": package_readme("windows-x64", head)})
        record.update(binary_sha256=digest(executable), windows_imports=dependencies, archives={})
        path = destination / ARCHIVES['c-source']
        packed = write_zip(path, 'c-source', head, source)
        record['archives']['c-source'] = dict(path=path.name, sha256=digest(path), bytes=path.stat().st_size,
                                             files=len(packed['files']))
        extract_checked(path, destination / 'c-source', 'c-source', head)
        runtime_root = destination / 'windows-x64'
        runtime_root.mkdir()
        for name, data in runtime.items():
            target = local_path(runtime_root, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        atomic_json(logs / "quality-report.json", quality)
        shutil.copy2(build_path, logs / "build-manifest.json")
        shutil.copy2(build_path.parent / "test-report.json", logs / "test-report.json")
        croot = destination / "c-source"
        commands = [
            [str(cmake), "-S", str(croot), "-B", str(croot / "build"), "-G", "Ninja",
             "-DCMAKE_MAKE_PROGRAM=" + str(ninja), "-DCMAKE_C_COMPILER=" + build["compiler"],
             "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_TESTING=ON", "-DROCKETPERF_ENABLE_PYTHON_TESTS=OFF"],
            [str(cmake), "--build", str(croot / "build")],
            [str(cmake.with_name("ctest.exe")), "--test-dir", str(croot / "build"), "--output-on-failure"],
        ]
        for index, command in enumerate(commands):
            run = run_logged(command, croot, logs / f"source-{index}-stdout.txt", logs / f"source-{index}-stderr.txt", 180)
            if run.returncode:
                raise ValueError("Pure C source configure/build/test failed")
        if "100% tests passed, 0 tests failed out of 5" not in run.stdout:
            raise ValueError("Expected five executed pure-C tests")
        record["source_build"] = dict(status="PASS", tests=5, commands=commands,
                                      demonstrations=demos(croot / "build/rocketperf.exe", croot, logs, "source"))
        record["runtime_demonstrations"] = demos(destination / "windows-x64/rocketperf.exe", destination / "windows-x64", logs, "runtime")
        runtime.update({p.relative_to(destination).as_posix(): p.read_bytes() for p in logs.iterdir()})
        path = destination / ARCHIVES['windows-x64']
        packed = write_zip(path, 'windows-x64', head, runtime)
        record['archives']['windows-x64'] = dict(path=path.name, sha256=digest(path), bytes=path.stat().st_size,
                                                 files=len(packed['files']))
        atomic_text(destination / "project-guide.md", common["docs/project-guide.md"].decode("utf-8"))
        if (git(ROOT, "rev-parse", "HEAD", check=True).stdout.strip() != head
            or git(ROOT, "status", "--porcelain", check=True).stdout.strip()
            or quality_proof(ROOT, "build/quality/latest.json") != quality):
            raise ValueError("Source/quality changed while packaging")
        record["verification_files"] = {p.relative_to(destination).as_posix(): digest(p) for p in sorted(logs.iterdir())}
        record.update(status="PASS", finished_at=now())
        atomic_json(destination / "delivery-manifest.json", record)
        sums = [f"{digest(destination / name)}  {name}" for name in
                [*ARCHIVES.values(), "delivery-manifest.json", "project-guide.md"]]
        atomic_text(destination / "SHA256SUMS.txt", "\n".join(sums) + "\n")
        verify(destination)
    except Exception as exc:
        record.update(status="FAIL", error=str(exc), finished_at=now())
        atomic_json(destination / "delivery-manifest.json", record)
        raise
    return destination


def verify(directory):
    record = read_json(directory / "delivery-manifest.json")
    if (not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != 1
        or record.get("kind") != "windows-course-delivery" or record.get("status") != "PASS"
        or not isinstance(record.get("source_head"), str) or not re.fullmatch("[a-f0-9]{40}", record["source_head"])
        or set(record.get("archives", {})) != KINDS):
        raise ValueError("Delivery summary identity differs")
    for kind, entry in record["archives"].items():
        if entry["path"] != ARCHIVES[kind]:
            raise ValueError("Delivery archive name differs")
        path = local_path(directory, entry["path"])
        if digest(path) != entry["sha256"] or type(entry["bytes"]) is not int or path.stat().st_size != entry["bytes"]:
            raise ValueError("Delivery archive hash or size differs")
        packed = inspect_zip(path, kind, record["source_head"])
        if type(entry["files"]) is not int or len(packed["files"]) != entry["files"]:
            raise ValueError("Delivery archive file count differs")
        if kind == "windows-x64" and packed["files"]["rocketperf.exe"] != record["binary_sha256"]:
            raise ValueError("Delivery binary identity differs")
    evidence = record["verification_files"]
    actual = {p.relative_to(directory).as_posix() for p in (directory / "verification").iterdir() if p.is_file()}
    if not isinstance(evidence, dict) or set(evidence) != actual:
        raise ValueError("Delivery verification evidence differs")
    required_logs = {'verification/quality-report.json', 'verification/build-manifest.json', 'verification/test-report.json',
                     'verification/windows-imports.txt'}
    required_logs |= {f'verification/source-{i}-{stream}.txt' for i in range(3) for stream in ('stdout', 'stderr')}
    required_logs |= {f'verification/{prefix}-{name}-{stream}.{extension}'
                     for prefix in ('source', 'runtime') for name, *_ in DEMO_ARGS
                     for stream, extension in (('stdout', 'json'), ('stderr', 'txt'))}
    if set(evidence) != required_logs:
        raise ValueError('Delivery required verification logs missing')
    for path, identity in evidence.items():
        if digest(local_path(directory, path)) != identity:
            raise ValueError("Delivery verification bytes changed")
    quality = read_json(directory / "verification/quality-report.json")
    if quality["status"] != "PASS" or quality["input_fingerprint"] != record["quality_fingerprint"]:
        raise ValueError("Delivery quality identity differs")
    build = read_json(directory / "verification/build-manifest.json")
    verify_test_report(read_json(directory / "verification/test-report.json"), build, digest(directory / "verification/build-manifest.json"))
    if build["application"]["sha256"] != record["binary_sha256"]:
        raise ValueError("Delivery tested binary differs")
    source = record["source_build"]
    if source["status"] != "PASS" or type(source["tests"]) is not int or source["tests"] != 5:
        raise ValueError("Missing pure-C source build evidence")
    if '100% tests passed, 0 tests failed out of 5' not in (directory/'verification/source-2-stdout.txt').read_text(encoding='utf-8'):
        raise ValueError('Pure-C CTest log is incomplete')
    for prefix, results in (("source", source["demonstrations"]), ("runtime", record["runtime_demonstrations"])):
        expected = [dict(id=name, arguments=args, exit_code=code) for name, args, code in DEMO_ARGS]
        from adiabatic_study import typed_equal
        typed_equal(results, expected, "delivery demonstrations")
        for item in results:
            name = prefix + "-" + item["id"]
            check_demo(item["id"], (directory / "verification" / (name + "-stdout.json")).read_text(encoding="utf-8"),
                       (directory / "verification" / (name + "-stderr.txt")).read_text(encoding="utf-8"), item["exit_code"])
    expected_sums = "\n".join(f"{digest(directory / name)}  {name}" for name in
                              [*ARCHIVES.values(), "delivery-manifest.json", "project-guide.md"]) + "\n"
    if (directory / "SHA256SUMS.txt").read_text(encoding="utf-8") != expected_sums:
        raise ValueError("Delivery checksums differ")
    return record["source_head"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    creating = sub.add_parser("create")
    creating.add_argument("--destination", required=True)
    creating.add_argument("--cmake")
    creating.add_argument("--ninja")
    checking = sub.add_parser("verify")
    checking.add_argument("--directory", required=True)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        print(create(local_path(ROOT, args.destination), args.cmake, args.ninja) if args.action == "create"
              else "Delivery verified: " + verify(local_path(ROOT, args.directory)))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
