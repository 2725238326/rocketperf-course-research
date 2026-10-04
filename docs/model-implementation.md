# 模型实现说明：L0 与 S1

版本：IMP-001 v0.1；实现日期：2026-10-02

本文件专门描述L0/S1。NASA9、受限气相TP/HP和温变冻结喷管见[独立接口](thermo-nozzle-validation.md)；给定热状态外排循环已实现，见[循环边界](cycle-validation.md)。冷却求解和有限元未实现，循环原型不能当作真实发动机闭合。

## 1. 已实现的入口

L0/S1包含两个入口：

| 入口 | 用途 | 结果边界 |
|---|---|---|
| `rocketperf run CASE.ini` | 单个 L0 定比热准一维喷管算例 | 失败时无半份成功结果 |
| `rocketperf study area-ratio-ambient CASE.ini` | S1 面积比—环境压力笛卡尔扫描 | 每个点独立记录 `ok` 或模型域状态 |

S1 复用同一个 `rp_nozzle_solve_ideal`，因此扫描不会产生一套与单算例不一致的物理公式。扫描只改变 `area_ratio` 和 `ambient_pressure_pa`；`gamma`、`R`、`T0`、`p0`、`At` 来自算例文件。

## 2. C 接口与内存契约

核心接口在 `include/rocketperf/nozzle.h`：

- `RpNozzleInput`：SI 制输入；不包含文件路径、来源文字或界面状态。
- `RpNozzleResult`：单点成功结果；求解失败时调用方原有输出不被覆盖。
- `RpNozzleStudyGrid`：只读面积比和背压数组。
- `RpNozzleStudyPoint`：单个网格点的输入坐标、`RpStatus`、成功结果或短错误诊断。
- `rp_nozzle_scan_area_ratio_ambient`：按“面积比外层、环境压力内层”行主序写入点数组。

扫描数组容量由调用方传入。无效参数在写点数组前失败；非空`point_count`在入口清零。`RP_OK`表示网格评估完成，调用方仍须检查每点状态。CLI把`out_of_domain`保留为模型排除点；数值失败返回非零，不能称为一次成功计算。单点求解失败不修改原结果。

## 3. 命令行输入

默认网格为：

```text
area_ratios = 1, 1.25, 1.6875, 2, 4, 8, 16
ambient_pressures_pa = 0, 25000, 50000, 100000
```

可显式指定不超过 32 个值的网格轴：

```powershell
python tools/pipeline.py run --study area-ratio-ambient --case cases/research/s1_area_ratio_ambient.ini --area-ratios 1,1.25,1.6875,2,4,8 --ambient-pressures 0,25000,50000,100000
```

参数是十进制/科学计数法数值，不接受单位后缀、`NaN`、`Inf` 或空值。面积比限定为 `1...1e4`，环境压力限定为有限非负 Pa。CLI 参数错误返回2；算例格式/文件错误返回3；模型域或数值错误返回4。

## 4. 输出和证据链

扫描 stdout 是确定性的 UTF-8 JSON，包含：

1. `study.id=S1_area_ratio_ambient`、算例标识、算例类型和 `source_ref`；
2. 不含扫描轴的基准输入；
3. 两个网格轴及其固定排序；
4. 每个点的坐标、状态、成功结果或错误文字；
5. 明确的模型限制，特别是“研究情景输入不是已验证发动机数据”。

结果中的 `thrust_n` 是当前 L0 控制体下的喷管推力，不是整机推力；`mass_flow_kg_s` 是喉部理想阻塞流量，不含涡轮、泵、燃气发生器或冷却支路。`out_of_domain` 点不能被绘图脚本当成零值或插值成功值。

## 5. 独立验证

- `tests/test_core.c`：保留 Mach 2 闭式参考、连续方程和总焓守恒，并增加 2×3 网格扫描、越域点保留和非法网格拒绝。
- `tests/test_cli.py`：验证自定义网格、确定的点数、越域状态、背压增大导致推力下降，以及非法 CLI 轴值。
- `tests/test_adapters.c`：直接测试JSON写前检查、控制字符转义、未终止字符串、非有限数、点数和坐标对应。
- `tests/test_runner.py`：测试默认及自定义扫描归档；错误坐标、网格、数值和状态不能成为成功记录。
- `python tools/pipeline.py test --configuration Debug` 和 Release 构建均必须重新执行；旧构建不能作为当前实现证据。
- 解析参考仍来自 `tests/reference/air_mach2.json` 和 `docs/benchmarks.md`，不是由扫描程序自己生成的参考值。

这些测试证明数学实现和协议边界，不证明任何真实发动机的绝对性能。真实型号字段仍须通过字段级公开证据进入独立参数记录；缺失字段不能从产品页或同系列型号拼接。

## 6. 后续实现条件

L1固定数据/气相参考和L2外排计账原型已经落地；各自验证范围以专题说明为准。后续扩大物理范围时仍需新输入契约与独立参考。空气基准不能被认作已完成课程研究。

L0归档校验现在重算面积—Mach、温度、压力、速度、cstar、流量、推力、CF、Isp和出口连续关系；扫描越域点通过背压边界反算核对，不接受任意诊断文字。Python不重新求解面积根，只校核C报告的状态。
