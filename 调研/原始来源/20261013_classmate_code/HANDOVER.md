# HANDOVER —— 项目交接说明

| 项目   | 内容                                                                         |
| ---- | -------------------------------------------------------------------------- |
| 交接对象 | 本项目的原始开发者                                                                  |
| 基线提交 | `27e29facf4ba12cc733a178e02c41e6ba968dc8f`（基线包见 `代码(1).zip`，2026-10-07）    |
| 交接日期 | 2026-10-12                                                                 |
| 交接原因 | 课程大作业要求"用 C 语言计算朱雀三号与长征十号乙两型火箭动力系统性能"，需要在既有程序上补一个**补燃循环**，并把发布包改造成可直接演示的形态 |

> 配套文件：同目录下的 **`HANDOVER.diff`** —— 7 个被修改文件的逐行 unified diff（467 行），建议与本文件对照阅读。
>
> 基线原件也在同目录：**`rocketperf-c-source.zip`** 与 **`rocketperf-windows-x64.zip`**（均为 2026-10-07 的原始包），可随时解压做对照。

---

## 0. 先看这三件事（TL;DR）

1. **唯一的功能性改动**：新增"**补燃（分级燃烧）循环**"闭包，模型 ID `staged_thermal_cycle_v1`，**与原来的开式燃气发生器闭包并存**。原闭包的代码路径一行未改。
2. **旧行为零变化**：旧算例的 JSON 数值逐位一致，唯一新增一个顶层键 `staged_combustion`。用旧基准算例实测对照：`296.254 kN / 302.0952 s`，与基线完全一致。
3. **发布包被改造为可交付形态**：新增两级菜单启动器、两个型号算例、参数来源数据、逐选项说明文档。**没有删除任何原有文件**。

---

## 1. 三分钟验证（照抄即可）

工具链要求与基线 README 相同（Windows + GCC + CMake + Ninja）。本次实际使用：

| 工具    | 版本                                                  |
| ----- | --------------------------------------------------- |
| GCC   | MinGW-W64 x86_64-ucrt-posix-seh **16.2.0**（WinLibs） |
| CMake | **4.4.4**                                           |
| Ninja | **1.13.2**                                          |

```powershell
cmake -S . -B build/cmake -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DROCKETPERF_ENABLE_PYTHON_TESTS=OFF
cmake --build build/cmake
ctest --test-dir build/cmake --output-on-failure
```

**预期结果（已实测）**：

- 构建 **46 个目标全部成功**。注意 `CMakeLists.txt` 第 82~83 行带 **`-Werror`**（`-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -fno-common`）——**构建通过即等于 0 警告**，不需要另外检查。
- `ctest` **5/5 通过**：

| 测试         | 当前检查项数                     | 基线检查项数  | 说明                                  |
| ---------- | -------------------------- | ------- | ----------------------------------- |
| core       | 207 checks, 0 failures     | 207     | 未改动                                 |
| thermo     | 8978 checks, 0 failures    | 8978    | 未改动                                 |
| combustion | 3894 checks, 0 failures    | 3894    | 未改动                                 |
| **cycle**  | **394 checks, 0 failures** | **353** | **本次 +41 项**（`test_staged()` 及辅助函数） |
| adapters   | 29 checks, 0 failures      | 29      | 未改动                                 |

> 上表的"基线"一列是我把基线包单独构建后实测得到的（基线 `ctest` 同样是 5/5 通过），可与当前结果逐项对照。

再跑两个新算例（在发布包目录下）：

```powershell
rocketperf.exe cycle prescribed cases\active-cases\zhuque3-tq12a-open.ini
rocketperf.exe cycle prescribed cases\active-cases\cz10b-yf100k-staged.ini
```

预期 `exit=0`，关键数字：

