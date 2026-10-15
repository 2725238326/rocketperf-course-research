"""Build the desktop GUI rocketperf-gui.exe (WebView2 host + C bridge + C core).

Development tool only; the program it produces runs without Python. C sources
use the project's strict flags; the vendored webview C++ shell is compiled once
and cached by content hash. Output: build/gui/ with a manifest of inputs,
outputs and DLL imports (Windows system DLLs only, else the build fails).

    python tools/gui_build.py               # bridge harness + GUI exe
    python tools/gui_build.py --bridge-only # stdio harness for tests/preview
    python tools/gui_build.py --dist        # also build/gui/dist/RocketPerf-GUI (portable folder)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "gui"
FLAGS = ["-std=c17", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-Wconversion", "-Wshadow",
         "-Wstrict-prototypes", "-Wmissing-prototypes", "-fno-common", "-Iinclude", "-Isrc/adapters", "-Isrc/gui"]
WEBVIEW = ["third_party/webview/src/webview.cc", "third_party/webview/include/webview/webview.h",
           "third_party/webview/compat/EventToken.h", "third_party/webview2/include/WebView2.h",
           "third_party/webview2/include/WebView2EnvironmentOptions.h"]
LIBS = ["-ladvapi32", "-lole32", "-lshell32", "-lshlwapi", "-luser32", "-lversion"]
SYSTEM_DLLS = {"kernel32.dll", "user32.dll", "advapi32.dll", "ole32.dll", "shell32.dll", "shlwapi.dll", "version.dll",
               "msvcrt.dll", "ucrtbase.dll"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def modules() -> dict:
    return {m["id"]: m for m in json.loads((ROOT / "project/modules.json").read_text(encoding="utf-8"))["modules"]}


def sources() -> tuple[list[str], list[str]]:
    reg = modules()
    core = [s for mid in ("core", "nozzle", "thermo", "cycle", "adapters") for s in reg[mid]["sources"]]
    gui = reg["gui"]["sources"] if "gui" in reg else ["src/gui/gui_json.c", "src/gui/gui_bridge.c", "src/gui/gui_main.c"]
    return core, gui


def run(cmd: list[str], log: list[str]) -> None:
    log.append(" ".join(cmd))
    done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.stdout.strip():
        log.append(done.stdout)
    if done.stderr.strip():
        log.append(done.stderr)
    if done.returncode != 0:
        (OUT / "build.log").write_text("\n".join(log), encoding="utf-8")
        sys.stderr.write(done.stderr[-4000:])
        raise SystemExit(f"FAIL: {cmd[0]} exited {done.returncode}; see build/gui/build.log")


def imports(exe: Path) -> list[str]:
    text = subprocess.run(["objdump", "-p", str(exe)], capture_output=True, text=True, check=True).stdout
    return re.findall(r"DLL Name:\s+(\S+)", text)


def build(bridge_only: bool) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    log: list[str] = []
    core, gui = sources()
    bridge_src = [s for s in gui if not s.endswith("gui_main.c")]
    harness = OUT / "gui_bridge_stdio.exe"
    run(["gcc", *FLAGS, *core, *bridge_src, "tools/gui_bridge_stdio.c", "-lm", "-o", str(harness)], log)
    outputs = {"bridge": harness}
    if not bridge_only:
        key = hashlib.sha256("".join(sha(ROOT / p) for p in WEBVIEW).encode()).hexdigest()[:16]
        webview_obj = OUT / f"webview-{key}.o"
        if not webview_obj.is_file():
            run(["g++", "-c", "-std=c++14", "-O2", "-DWEBVIEW_STATIC", "-Ithird_party/webview/include",
                 "-Ithird_party/webview/include/webview", "-Ithird_party/webview2/include", "-Ithird_party/webview/compat",
                 "third_party/webview/src/webview.cc", "-o", str(webview_obj)], log)
        res = OUT / "gui-res.o"
        run(["windres", "--input-format=rc", "-O", "coff", "-I", "src/gui", "src/gui/gui.rc", "-o", str(res)], log)
        objs = []
        for src in [*core, *gui]:
            obj = OUT / "obj" / (src.replace("/", "_").removesuffix(".c") + ".o")
            obj.parent.mkdir(exist_ok=True)
            extra = ["-DWEBVIEW_STATIC", "-isystem", "third_party/webview/include"] if src.endswith("gui_main.c") else []
            run(["gcc", *FLAGS, *extra, "-c", src, "-o", str(obj)], log)
            objs.append(str(obj))
        exe = OUT / "rocketperf-gui.exe"
        run(["g++", *objs, str(webview_obj), str(res), "-o", str(exe), "-static", "-mwindows", "-s", *LIBS], log)
        dlls = imports(exe)
        foreign = [d for d in dlls if d.lower() not in SYSTEM_DLLS and not d.lower().startswith("api-ms-win-")]
        if foreign:
            raise SystemExit(f"FAIL: non-system DLL imports {foreign}")
        outputs["gui"] = exe
    (OUT / "build.log").write_text("\n".join(log), encoding="utf-8")
    web = sorted((ROOT / "src/gui/web").glob("*"))
    manifest = {
        "schema_version": 1, "kind": "gui-build", "status": "PASS",
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "compiler": shutil.which("gcc"),
        "inputs": [{"path": p, "sha256": sha(ROOT / p)} for p in [*core, *gui, "tools/gui_bridge_stdio.c", "src/gui/gui.rc",
                   *[w.relative_to(ROOT).as_posix() for w in web], *WEBVIEW]],
        "outputs": {k: {"path": v.relative_to(ROOT).as_posix(), "sha256": sha(v), "bytes": v.stat().st_size} for k, v in outputs.items()},
        "dll_imports": imports(outputs["gui"]) if "gui" in outputs else None,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def dist(manifest: dict) -> Path:
    """Portable folder: the exe, bundled vehicle cases it loads, third-party notices."""
    folder = OUT / "dist" / "RocketPerf-GUI"
    if folder.exists():
        shutil.rmtree(folder)
    (folder / "cases" / "vehicles").mkdir(parents=True)
    (folder / "licenses").mkdir()
    shutil.copy2(ROOT / manifest["outputs"]["gui"]["path"], folder / "rocketperf-gui.exe")
    for ini in sorted((ROOT / "cases/vehicles").glob("*.ini")):
        shutil.copy2(ini, folder / "cases/vehicles" / ini.name)
    shutil.copy2(ROOT / "third_party/webview/LICENSE", folder / "licenses/webview-MIT.txt")
    shutil.copy2(ROOT / "third_party/webview2/LICENSE.txt", folder / "licenses/WebView2-SDK-BSD.txt")
    (folder / "README.txt").write_text(
        "RocketPerf 液体火箭发动机性能计算（图形界面版）\r\n\r\n"
        "双击 rocketperf-gui.exe 运行。需要 Microsoft Edge WebView2 Runtime（Windows 10/11 通常已自带）。\r\n"
        "cases/vehicles 为循环模块读取的研究算例，请与程序放在同一目录。\r\n"
        "全部计算由程序内置 C17 核心完成；licenses/ 为第三方界面组件许可。\r\n", encoding="utf-8")
    return folder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-only", action="store_true")
    parser.add_argument("--dist", action="store_true")
    args = parser.parse_args()
    manifest = build(args.bridge_only)
    if args.dist and not args.bridge_only:
        print(f"PASS dist: {dist(manifest).relative_to(ROOT).as_posix()}")
    for name, out in manifest["outputs"].items():
        print(f"PASS {name}: {out['path']} ({out['bytes'] / 1024:.0f} KiB)")
    if manifest["dll_imports"]:
        print("DLL imports:", ", ".join(manifest["dll_imports"]))


if __name__ == "__main__":
    main()
