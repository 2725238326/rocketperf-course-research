# 代码质量实质改进与真实核查

日期：2026-10-14，执行者root。用户指出前期工作有自嗨成分，要求优化实际成果并直接本地提交（不建PR）。本轮给四个核心模块补物理文档、改进关键错误消息，并修正前期评估报告中的两处事实错误。

## 前期评估的错误与修正

- **"13744项测试无法验证"是错误结论**。前期评估用grep数CHECK宏（754个）否定测试规模，但13744来自 `test-report.json` 真实统计：core 250 + adapters 41 + thermo 8978（参数化物性数据点逐项检查）+ combustion 3922 + cycle 505 + CLI 48组。数字属实，口径为"验证检查项"含参数化展开，不是13744个独立用例。
- **"构建系统不可用"是方法错误**。构建入口是 `scripts/build.ps1` → `tools/pipeline.py`，不是裸cmake/make。前期评估没找对入口就下了结论。
- 两处修正已写回 [code-quality-reality-check.md](../docs/code-quality-reality-check.md)，不静默抹去原结论。

## 代码实质改进

- `src/thermo/equilibrium.c`：Gibbs最小化文档（4维变量定义、Newton+阻尼+线搜索、6000K起500K步长延拓、HP二分、Log-sum-exp稳定性、9物种适用边界）。
- `src/cycle/adiabatic.c`：GG/ORSC循环文档（守恒方程、Q=0假设、涡轮出口压力的循环差异）。
- `src/nozzle/frozen.c`：冻结流文档（与ideal.c的γ常数/γ(T)区别、能量/熵/质量守恒）。
- `include/rocketperf/combustion.h`、`engine_cycle.h`：结构体字段补单位注释和典型范围。
- 错误消息改进6处（equilibrium域检查/元素库存/元素守恒、adiabatic输入验证/ORSC约束、ideal超膨胀）：带具体数值、物理含义和恢复建议。

## 工程问题与修复

- **契约字符串钉死**：改 ideal.c 超膨胀错误消息后，`pipeline.py` 的 study 域排除校验仍精确比对旧文案，runner 两个用例失败。这是本轮改动真正引入的回归（不是既有问题）。修复：校验改为匹配 `Overexpanded:` 前缀（保留对假排除的拒绝能力，伪造文案测试同步更新为合法格式仍被拒——因为该点物理上不超膨胀）。
- **launcher 测试失败为环境问题**：handoff 的运行包测试在本会话报 cmd 9009。定位：会话环境含 `NoDefaultCurrentDirectoryInExePath=1`（注册表未设，系本会话进程注入），禁用 cmd/CreateProcess 对当前目录 exe 的隐式搜索；launcher bat 依赖该行为。清除该变量后 handoff 16项全过。非代码缺陷，未改 launcher。

## 验证记录

- `scripts/build.ps1 -Configuration Release`：Build PASS（-Werror）。
- `python tools/pipeline.py test --configuration Release`：13744项检查0失败（HP、冻结喷管A=10/A=40、循环性能数值输出与既有基线一致）。
- 首次并发跑pipeline test与quality时出现"Validation inputs changed during tests"及liquid-hp临时目录FileNotFoundError；串行重跑无此问题，判定为并发互踩工作目录，非代码缺陷。失败记录未抹去。
- 统一质量 `python tools/quality.py` 期间曾因根目录误建 `.improvement-plan.md`（未分类根条目）FAIL；删除后重跑。runner 契约修复后 PASS；handoff 清除环境变量后 PASS。完整六组结果以本轮登记的新鲜质量证据为准。

## 未完成与不夸大

适配器/CLI层约15个文件仍无文档；186个错误点仅改进约7个；无CI、无覆盖率工具。本轮改进是文档与诊断质量，不改变任何计算结果或物理模型。