|                               | 朱雀三号 一级                       | 长征十号乙 一级                      |
| ----------------------------- | ----------------------------- | ----------------------------- |
| `model`                       | `prescribed_thermal_cycle_v1` | **`staged_thermal_cycle_v1`** |
| `staged_combustion`           | `false`                       | **`true`**                    |
| 支路流量                          | 2.8624 kg/s（**外排**）           | 200.649 kg/s（**回流**）          |
| `external_mass_flow_kg_per_s` | 2.8624                        | **0**                         |
| `branch_nozzle`               | 有（推力 5.955 kN）                | **`null`**                    |
| 总推力                           | 807.006 kN                    | 1396.050 kN                   |
| 整机比冲                          | 352.820 s                     | 355.894 s                     |
| 守恒残差（质量/轴功/能量）                | −2.5e−17 / 0 / −2.4e−16       | 0 / 0 / −8.3e−17              |

---

## 2. 改动清单（相对基线 `27e29fa`）

### 2.1 源码包 `rocketperf-c-source`：8 个文件（1 新增 / 7 修改）+ 清单重建

| 文件                                 | 变更     | 行数      | 要点                                                                                    |
| ---------------------------------- | ------ | ------- | ------------------------------------------------------------------------------------- |
| `src/cycle/staged.c`               | **新增** | +170    | 补燃闭包的全部实现                                                                             |
| `include/rocketperf/cycle.h`       | 修改     | 129→145 | 新增 `RP_STAGED_CYCLE_MODEL` 宏与 `rp_cycle_solve_staged()` 声明；更新注释（`return_*` 不再是保留字段）   |
| `include/rocketperf/cycle_study.h` | 修改     | 56→61   | 新增 `rp_cycle_scan_staged()` 声明                                                        |
| `src/cycle/study.c`                | 修改     | 93→110  | 抽出 `RpCycleSolver` 函数指针 + 内部 `scan()`，两个既有/新增包装共用                                     |
| `src/adapters/cycle_case.h`        | 修改     | 26→27   | `RpCycleCase` 增加 `int staged_combustion;`                                             |
| `src/adapters/cycle_case.c`        | 修改     | 256→306 | 可选布尔字段解析；闭包选择；报告新增 `staged_combustion`；按闭包切换 `model`/`boundary`/`limitations`/`study` |
| `tests/test_cycle.c`               | 修改     | 327→436 | 新增 `staged_benchmark()` / `check_staged()` / `test_staged()`                          |
| `project/modules.json`             | 修改     | 1 行     | cycle 模块 `sources` 加入 `src/cycle/staged.c`，`contract` 文案同步                            |
| `PACKAGE.json`                     | 重建     | —       | 逐文件 SHA256 更新 + 新增 `modifications` 字段（原 `kind`/`schema_version`/`source_head` 保留）     |

### 2.2 发布包 `rocketperf-windows-x64`：51 → 71 个文件

**新增 20 个**（另有 2 个运行产物已清理）：

| 路径                                                                     | 说明                 |
| ---------------------------------------------------------------------- | ------------------ |
| `rocketperf-run.bat`                                                   | 两级菜单启动器（GBK 编码）    |
| `cases/active-cases/zhuque3-tq12a-open.ini`                            | 朱雀三号一级算例（开式）       |
| `cases/active-cases/cz10b-yf100k-staged.ini`                           | 长征十号乙一级算例（补燃）      |
| `cases/active-cases/README.txt`                                        | 算例文件夹使用说明          |
| `model-data/zhuque3-tq12a.md`                                          | 朱雀三号参数口径、来源链接、验证数据 |
| `model-data/cz10b-yf100k.md`                                           | 长征十号乙同上            |
| `model-data/README.txt`                                                | 数据文件夹索引            |
| `results/README.md`                                                    | 结果与选项说明总览          |
| `results/选项-*.md`（8 个）                                                 | 每个菜单项的输出说明         |
| `verification/runtime-zhuque3-tq12a-open-stdout.json` / `-stderr.txt`  | 朱雀三号的运行留证          |
| `verification/runtime-cz10b-yf100k-staged-stdout.json` / `-stderr.txt` | 长征十号乙的运行留证         |

**修改 3 个**：

