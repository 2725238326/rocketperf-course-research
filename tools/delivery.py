"""Create reviewed C-source and Windows archives from one clean tested Git commit."""
from __future__ import annotations

import argparse
import hashlib
import math
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
    ("pair", ["study", "propellants", "--case", "cases/research/propellant_comparison.ini"], 0),
    ("rp1", ["combustion", "frozen-rp1", "cea-v3.3.4-rp1-o2l-assigned-v1", "liquid", "RP-1", "O2(L)",
             "10000000", "2.6", "298.15", "90.170", "10", "0", "0.01"], 0),
    ("rejection", ["run", "tests/fixtures/overexpanded.ini"], 4),
]
CURRENT_DEMO_ARGS = DEMO_ARGS + [
    ("ambient", ["run", "cases/benchmarks/air_mach2_ambient.ini"], 0),
    ("grid", ["study", "area-ratio-ambient", "cases/research/s1_area_ratio_ambient.ini"], 0),
    ("regime", ["nozzle", "regime", "cases/research/s3_sealevel_regime.ini"], 0),
    ("regime-text", ["nozzle", "regime", "cases/research/s3_sealevel_regime.ini", "--text"], 0),
    ("cases", ["cases"], 0),
    ("interactive", ["interactive"], 0),
]
VEHICLE_CASES = ("zq3_y1_stage1", "zq3_y1_stage2", "cz10b_first_stage1",
                 "cz10b_first_stage2", "cz10b_first_stage2_orsc")
VEHICLE_DEMO_ARGS = [("vehicle-" + name, ["cycle", "adiabatic", "cases/vehicles/" + name + ".ini"], 0)
                     for name in VEHICLE_CASES]
FINAL_DEMO_ARGS = CURRENT_DEMO_ARGS + VEHICLE_DEMO_ARGS + [("launcher", ["rocketperf-run.bat"], 0)]
INTERACTIVE_INPUT = "\n".join(["1", "1", "", "", "", "", "", "", "40", "101.325", "", "0"]) + "\n"
LAUNCHER_INPUT = "\n".join(value for index in range(1, 6) for value in ("8", str(index))) + "\n0\n"
ADVERTISED_CASES = {"cases/" + path for path in (
    "benchmarks/air_mach2_vacuum.ini", "benchmarks/air_mach2_ambient.ini",
    "benchmarks/prescribed_cycle.ini", "research/propellant_comparison.ini",
    "research/s1_area_ratio_ambient.ini", "research/s3_sealevel_regime.ini")}
FINAL_ADVERTISED_CASES = ADVERTISED_CASES | {"cases/vehicles/" + name + ".ini" for name in VEHICLE_CASES}


def demo_specs(version):
    if version not in {1, 2, 3}:
        raise ValueError("Unsupported delivery version")
    return {1: DEMO_ARGS, 2: CURRENT_DEMO_ARGS, 3: FINAL_DEMO_ARGS}[version]


