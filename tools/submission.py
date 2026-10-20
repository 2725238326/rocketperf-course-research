"""Assemble the four course deliverables from a verified local delivery.

The maintained inventory stays in deliverables; build logs and local paths stay
in build. Original reports, slides and research archives are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from delivery import verify
from projectlib import ROOT, digest, git, read_json

DEST = ROOT / "deliverables/submission-20261020"
ARCHIVE = ROOT / "deliverables/第五组_第一次大作业_20261020.zip"
FOLDERS = ("01_程序源代码", "02_程序发布版", "03_展示PPT", "04_作业报告")

SOURCE_README = """# 火箭动力系统性能计算程序

核心算法、输入输出及命令行程序使用 C17。图形界面通过 WebView2 显示
本地页面，在进程内调用同一套 C 计算核心；窗口宿主使用第三方 C++ 组件。

## 编译控制台版

需要 Windows x64、GCC、CMake 3.19 或更新版本，以及 Ninja。在本目录执行：

```powershell
cmake -S . -B build/cmake -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DROCKETPERF_ENABLE_PYTHON_TESTS=OFF
cmake --build build/cmake
ctest --test-dir build/cmake --output-on-failure
./build/cmake/rocketperf.exe interactive
```

上述构建和五项 C 测试不依赖 Python。`src/` 为实现，`include/` 为公共接口，
`tests/` 为 C 测试，`cases/` 为输入文件，`project/modules.json` 为源码清单。
物性数据已固化在 C 源码中，无须联网下载。

## 编译图形界面版

另需 GCC 配套的 G++、windres，以及 Python 3.10 或更新版本的标准库。
在本目录执行 `python tools/gui_build.py --dist`。
输出为 `build/gui/dist/RocketPerf-GUI/`，启动 `rocketperf-gui.exe`。
`src/gui/web/` 保存界面，`src/gui/` 保存 C 桥接与宿主入口；第三方窗口
组件及 WebView2 SDK 头文件在 `third_party/`，许可文件随源码提供。
Python 仅用于组织编译，不参与发布程序的性能计算。

图形界面核验可运行 `python tests/test_gui.py --bridge build/gui/gui_bridge_stdio.exe --cli build/cmake/rocketperf.exe`。
安装 Node.js 后，还可运行 `node tests/test_gui_frontend.mjs --cli build/cmake/rocketperf.exe`，
核对真实 C 回复的前端计数及 PowerShell 复制命令。

## 算例与适用范围

控制台菜单 8 提供五个两型火箭级段背景的循环研究情景，也可运行：

```powershell
./build/cmake/rocketperf.exe cycle adiabatic cases/vehicles/zq3_y1_stage1.ini --text
./build/cmake/rocketperf.exe study propellants --case cases/research/propellant_comparison.ini --text
```

压力输入为 Pa（绝对压力）、温度为 K、面积为 m²。退出码 0 表示成功，
2 为命令用法错误，3 为文件或格式错误，4 为模型越域或求解失败。
`tests/fixtures/overexpanded.ini` 为预期拒绝算例，应退出 4。

计算采用报告所列输入和模型条件；循环工作点为研究假设，RP-1 为指定
替代物。输出不作为真实发动机实测性能或复用寿命结论。
物性与组件来源见 `数据与许可.txt` 和 `third_party/`。
"""

RUNTIME_README = """火箭动力系统性能计算程序（Windows x64）

1. 控制台版：进入“控制台版”，双击 rocketperf-run.bat，按中文菜单操作。
   菜单 8 可选择五个循环研究情景。也可在 PowerShell 中运行
   ./rocketperf.exe cases 或 ./rocketperf.exe interactive。
2. 图形界面版：进入“图形界面版”，双击 rocketperf-gui.exe。
   需要 Microsoft Edge WebView2 Runtime；若系统缺少该组件，可先使用
   控制台版，或安装微软官方 WebView2 Runtime 后再启动图形界面。
3. 请先完整解压，保留各程序旁的 cases 目录。运行不需要 Python、
   编译器、CEA 或联网计算。
4. 算例文件的压力为 Pa（绝对压力），温度为 K，面积为 m²，混合比为质量比。
   交互菜单和图形界面中的 MPa、kPa 等单位以输入标签为准。
   计算失败时请检查输入与提示，不能将失败点解释为零性能。
5. 程序输出适用于报告所列的研究输入和模型条件。循环工作点为研究
   假设，RP-1 为指定替代物，不代表真实发动机实测性能和寿命。
"""

LICENSE_TEXT = """数据与第三方组件

NASA9 热化学系数及指定反应物常量来自 NASA CEA v3.3.4。
CH4/O2 单相液体参考表来自 CoolProp 7.1.0 HEOS。
图形界面窗口组件为 webview 0.12.0，使用 WebView2 SDK 头文件。
C 计算程序使用固化数据，不在运行时调用上述参考求解器。