| 路径                                       | 说明                                                 |
| ---------------------------------------- | -------------------------------------------------- |
| `rocketperf.exe`                         | 重新构建（182 995 → **206 301** 字节），含补燃模块               |
| `PACKAGE.json`                           | 重建 + `modifications` / `excluded_from_manifest` 字段 |
| `verification/runtime-cycle-stdout.json` | 新增 `staged_combustion` 键；**所有数值实测未变**              |

**删除 0 个。**

### 2.3 明确"一个字节都没动"的部分

以下文件经 SHA256 比对与基线**逐字节一致**（可用 `PACKAGE.json` 复核）：

- `src/cycle/prescribed.c`（160 行）、`src/cycle/components.c`（112 行）
- `src/thermo/**`、`src/nozzle/**`、`src/cli/**`、`src/core/**`
- `include/rocketperf/` 下除 `cycle.h`、`cycle_study.h` 外的全部头文件
- `cases/**`（原有两个基准算例与研究算例）、`tests/fixtures/**`、`tests/reference/**`
- 发布包的 `docs/**`、`third_party/**`、`DATA-SOURCES.md`、`README.md`、`cases/**`、`tests/**`
- 源码包的 `CMakeLists.txt`、`README.md`、`DATA-SOURCES.md`、`docs/**`、`third_party/**`

---

## 3. 设计思路

### 3.1 总原则：新增闭包，而不是修改现有闭包

`prescribed_thermal_cycle_v1` 是已经过 reference 校核的模型。任何语义改动都会：

1. 让 `tests/reference/**` 与发布包 `verification/**` 里的既有证据失效；
2. 让已经写好的报告/PPT 里的数字全部作废。

所以补燃**另起一个模型 ID、另起一个函数**，只在**用例层**（`.ini` 的布尔开关）做选择。旧路径的代码结构、字段、数值全部保留。

### 3.2 补燃闭包 `staged_thermal_cycle_v1` 的口径

**拓扑**：

```
开式：  泵 ─┬─ 主路推进剂 ─────────────────→ 主燃烧室 → 主喷管 ↘
           └─ 支路推进剂 → 燃气发生器 → 涡轮 → 支路喷管（外排）

补燃：  泵 ─┬─ 主路推进剂 ────────────────┐
           └─ 支路推进剂 → 预燃室 → 涡轮 ─┘→ 主燃烧室 → 主喷管（全流量）
                                            （无支路喷管、无外排）
```

**相对开式的三条硬性差异**（写在 `src/cycle/staged.c` 的返回值里）：

| 量                                                                    | 开式         | 补燃                                       |
| -------------------------------------------------------------------- | ---------- | ---------------------------------------- |
| `external_mass_flow_kg_per_s`                                        | = 支路流量     | **0**                                    |
| `returned_mass_flow_kg_per_s`                                        | 0          | **= 支路流量**                               |
| `main_mass_flow_kg_per_s`                                            | = 总流量 − 支路 | **= 总流量**                                |
| `branch_nozzle_active` / `branch_thrust_n` / `branch_throat_area_m2` | 正常解        | **0 / 0 / 0，`branch_nozzle` 输出为 `null`** |

**能量账**（主室入流 = 回流燃气 + 未分支推进剂）：

```
chamber_heat = ṁ_main · h_chamber
             − [ ṁ_return · h_turbine_out
               + (ṁ_f − ṁ_branch,f) · h_fuel_pump_out
               + (ṁ_o − ṁ_branch,o) · h_ox_pump_out ]
```

**新增的域规则**（只作用于补燃，开式不受影响）。`staged.c` 里一共 7 个显式拒绝分支：