def launcher_bytes():
    """Keep paths relative to the package and let the C CLI own its menu/UTF-8."""
    return ("@echo off\r\nsetlocal\r\npushd \"%~dp0\"\r\n"
            "if errorlevel 1 exit /b 3\r\n"
            "if not exist \"rocketperf.exe\" (\r\n"
            "  echo [ERROR] rocketperf.exe is missing. Extract the complete ZIP first.\r\n"
            "  popd\r\n  pause\r\n  exit /b 3\r\n)\r\n"
            "\"rocketperf.exe\" interactive\r\nset \"CODE=%errorlevel%\"\r\npopd\r\n"
            "if not \"%CODE%\"==\"0\" (\r\n"
            "  echo [ERROR] rocketperf exited with code %CODE%.\r\n  pause\r\n)\r\n"
            "exit /b %CODE%\r\n").encode("ascii")


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
    for path in ('docs/propellant-case-format.md','docs/coding-style.md','cases/research/propellant_comparison.ini'):
        if git(root,'cat-file','-e',head+':'+path).returncode == 0:
            files[path] = read_commit(root,head,path)
    if git(root, 'cat-file', '-e', head+':docs/propellant-method-comparison.md').returncode == 0:
        for path in ('docs/propellant-method-comparison.md', 'docs/propellant-comparison.svg'):
            files[path] = read_commit(root, head, path)
    for name in ("assignment", "business", "components", "workflow"):
        files["docs/architecture/" + name + ".svg"] = diagram(read_commit(root, head, "docs/architecture/" + name + ".svg"))
    for name, original in LICENSES.items():
        files[name] = read_commit(root, head, original)
    for name in ("air_mach2_vacuum", "air_mach2_ambient", "prescribed_cycle"):
        relative = "cases/benchmarks/" + name + ".ini"
        files[relative] = read_commit(root, head, relative)
    files["tests/fixtures/overexpanded.ini"] = read_commit(root, head, "tests/fixtures/overexpanded.ini")
    for name in ("s1_area_ratio_ambient", "s3_sealevel_regime"):
        relative = "cases/research/" + name + ".ini"
        files[relative] = read_commit(root, head, relative)
    for name in VEHICLE_CASES:
        relative = "cases/vehicles/" + name + ".ini"
        files[relative] = read_commit(root, head, relative)
    files["rocketperf-run.bat"] = launcher_bytes()
    files["docs/vehicle-cycle-cases.md"] = (
        "# 两型一二级循环研究算例\n\n固定源码提交：" + head + "\n\n"
        "完整解压后双击 `rocketperf-run.bat`，选择8，再选择1–5。命令行使用 "
        "`rocketperf.exe cycle adiabatic cases/vehicles/NAME.ini --text`；去掉 `--text`输出JSON。\n\n"
        "| 菜单 | NAME | 拓扑/入口与证据角色 |\n|---|---|---|\n"
        "| 1 | zq3_y1_stage1 | 朱雀三号遥一一级背景；甲烷液态表，开式家族研究情景 |\n"
        "| 2 | zq3_y1_stage2 | 朱雀三号遥一二级背景；甲烷液态表，开式；外排不模拟延伸段混合 |\n"
        "| 3 | cz10b_first_stage1 | 长十乙一级背景；RP-1指定替代物，全氧化剂富氧补燃；仅家族证据 |\n"
        "| 4 | cz10b_first_stage2 | 长十乙二级背景；甲烷开式待判情景 |\n"
        "| 5 | cz10b_first_stage2_orsc | 同一二级背景；甲烷补燃待判情景 |\n\n"
        "模型 `adiabatic_single_shaft_cycle_v1`以Q=0、入口/回流焓和元素库存求HP温度。"
        "开式给定涡轮出口压力、求支路流量；补燃全部氧化剂进预燃室，按轴功求涡轮出口压力。"
        "低于回流压力要求或超出求解域明确拒绝。\n\n"
        "所有输入工作点和100 kg/s流量均为研究假设，推力随本例流量定尺寸；不是具名发动机性能卡。"
        "RP-1不是国产煤油批次；长十乙一级具体后缀及二级循环仍待核。"
        "九种理想气相HP限1000–6000 K，恒密度泵、冻结涡轮/喷管，不含冷却、泵图谱、凝聚相、起动、寿命或实验标定。"
        "质量/轴功/能量残差只能支持模型内部检查。\n\n"
        "完整原文、参考卡和接收审阅维护于原工作仓库，本轻量包没有附带全部资料。"
        "同学旧 `staged_thermal_cycle_v1`给定温度、倒算热量和甲烷代理的YF例不是本接口输入。\n"
    ).encode("utf-8")
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
               "./rocketperf.exe study propellants --case cases/research/propellant_comparison.ini\n"
               "./rocketperf.exe nozzle regime cases/research/s3_sealevel_regime.ini --text\n"
               "./rocketperf.exe cases\n./rocketperf.exe interactive\n"
               "./rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage1.ini --text\n"
               "./rocketperf.exe combustion frozen-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 'O2(L)' 10000000 2.6 298.15 90.170 10 0 0.01\n"
               "./rocketperf.exe run tests/fixtures/overexpanded.ini\n$LASTEXITCODE\n")
    return ("# Rocketperf " + ("纯C源码包" if kind == "c-source" else "Windows x64运行包") +
            "\n\n固定Git提交：" + head + "\n\n"
            "项目详细解读：[docs/project-guide.md](docs/project-guide.md)。数据许可见DATA-SOURCES.md和third_party。\n\n"
            "源码构建需要Windows GCC/CMake/Ninja；exe运行只需Windows系统库。没有Python/Fortran生产依赖。\n\n"
            "Windows运行包完整解压后，双击 `rocketperf-run.bat` 进入C内置菜单；选择8，再选1–5运行两型一二级研究情景。"
            "全部工作点是假设，RP-1为指定替代物，长十乙二级循环仍待判。启动器先定位包目录，不要求中文代码页。\n\n"
            "模型及算例说明见 `docs/vehicle-cycle-cases.md`；完整证据保留于原工作仓库。"
            "源码包构建后将 `build/cmake/rocketperf.exe`复制到包根目录也可使用启动器。\n\n"
            "```powershell\n" + command + "```\n\n"
            "拒绝算例退出4、stdout为空；成功输出JSON。阶段方法结果不可贴真实发动机性能标签。\n\n"
            "完整研究资料与维护记录见私有仓库。PACKAGE.json核对逐文件SHA256，Release外部SHA256SUMS.txt核对ZIP来源。\n").encode("utf-8")