CEA 的 Apache-2.0 LICENSE/NOTICE、CoolProp 的 MIT 许可，以及界面
组件的 MIT/BSD 许可均随包保留。项目自有代码供本次课程作业接收，
尚未另行授予公开再分发许可。
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def checked_run(args: list[str], cwd: Path, log: Path, expected: int = 0) -> str:
    run = subprocess.run(args, cwd=cwd, capture_output=True, encoding="utf-8",
                         errors="strict", timeout=240)
    write(log.with_suffix(".stdout.txt"), run.stdout)
    write(log.with_suffix(".stderr.txt"), run.stderr)
    if run.returncode != expected:
        raise ValueError(f"Submission check failed: {log.name}, exit {run.returncode}")
    return run.stdout


def create(delivery: Path, ppt: Path, destination: Path = DEST, archive: Path = ARCHIVE,
           report: Path | None = None, report_pages: int = 20) -> None:
    report = report or ROOT / "deliverables/report_typst_v1/report-final.pdf"
    include_animation = report.name == "report-final.pdf"
    if not destination.resolve().is_relative_to((ROOT / "deliverables").resolve()):
        raise ValueError("Submission directory belongs under deliverables/")
    if archive.parent.resolve() != (ROOT / "deliverables").resolve() or archive.suffix != ".zip":
        raise ValueError("Submission archive belongs directly under deliverables/")
    if report_pages < 1 or not report.is_file():
        raise ValueError("A compiled report and its verified page count are required")
    verify(delivery)
    upstream = read_json(delivery / "delivery-manifest.json")
    if git(ROOT, "status", "--porcelain", check=True).stdout.strip():
        raise ValueError("Commit reviewed source and tooling before assembly")
    if upstream["source_head"] != git(ROOT, "rev-parse", "HEAD", check=True).stdout.strip():
        raise ValueError("Delivery and current source commit differ")
    if archive.exists() or any((destination / name).exists() for name in FOLDERS):
        raise FileExistsError("Submission already exists; choose a new dated version")
    proof = ROOT / "build" / ("submission-checks-20261020" if destination == DEST else destination.name + "-checks")
    if proof.exists():
        raise FileExistsError("Submission check directory already exists")
    proof.mkdir(parents=True)
    source = destination / FOLDERS[0]
    cli = destination / FOLDERS[1] / "控制台版"
    gui = destination / FOLDERS[1] / "图形界面版"
    with zipfile.ZipFile(delivery / "rocketperf-c-source.zip") as z:
        for name in z.namelist():
            if name.startswith(("src/", "include/", "tests/", "cases/", "third_party/")) or name in {"CMakeLists.txt", "project/modules.json", "rocketperf-run.bat"}:
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
    for folder in ("third_party/webview", "third_party/webview2"):
        for item in (ROOT / folder).rglob("*"):
            if item.is_file():
                copy_file(item, source / item.relative_to(ROOT))
    for name in ("tools/gui_build.py", "tools/gui_bridge_stdio.c", "tests/test_gui.py", "tests/test_gui_frontend.mjs"):
        copy_file(ROOT / name, source / name)
    write(source / "README.md", SOURCE_README)
    write(source / "数据与许可.txt", LICENSE_TEXT)
    with zipfile.ZipFile(delivery / "rocketperf-windows-x64.zip") as z:
        for name in z.namelist():
            if name == "rocketperf.exe" or name == "rocketperf-run.bat" or name.startswith(("cases/", "third_party/", "tests/fixtures/")):
                target = cli / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
    write(cli / "使用说明.txt", RUNTIME_README.split("1. 控制台版：", 1)[0] +
          "双击 rocketperf-run.bat 进入中文菜单；菜单 8 为循环研究情景。\n" +
          "请保留 cases 目录。详细说明见上一级的“使用说明.txt”。\n")
    write(cli / "数据与许可.txt", LICENSE_TEXT)
    # Build the exact submitted source tree in a separate writable directory.
    isolated = proof / "source"
    shutil.copytree(source, isolated)
    cmake = str((ROOT / "build/tooling/cmake/data/bin/cmake.exe").resolve(strict=True))
    ninja = str((ROOT / "build/tooling/bin/ninja.exe").resolve(strict=True))
    compiler = read_json(delivery / "verification/build-manifest.json")["compiler"]
    checked_run([cmake, "-S", ".", "-B", "build/cmake", "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_C_COMPILER=" + compiler, "-DCMAKE_MAKE_PROGRAM=" + ninja, "-DBUILD_TESTING=ON", "-DROCKETPERF_ENABLE_PYTHON_TESTS=OFF"], isolated, proof / "configure")
    checked_run([cmake, "--build", "build/cmake"], isolated, proof / "compile")
    ctest = str(Path(cmake).with_name("ctest.exe"))
    tests = checked_run([ctest, "--test-dir", "build/cmake", "--output-on-failure"], isolated, proof / "ctest")
    if "100% tests passed, 0 tests failed out of 5" not in tests:
        raise ValueError("Expected five executed C tests")
    checked_run([sys.executable, "tools/gui_build.py", "--dist"], isolated, proof / "gui-build")
    checked_run([sys.executable, "tests/test_gui.py", "--bridge", str(isolated / "build/gui/gui_bridge_stdio.exe"), "--cli", str(cli / "rocketperf.exe")], isolated, proof / "gui-tests")
    node = shutil.which("node")
    if node is None:
        raise ValueError("Node.js is required for the frontend delivery check")
    checked_run([node, "tests/test_gui_frontend.mjs", "--cli", str(cli / "rocketperf.exe")], isolated, proof / "frontend-tests")
    shutil.copytree(isolated / "build/gui/dist/RocketPerf-GUI", gui)
    # The GUI also embeds core data, so ship their notices alongside UI notices.
    shutil.copytree(cli / "third_party", gui / "third_party")
    write(gui / "数据与许可.txt", LICENSE_TEXT)
    write(destination / FOLDERS[1] / "使用说明.txt", RUNTIME_README)
    exe = cli / "rocketperf.exe"
    for label, args, expected in (
        ("success", ["cycle", "adiabatic", "cases/vehicles/zq3_y1_stage1.ini", "--text"], 0),
        ("rejection", ["run", "tests/fixtures/overexpanded.ini"], 4),
    ):
        checked_run([str(exe), *args], cli, proof / label, expected)
    copy_file(ppt, destination / FOLDERS[2] / "第五组_两型火箭动力系统性能研究.pptx")
    copy_file(report, destination / FOLDERS[3] / "第五组_两型火箭动力系统性能研究报告.pdf")
    if include_animation:
        copy_file(ROOT / "deliverables/report_typst_v1/figures/architecture-report.html", destination / FOLDERS[3] / "figures/architecture-report.html")
    appendix = "，附报告所引用的架构动画" if include_animation else ""
    write(destination / "提交说明.txt", "火箭发动机原理 第一次大作业\n第五组\n\n题目：两型运载火箭动力系统性能研究\n组员：崔笑睿、谢宝钦、李星辰、宋俊辉、何明轩、纪博闻\n\n01_程序源代码：C17计算核心、命令行、图形界面及编译说明。\n02_程序发布版：Windows x64控制台版与图形界面版。\n03_展示PPT：17页演示稿。\n04_作业报告：" + str(report_pages) + "页PDF" + appendix + "。\n\n请先完整解压。程序启动方法见02_程序发布版/使用说明.txt。\n")
    files = {p.relative_to(destination).as_posix(): digest(p) for name in (*FOLDERS, "提交说明.txt") for p in ([destination / name] if (destination / name).is_file() else sorted((destination / name).rglob("*"))) if p.is_file()}
    record = {"schema_version": 1, "status": "PASS", "source_commit": upstream["source_head"],
              "report_pages": report_pages, "slides": 17, "source_c_tests": 5,
              "cli_demonstrations_per_build": len(upstream["runtime_demonstrations"]),
              "gui_source_build": "PASS", "gui_bridge_tests": "PASS", "gui_frontend_checks": "PASS", "gui_native_window_visual_check": "pending",
              "files": files}
    write(destination / "manifest.json", json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    write(destination / "SHA256SUMS.txt", "\n".join(f"{v}  {k}" for k, v in sorted(files.items())) + "\n")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in (*files, "SHA256SUMS.txt"):
            z.write(destination / name, "第五组_第一次大作业/" + name)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("Submission ZIP CRC failure")
        for name, expected in files.items():
            if hashlib.sha256(z.read("第五组_第一次大作业/" + name)).hexdigest() != expected:
                raise ValueError("Submission ZIP file mismatch")
    record["archive"] = {"path": archive.name, "sha256": digest(archive), "bytes": archive.stat().st_size}
    write(destination / "manifest.json", json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "files": len(files), "archive": record["archive"]}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery", required=True, type=Path)
    parser.add_argument("--ppt", required=True, type=Path)
    parser.add_argument("--destination", type=Path, default=DEST)
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--report-pages", type=int, default=20)
    args = parser.parse_args()
    create(args.delivery.resolve(strict=True), args.ppt.resolve(strict=True),
           args.destination.resolve(), args.archive.resolve(),
           args.report.resolve(strict=True) if args.report else None, args.report_pages)