| # | 触发条件                                                                   | 状态                    | 错误文本                                                                                         |
| - | ---------------------------------------------------------------------- | --------------------- | -------------------------------------------------------------------------------------------- |
| 1 | 流量 / 效率 / 管路字段非法或为负                                                    | `RP_INVALID_ARGUMENT` | `Invalid staged-cycle flow, efficiencies, routing or pump flow overrides.`                   |
| 2 | `return_fraction != 1.0`                                               | `RP_OUT_OF_DOMAIN`    | `Staged combustion requires a full turbine return (return_fraction == 1).`                   |
| 3 | 有轴功需求但涡轮比功为零                                                           | `RP_OUT_OF_DOMAIN`    | `Positive shaft load cannot be met by a zero-work turbine.`                                  |
| 4 | 所需支路流量超出 `maximum_branch_fraction`                                     | `RP_OUT_OF_DOMAIN`    | `Shaft demand exceeds the declared preburner-flow envelope.`                                 |
| 5 | 支路抽取把某一路泵流量抽空                                                          | `RP_OUT_OF_DOMAIN`    | `Preburner diversion starves a pump-feed stream.`                                            |
| 6 | 泵出口压力达不到所声明的室压 / 预燃室压力                                                 | `RP_OUT_OF_DOMAIN`    | `Pump delivery pressure cannot reach a declared chamber/preburner state.`                    |
| 7 | `turbine_outlet_pressure < chamber_pressure + return_pressure_drop_pa` | `RP_OUT_OF_DOMAIN`    | `Turbine discharge pressure cannot inject into the chamber across the declared return drop.` |

**回流管路压降 `return_pressure_drop_pa` 是声明值**——模型不做喷注器 / 歧管建模。

任何一条拒绝都**不改动输出结构体**（`test_staged()` 用 `sentinel` 字节模式逐个验证）。

**仍然沿用"声明热状态"的方法论**：`chamber_temperature_k` / `generator_temperature_k` 是**输入**而非计算结果；`chamber_heat_w` / `generator_heat_w` 是**倒算记账值**，不是经验证的燃烧热。这一点在报告 JSON 的 `limitations` 里逐条声明。

### 3.3 算例文件开关：为什么用布尔，而不是直接写 `return_fraction`

| 方案                                  | 问题                                               |
| ----------------------------------- | ------------------------------------------------ |
| 直接让用户填 `return_fraction = 1`        | 把"物理量"和"用例选择"混在一起；旧文件语义变复杂                       |
| **加一个布尔 `staged_combustion`（本次采用）** | 布尔是**用例层**的选择，由 adapter 翻译成模型的 `return_fraction` |

实现约束（都在 `cycle_case.c`）：

- 布尔**可选、缺省 false** → 基线的 `.ini` 一个字不改也能加载（向后兼容的硬要求）；
- 文件里的 `return_fraction` 必须留 `0`，写非零会明确报错：  
  `return_fraction is driven by staged_combustion; keep the case-file value at 0.`；
- 映射逻辑集中在 `select_closure()`，求解分派集中在 `solve_case()`，扫描分派写在 `rp_cycle_case_study()` 内（这三个都是 `cycle_case.c` 里的 static 函数，见 `HANDOVER.diff`）。

**JSON 输出的变化**（只有这些）：

| 字段                           | 开式                                    | 补燃                                                                                    |
| ---------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------- |
| `model`                      | `prescribed_thermal_cycle_v1`         | `staged_thermal_cycle_v1`                                                             |
| `boundary`                   | `pump_inlets_to_two_nozzle_exits_...` | `pump_inlets_through_preburner_and_turbine_return_into_main_chamber_to_main_exit_...` |
| `staged_combustion`（**新增键**） | `false`                               | `true`                                                                                |
| `limitations`                | 4 条                                   | 6 条（含"预燃室化学固定 CH4/O2""回流压降为声明值"）                                                      |
| 扫描结果的 `study`                | `prescribed_cycle_scan_v1`            | `staged_cycle_scan_v1`                                                                |

### 3.4 `study.c` 的重构：函数指针去重

原来 `rp_cycle_scan_prescribed()` 内部把求解器写死成 `rp_cycle_solve_prescribed()`。要支持补燃，最省事的做法是复制一份函数——但那样指标计算（Δ推力、Δ比冲、弹性、出口面积代价）就有两份，日后必然漂移。