def check_regime(report, input_text=None):
    """Recompute algebraic relations, including inverse area references, without C."""
    from pipeline import CORE_KEYS, RESULT_KEYS, check_relation, ideal_log_area, snapshot_values
    if input_text is None:
        input_text = (ROOT / "cases/research/s3_sealevel_regime.ini").read_text(encoding="utf-8")
    values = snapshot_values(input_text)
    expected_inputs = {key: float(values[key]) for key in CORE_KEYS}
    if (report.get("model") != "ideal_constant_gamma_v1_regime_assessment_v1"
        or report.get("inputs") != expected_inputs
        or report.get("case") != dict(id=values["case_id"], kind=values["case_kind"], source_ref=values["source_ref"])
        or set(report.get("ideal_attached_results", {})) != RESULT_KEYS
        or not isinstance(report.get("limitations"), list) or not report["limitations"]):
        raise ValueError("Regime demo identity differs")
    inputs = report["inputs"]
    result = report["ideal_attached_results"]
    gamma = inputs["gamma"]
    delta = gamma - 1
    mach = result["exit_mach"]
    if any(type(x) not in {int, float} or not math.isfinite(x) or x <= 0 for x in result.values()):
        raise ValueError("Invalid ideal regime result")
    check_relation(ideal_log_area(mach, gamma), math.log(inputs["area_ratio"]), "area ratio")
    temperature = inputs["stagnation_temperature_k"] / (1 + delta * mach * mach / 2)
    pressure = inputs["stagnation_pressure_pa"] * math.exp(-gamma / delta * math.log1p(delta * mach * mach / 2))
    velocity = mach * math.sqrt(gamma * inputs["gas_constant_j_kg_k"] * temperature)
    area = inputs["throat_area_m2"] * inputs["area_ratio"]
    cstar = math.sqrt(inputs["gas_constant_j_kg_k"] * inputs["stagnation_temperature_k"] / gamma) * math.exp((gamma + 1) / (2 * delta) * math.log1p(delta / 2))
    flow = inputs["stagnation_pressure_pa"] * inputs["throat_area_m2"] / cstar
    thrust = flow * velocity + pressure * area
    expected = dict(exit_temperature_k=temperature, exit_pressure_pa=pressure, exit_velocity_m_s=velocity,
                    exit_area_m2=area, characteristic_velocity_m_s=cstar, mass_flow_kg_s=flow, thrust_n=thrust,
                    thrust_coefficient=thrust / (inputs["stagnation_pressure_pa"] * inputs["throat_area_m2"]),
                    specific_impulse_s=thrust / (flow * 9.80665))
    for key, value in expected.items():
        check_relation(result[key], value, key)
    regime = report["regime"]
    ambient = inputs["ambient_pressure_pa"]
    if regime["class"] != "separation_hint" or pressure >= .4 * ambient:
        raise ValueError("Regime demo classification differs")
    check_relation(regime["ambient_over_exit_pressure"], ambient / pressure, "pressure ratio")
    check_relation(regime["ideal_thrust_n"], thrust - ambient * area, "ambient thrust")
    check_relation(regime["separation_reference_pa"], .4 * ambient, "separation reference")
    for key, target in (("matched_area_ratio", ambient), ("separation_area_ratio", .4 * ambient)):
        reference = regime[key]
        if reference["available"] is not True or not 1 <= reference["area_ratio"] <= 1e4:
            raise ValueError("Regime demo reference availability differs")
        reference_mach = math.sqrt(2 / delta * math.expm1(delta / gamma *
                                   (math.log(inputs["stagnation_pressure_pa"]) - math.log(target))))
        check_relation(reference["area_ratio"], math.exp(ideal_log_area(reference_mach, gamma)), key)
    if "not a separation prediction" not in regime["basis"]:
        raise ValueError("Regime demo limitation differs")


def check_launcher(stdout, reports):
    """Tie each displayed menu result to its separately checked JSON result."""
    blocks = re.split(r"(?m)^  算例: ", stdout)[1:]
    if not isinstance(reports, dict) or len(blocks) != len(VEHICLE_CASES) or len(reports) != len(VEHICLE_CASES):
        raise ValueError("Launcher did not display each vehicle result once")
    for block, name in zip(blocks, VEHICLE_CASES):
        report = reports.get("vehicle-" + name)
        if not isinstance(report, dict) or block.splitlines()[0].strip() != report["case"]["id"]:
            raise ValueError("Launcher displayed a different vehicle case or order")
        balance = report["balance"]
        for label, key, unit, divisor in (
            ("回流主室流量", "returned_mass_flow_kg_per_s", "kg/s", 1),
            ("外排流量", "external_mass_flow_kg_per_s", "kg/s", 1),
            ("整机研究推力", "total_thrust_n", "kN", 1000),
            ("整机研究比冲", "engine_specific_impulse_s", "s", 1),
        ):
            matches = re.findall(r"(?m)^  " + label + r"\s+([-+\d.eE]+) " + re.escape(unit) + r"$", block)
            expected = float(format(balance[key] / divisor, '.6g'))  # C uses %.6g.
            if len(matches) != 1 or float(matches[0]) != expected:
                raise ValueError("Launcher result differs from validated JSON: " + name + " / " + label)