本次改为：

```c
typedef RpStatus (*RpCycleSolver)(const RpCycleInput *, const RpRootOptions *,
                                   RpCycleResult *, RpError *);
static RpStatus scan(..., RpCycleSolver solver, ...);              /* 内部实现，网格与指标 100% 复用 */
RpStatus rp_cycle_scan_prescribed(...) { return scan(..., rp_cycle_solve_prescribed, ...); }  /* 签名不变 */
RpStatus rp_cycle_scan_staged(...)     { return scan(..., rp_cycle_solve_staged,     ...); }  /* 新增 */
```

**两个既有函数签名保持原样**，调用方（`cycle_case.c`）无需改动；新增的只是另一个包装。

### 3.5 过程中修正的一处边界缺陷（**请重点 review 这段**）

`cycle_case.c` 原本用 `if (field == META_COUNT + FIELD_COUNT) ... "Unknown field."` 判定"字段不存在"。加入**可选字段**后，索引空间变成三段：必填字段 / 可选开关 / 越界未知。第一次实现里我把 `FLAG_INDEX` 与 `REQUIRED_COUNT` 定义成了同一个数值，导致"可选字段缺席"被误判为未知字段，算例加载直接报 `Unknown field.`。

最终定义（即当前代码）：

| 宏                | 值                          | 含义            |
| ---------------- | -------------------------- | ------------- |
| `REQUIRED_COUNT` | `META_COUNT + FIELD_COUNT` | 必填字段个数        |
| `FLAG_INDEX`     | `REQUIRED_COUNT`           | 可选开关的索引       |
| `SEEN_COUNT`     | `REQUIRED_COUNT + 1`       | `seen[]` 数组长度 |

判定改为 `field >= SEEN_COUNT` 才报未知，`field == FLAG_INDEX` 走开关分支。这是本次**唯一一处"修缺陷"性质的改动**，其余都是纯新增。

### 3.6 质量与风格

- 遵循包内 `docs/coding-style.md`；新代码不引入动态分配、不做 I/O、错误路径不改输出（沿用项目 status 契约）；
- 项目自带 `-Werror`，构建通过 = 0 警告；
- 新增测试覆盖：补燃基础解、开式对照、流量倍增的相似性、6 条域规则拒绝、3 条参数校验、`sentinel` 输出不变性、扫描包装的基准一致性。

### 3.7 为什么还要单独做一个 `.bat` 启动器

**要解决的问题**：`rocketperf.exe` 是**命令行程序**，必须带参数才能工作。不带参数运行时，它只往 stderr 打印一行用法，然后**立刻以退出码 2 退出**——Windows 控制台窗口随进程结束而关闭，用户看到的就是"黑框一闪就没了"。这不是程序缺陷，是控制台程序的正常行为，但对"课堂上双击演示"和"交给不熟悉命令行的组员"来说等于不可用。

**做法**：在**不改动一行动 C 代码**的前提下，加一层批处理作为"最轻量的用户友好界面"（作业本身也允许发布版做成"控制台 / 带用户友好界面"等形式）。

`rocketperf-run.bat` 承担五件事：

| # | 职责 | 具体做法 |
|---|---|---|
| 1 | **拼命令** | 把 `cycle prescribed <算例路径>` 的参数顺序固化，用户不必记参数格式 |
| 2 | **留住输出** | stdout 存 `results\<算例基名>.json`、stderr 存 `results\<算例基名>.err`，同时回显——写报告时直接有文件可引用 |
| 3 | **让窗口停住** | 每个分支末尾 `pause`，从根上解决"一闪而过" |
| 4 | **组织入口** | 两级菜单：第 1 步选算例、第 2 步选计算内容；且第 2 步菜单**随算例类型切换**（型号算例只显示相关的 5 项，基准算例才显示三个自带演示） |
| 5 | **结果按算例命名** | `<算例基名>.json` / `scan_<算例基名>.json`，切换算例时互不覆盖、不混淆 |