def check_demo(name, stdout, stderr, code, version=1, case_text=None, vehicle_reports=None):
    expected = next(item[2] for item in demo_specs(version) if item[0] == name)
    if code != expected or (code == 0 and stderr) or (code != 0 and (stdout or not stderr.startswith("out_of_domain:"))):
        raise ValueError("Delivery demonstration protocol differs: " + name)
    if code != 0:
        return
    if name in {"regime-text", "cases", "interactive", "launcher"}:
        required = {"regime-text": ("域评估", "分离"),
                    "cases": tuple(FINAL_ADVERTISED_CASES if version == 3 else ADVERTISED_CASES),
                    "interactive": ("域评估", "分离"),
                    "launcher": ("绝热研究算例", "整机研究比冲", "循环身份待核", *VEHICLE_CASES)}[name]
        if any(marker not in stdout for marker in required) or "失败 (" in stdout:
            raise ValueError("Delivery text/interactive demonstration differs: " + name)
        if name == "launcher":
            check_launcher(stdout, vehicle_reports)
        return
    def case(relative):
        return case_text if case_text is not None else (ROOT / relative).read_text(encoding="utf-8")
    report = strict_json(stdout)
    if name in {"ideal", "ambient"}:
        path = "air_mach2_vacuum" if name == "ideal" else "air_mach2_ambient"
        validate_result(report, case("cases/benchmarks/" + path + ".ini"))
    elif name == "grid":
        from pipeline import DEFAULT_RATIOS, DEFAULT_PRESSURES, validate_study
        validate_study(report, case("cases/research/s1_area_ratio_ambient.ini"),
                       DEFAULT_RATIOS, DEFAULT_PRESSURES)
    elif name == "regime":
        check_regime(report, case("cases/research/s3_sealevel_regime.ini"))
    elif name == "cycle":
        validate_cycle(report, case("cases/benchmarks/prescribed_cycle.ini"))
    elif name.startswith("vehicle-"):
        from engine_cycles import validate
        validate(report, case("cases/vehicles/" + name.removeprefix("vehicle-") + ".ini"))
    elif name == "pair":
        from propellant_comparison import LIMITS
        from adiabatic_study import typed_equal
        from pipeline import snapshot_values, check_relation
        pair_input = case("cases/research/propellant_comparison.ini")
        values = snapshot_values(pair_input)
        numeric_map = {key: key for key in ("pressure_pa", "throat_area_m2", "area_ratio", "ambient_pressure_pa")}
        numeric_map.update(methane_of="methane_oxidizer_fuel_mass_ratio", kerosene_of="kerosene_oxidizer_fuel_mass_ratio")
        inlet_map = {
            "methane": {"dataset": "methane_dataset_id", "basis": "methane_enthalpy_basis",
                        **{key: "methane_" + key for key in ("fuel_temperature_k", "oxidizer_temperature_k", "fuel_pressure_pa", "oxidizer_pressure_pa")}},
            "kerosene": {"dataset": "kerosene_dataset_id", "fuel": "kerosene_fuel_id", "oxidizer": "kerosene_oxidizer_id",
                         **{key: "kerosene_" + key for key in ("fuel_temperature_k", "oxidizer_temperature_k")}},
        }
        required = set(numeric_map.values()) | {key for mapping in inlet_map.values() for key in mapping.values()}
        required |= {"schema_version", "model", "case_id", "source_ref", "methane_phase", "kerosene_phase"}
        if (set(values) != required or values["schema_version"] != "1" or values["model"] != "propellant_fixed_geometry_v1"
            or values["methane_phase"] != "liquid" or values["kerosene_phase"] != "liquid"):
            raise ValueError("Invalid packaged pair input schema")
        expected_inputs = {key: float(values[field]) for key, field in numeric_map.items()}
        expected_inlets = {fuel: {key: float(values[field]) if key.endswith(("_k", "_pa")) else values[field]
                                  for key, field in mapping.items()} for fuel, mapping in inlet_map.items()}
        numbers = [*expected_inputs.values(), *(v for inlet in expected_inlets.values() for v in inlet.values() if isinstance(v, float))]
        if any(not math.isfinite(v) for v in numbers):
            raise ValueError("Non-finite packaged pair input")
        if set(report) != {"schema_version", "study", "case", "inputs", "inlets", "methane",
                           "kerosene", "methane_minus_kerosene", "limitations"}:
            raise ValueError("Pair demo schema differs")
        typed_equal(report["study"], "propellant_fixed_geometry_v1", "pair demo study")
        typed_equal(report["inputs"], expected_inputs, "pair demo inputs")
        typed_equal(report["inlets"], expected_inlets, "pair inlet states")
        typed_equal(report["schema_version"], 1, "pair schema")
        typed_equal(report["limitations"], LIMITS, "pair demo limitations")
        typed_equal(report["case"], {"id": values["case_id"], "source_ref": values["source_ref"]}, "pair demo case")
        for fuel in ("methane", "kerosene"):
            g = report[fuel]["geometry"]; n = report[fuel]["nozzle"]
            if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in g.values()):
                raise ValueError("Invalid pair geometry")
            check_relation(g["throat_area_m2"], expected_inputs["throat_area_m2"], "pair throat")
            check_relation(g["exit_area_m2"], g["throat_area_m2"] * expected_inputs["area_ratio"], "pair exit area")
            check_relation(g["mass_flow_kg_per_s"], expected_inputs["pressure_pa"] * g["throat_area_m2"] / n["cstar_m_per_s"], "pair mass flow")
            check_relation(g["thrust_n"], g["mass_flow_kg_per_s"] * n["effective_velocity_m_per_s"], "pair thrust")
            check_relation(g["specific_impulse_s"], g["thrust_n"] / g["mass_flow_kg_per_s"] / 9.80665, "pair Isp")
        differences = {key: report['methane']['geometry'][field] - report['kerosene']['geometry'][field]
                       for key, field in (("thrust_n", "thrust_n"), ("isp_s", "specific_impulse_s"), ("mass_flow_kg_per_s", "mass_flow_kg_per_s"))}
        differences["cstar_m_per_s"] = report['methane']['nozzle']['cstar_m_per_s'] - report['kerosene']['nozzle']['cstar_m_per_s']
        typed_equal(report["methane_minus_kerosene"], differences, "pair differences")
    elif name == "rp1":
        reference = ROOT / "results/validation/kerosene_anchor_v1/of_2_6_rocket.out"
        summary = parse_output(reference.read_bytes(), True, True, 1e-7)
        compare_report(report, dict(summary=summary), "frozen-rp1", 10, expected_inputs=rp1_inputs(2.6, 10))