**为什么不用别的方式**：

| 备选方案 | 为什么不采用 |
|---|---|
| 让用户直接敲命令 | 课堂演示时手敲参数容易出错；组员大多不熟命令行 |
| 改 C 代码，做"无参数即弹菜单" | 违反"核心计算程序保持纯净"的边界，会把交互与 I/O 逻辑塞进已校核的求解代码 |
| 写 GUI（Win32 / WinForms / Python） | 需要额外框架与运行时依赖，交付风险高；批处理**零依赖**，任何 Windows 都能直接跑 |
| 把菜单塞进 exe 里统一发布 | 同样要改工程结构与入口点，收益不足 |

**两个实现上的坑（务必保留现有写法）**：

1. **脚本必须存成 GBK(cp936) 编码**。批处理里有中文标签（如"完整循环计账"），若存成 UTF-8，中文 Windows 的 cmd 会按 936 解析成乱码。
2. **脚本里不要调用 `chcp`**。实测 `chcp 936` 会让"stdin 被重定向"时的 `set /p` 读不到数据（真实控制台里不受影响，但脚本就无法被自动化测试或其他批处理调用）。当前写法是"脚本以 GBK 保存 + 不调 chcp"——中文 Windows 控制台默认就是 936，中文照常显示。

**它只是入口便利层，不参与任何计算**。命令行等价写法始终可用（也写在 `cases/active-cases/README.txt` 里）：

```
rocketperf.exe cycle prescribed cases\active-cases\zhuque3-tq12a-open.ini
```

删掉这个 `.bat` 也不影响程序功能，只是回到"必须手敲参数"。

---

## 4. 接口变化清单（给调用方）

| 位置                                 | 变化                                                                                                | 兼容性            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------- | -------------- |
| `include/rocketperf/cycle.h`       | 新增宏 `RP_STAGED_CYCLE_MODEL`、函数 `rp_cycle_solve_staged()`                                          | 纯新增            |
| `include/rocketperf/cycle_study.h` | 新增函数 `rp_cycle_scan_staged()`                                                                     | 纯新增            |
| `include/rocketperf/cycle.h`       | `RpCycleInput.return_fraction` / `return_pressure_drop_pa` **语义生效**（原注释为 "Reserved: unsupported"） | 开式下仍要求 0，行为不变  |
| `src/adapters/cycle_case.h`        | `RpCycleCase` 增加字段 `int staged_combustion;`                                                       | 结构体变大（源码级兼容）   |
| 循环报告 JSON                          | 新增 `staged_combustion`；`model`/`boundary`/`limitations`/扫描 `study` 按闭包切换                          | **旧字段与数值全部不变** |
| CLI 命令与参数                          | 无变化（同一个 `cycle prescribed CASE.ini`）                                                              | 完全兼容           |
| 退出码                                | 无变化（0 成功 / 2 语法 / 3 文件格式 / 4 模型拒绝）                                                                | 完全兼容           |



---

## 5. 两条新算例的口径与结果

| | 朱雀三号（基础型/遥一）一级 | 长征十号乙（首飞）一级 |
|---|---|---|
| 发动机 | 天鹊-12A | YF-100K |
| 循环 | 燃气发生器（开式） | **高压补燃** |
| 室压 / 面积比 / 总混合比 | 10.1 MPa / 40 / 2.9 | 18.7 MPa / 35 / 2.6 |
| 预燃室 | O/F = 1.0，1800 K | O/F = 20，1200 K，涡轮 30→20 MPa |
| 总流量（标定值） | 233.24 kg/s | 400 kg/s |
| 支路流量 | 2.8624 kg/s（1.23%，外排） | 200.649 kg/s（50.16%，回流） |
| 总推力 / 整机比冲 | 807.006 kN / 352.820 s | 1396.050 kN / 355.894 s |

参数口径、来源链接与"哪些是公开值 / 继承声明 / 工程假设"的逐条标注，见发布包内：
`model-data/zhuque3-tq12a.md`、`model-data/cz10b-yf100k.md`。