def demos(binary, folder, logs, prefix, version=3):
    clean = subprocess_env()
    clean["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    results = []
    vehicle_reports = {}
    for name, arguments, code in demo_specs(version):
        stdout = logs / (prefix + "-" + name + "-stdout.json")
        stderr = logs / (prefix + "-" + name + "-stderr.txt")
        command = ([str(Path(os.environ["SystemRoot"]) / "System32/cmd.exe"), "/d", "/c",
                    str(folder / "rocketperf-run.bat")] if name == "launcher" else [str(binary), *arguments])
        run = subprocess.run(command, cwd=folder.parent if name == "launcher" else folder, env=clean,
                             input=LAUNCHER_INPUT if name == "launcher" else INTERACTIVE_INPUT if name == "interactive" else None,
                             capture_output=True, encoding="utf-8", errors="strict", timeout=30)
        atomic_text(stdout, run.stdout)
        atomic_text(stderr, run.stderr)
        case_path = next((value for value in arguments if value.endswith(".ini")), None)
        case_text = (folder / case_path).read_text(encoding="utf-8") if case_path else None
        check_demo(name, run.stdout, run.stderr, run.returncode, version, case_text, vehicle_reports)
        if name.startswith("vehicle-"):
            vehicle_reports[name] = strict_json(run.stdout)
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
    record = dict(schema_version=3, kind="windows-course-delivery", status="RUNNING", started_at=now(),
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
        shutil.copy2(croot / "build/rocketperf.exe", croot / "rocketperf.exe")
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
    if (not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] not in {1, 2, 3}
        or record.get("kind") != "windows-course-delivery" or record.get("status") != "PASS"
        or not isinstance(record.get("source_head"), str) or not re.fullmatch("[a-f0-9]{40}", record["source_head"])
        or set(record.get("archives", {})) != KINDS):
        raise ValueError("Delivery summary identity differs")
    specifications = demo_specs(record["schema_version"])
    demo_cases = {argument for _, arguments, _ in specifications for argument in arguments if argument.endswith(".ini")}
    packaged_cases = {}
    packaged_launcher = {}
    for kind, entry in record["archives"].items():
        if entry["path"] != ARCHIVES[kind]:
            raise ValueError("Delivery archive name differs")
        path = local_path(directory, entry["path"])
        if digest(path) != entry["sha256"] or type(entry["bytes"]) is not int or path.stat().st_size != entry["bytes"]:
            raise ValueError("Delivery archive hash or size differs")
        packed = inspect_zip(path, kind, record["source_head"])
        required_cases = FINAL_ADVERTISED_CASES if record["schema_version"] == 3 else ADVERTISED_CASES
        if record["schema_version"] >= 2 and not required_cases <= set(packed["files"]):
            raise ValueError("Advertised delivery cases missing")
        with zipfile.ZipFile(path) as archive:
            packaged_cases[kind] = {name: archive.read(name).decode("utf-8") for name in demo_cases}
        if record["schema_version"] == 3:
            if "rocketperf-run.bat" not in packed["files"]:
                raise ValueError("Delivery launcher is missing")
            with zipfile.ZipFile(path) as archive:
                packaged_launcher[kind] = archive.read("rocketperf-run.bat")
        if type(entry["files"]) is not int or len(packed["files"]) != entry["files"]:
            raise ValueError("Delivery archive file count differs")
        if kind == "windows-x64" and packed["files"]["rocketperf.exe"] != record["binary_sha256"]:
            raise ValueError("Delivery binary identity differs")
    if packaged_cases["c-source"] != packaged_cases["windows-x64"] or (record["schema_version"] == 3 and
                                            packaged_launcher["c-source"] != packaged_launcher["windows-x64"]):
        raise ValueError("Source/runtime input or launcher bytes differ")
    evidence = record["verification_files"]
    actual = {p.relative_to(directory).as_posix() for p in (directory / "verification").iterdir() if p.is_file()}
    if not isinstance(evidence, dict) or set(evidence) != actual:
        raise ValueError("Delivery verification evidence differs")
    required_logs = {'verification/quality-report.json', 'verification/build-manifest.json', 'verification/test-report.json',
                     'verification/windows-imports.txt'}
    required_logs |= {f'verification/source-{i}-{stream}.txt' for i in range(3) for stream in ('stdout', 'stderr')}
    required_logs |= {f'verification/{prefix}-{name}-{stream}.{extension}'
                     for prefix in ('source', 'runtime') for name, *_ in specifications
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
        expected = [dict(id=name, arguments=args, exit_code=code) for name, args, code in specifications]
        from adiabatic_study import typed_equal
        typed_equal(results, expected, "delivery demonstrations")
        vehicle_reports = {}
        for item in results:
            name = prefix + "-" + item["id"]
            stdout = (directory / "verification" / (name + "-stdout.json")).read_text(encoding="utf-8")
            case_path = next((value for value in item["arguments"] if value.endswith(".ini")), None)
            case_text = packaged_cases["c-source" if prefix == "source" else "windows-x64"][case_path] if case_path else None
            check_demo(item["id"], stdout,
                       (directory / "verification" / (name + "-stderr.txt")).read_text(encoding="utf-8"),
                       item["exit_code"], record["schema_version"], case_text, vehicle_reports)
            if item["id"].startswith("vehicle-"):
                vehicle_reports[item["id"]] = strict_json(stdout)
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