---

## 6. 文档地图（说清每一份文档在哪、给谁看）

### 6.1 源码包 `代码(1)/rocketperf-c-source/`

| 路径 | 内容 | 适合谁 |
|---|---|---|
| `README.md` | 基线自带的构建说明（本次未改动） | 所有人 |
| **`PACKAGE.json`** | 逐文件 SHA256 + 本次 `modifications` 说明 | 验收 / 完整性核对 |
| `docs/project-guide.md` | 项目解读（数据口径、模型边界） | 初次接触项目 |
| `docs/coding-style.md` | 编码规范（新增代码遵循此规范） | 改动代码前 |
| `project/modules.json` | 模块登记表：职责、依赖、契约、测试 | 想知道"改这块要注意什么" |
| `docs/propellant-case-format.md` | 成对推进剂算例的字段格式 | 写新算例 |
| `docs/propellant-method-comparison.md` | 推进剂对比方法说明 | 理解 compare 口径 |
| `DATA-SOURCES.md` | 数据来源许可 | 引用数据 |
| `docs/architecture/*.svg` | 架构图（构件、流程、业务、任务） | 汇报 / 快速理解 |
| `include/rocketperf/cycle.h` | **补燃闭包的接口与域规则注释**（新增部分） | **改循环功能必读** |
| `src/cycle/staged.c` | **补燃闭包实现**（170 行，含逐段注释） | **review 重点** |
| `tests/test_cycle.c` → `test_staged()` | 补燃闭包的 109 项检查 | 验证/回归 |
| 同目录 **`../HANDOVER.diff`** | 7 个修改文件的逐行 diff | **review 起点** |

### 6.2 发布包 `代码(1)/rocketperf-windows-x64/`

| 路径 | 内容 | 适合谁 |
|---|---|---|
| `README.md` | 基线自带的发布说明（未改动） | 所有人 |
| **`rocketperf-run.bat`** | 两级菜单启动器（第 1 步选算例 → 第 2 步选计算内容）；**为什么要单独做它，见 §3.7** | **演示 / 日常使用入口** |
| `cases/active-cases/README.txt` | 两个型号算例的用法与循环开关说明 | 使用者 |
| `cases/active-cases/*.ini` | 两个型号算例本体 | 改参数 |
| `model-data/*.md` | 参数口径、来源链接、验证数据 | 报告撰写 |
| **`results/README.md`** | 结果文件命名规则、两套菜单对照、通用阅读建议 | 看结果前 |
| `results/选项-*.md`（8 份） | 每个菜单项的：命令 / 输出文件 / 字段释义 / 实测值 / 对应报告章节 | 解读输出 |
| `verification/**` | 运行留证（stdout/stderr），含新增的两型记录 | 结果核验 |
| `docs/**` | 基线文档（未改动） | 背景资料 |
| **`PACKAGE.json`** | 逐文件 SHA256；`excluded_from_manifest` 声明 `results/` 为运行产物目录 | 完整性核对 |

### 6.3 按目的找文档

| 我想…… | 看这个 |
|---|---|
| 看代码到底改了哪些行 | `代码(1)/HANDOVER.diff` |
| 理解补燃闭包怎么写的 | `src/cycle/staged.c` + `include/rocketperf/cycle.h` |
| 验证改动没破坏旧行为 | 跑 `ctest`；看 `verification/runtime-cycle-stdout.json` 对照 |
| 跑一次看看 | 双击 `rocketperf-run.bat` |
| 搞清某个输出字段什么意思 | `results/选项-*.md` |
| 核对参数的出处 | `model-data/*.md` |
| 知道模块职责与边界 | `project/modules.json` + `docs/project-guide.md` |

---

## 7. 已知限制与遗留事项（交接方认为需要后续处理）

### 7.1 模型层面（**写报告/汇报时必须声明**）

1. **补燃闭包没有真实发动机验证数据**：`chamber_heat_w` / `generator_heat_w` 是给定热状态下的倒算记账值，`limitations` 已逐条声明。
2. **循环模型的燃烧化学固定为 CH4/O2**：长征十号乙一级是**煤油**发动机，本次只能用"甲烷代理"，比冲因此偏高（355.89 s vs 公开真空比冲约 336.9 s，差约 5.6%）。同一程序用**单机煤油路**（`combustion frozen-rp1`，锁定 10 MPa / O-F 2.2–4.0）算得 331.82 s，与公开值差 1.5%。**若要修正，需要补煤油循环化学（属于 thermo 模块的工作）。**
3. **预燃室 O/F 上限 20**：受气相平衡域（0.1–20）限制，真机富氧预燃室远高于此；算例已取域上限。
4. **不支持过膨胀**：背压 > 出口压会返回 `RP_OUT_OF_DOMAIN`（退出码 4），因此两个算例都是**真空工况**，海平面比冲无法直接复现。
5. 推力是**标定值**（由公开推力量级反算总流量），因此"推力吻合公开值"**不构成独立验证**。

### 7.2 工程层面

6. 两个包的 `PACKAGE.json` 均已按当前内容**重建**，并新增 `modifications` 字段；原 `kind` / `schema_version` / `source_head` 字段保留未动。**如果你有外部 `SHA256SUMS.txt` 或发布流水线，需要按新清单重签。**
7. 发布包 `results/` 是**运行产物目录**（启动器每次运行会写 `*.json` / `*.err`），已通过 `PACKAGE.json` 的 `excluded_from_manifest: ["results/"]` 声明不纳入哈希。其中 9 份说明文档是手工文档，可长期保留。
8. `project/modules.json` 里 `tooling` 模块声明了 `tools/`、`scripts/`、`.githooks/` 以及 `tests/test_cli.py`、`test_data.py`、`test_handoff.py` 等 Python 检查，但**这些目录与文件在基线包中就不存在**（这正是基线 README 构建命令带 `-DROCKETPERF_ENABLE_PYTHON_TESTS=OFF` 的原因）。**本次未引入，也未补做。**
9. 补燃闭包**未接入 `docs/` 的方法说明文档**（`docs/propellant-*.md` 等仍是基线内容）。如果要让补燃正式"入册"，建议按现有 `docs/` 的写法补一篇 `docs/staged-cycle.md`，并在 `docs/architecture/*.svg` 里补一条支路回流路径。

---

## 8. 附：本次改动的复现方式

```powershell
# 1) 取得基线做对照（基线 zip 就在本目录，无需另找）
#    解压 代码(1)\rocketperf-c-source.zip  ->  基线源码包

# 2) 构建（结果应与 §1 一致）
cmake -S . -B build/cmake -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DROCKETPERF_ENABLE_PYTHON_TESTS=OFF
cmake --build build/cmake
ctest --test-dir build/cmake --output-on-failure

# 3) 回归对照：旧算例数值必须与基线一致（296.254 kN / 302.0952 s）
rocketperf.exe cycle prescribed cases\benchmarks\prescribed_cycle.ini

# 4) 新功能
rocketperf.exe cycle prescribed cases\active-cases\zhuque3-tq12a-open.ini
rocketperf.exe cycle prescribed cases\active-cases\cz10b-yf100k-staged.ini
```

**构建可复现性**：本次从零重新配置 + 构建，产出的 `rocketperf.exe` 与交接时包内 exe **字节完全一致（206 301 字节）**，说明改动是可稳定复现的。

---

## 9. 一句话总结

> 在 `27e29fa` 上**新增**了一个与原有开式闭包并列的**补燃循环闭包**，用一个可选的算例布尔开关在一个文件里切换两种循环；旧代码路径、旧字段、旧数值全部保持，回归实测一致；发布包补齐了"两型算例 + 参数来源 + 逐项说明 + 菜单启动器"，可直接用于课程演示与报告引用。唯一需要重点 review 的"改动中的修正"在 `cycle_case.c` 的未知字段判定（见 §3.5）。
