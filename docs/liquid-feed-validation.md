# C17 连续单相液体查表核验

证据截止：2026-10-05。接口只回答假设温压下纯甲烷/纯氧的密度与化学焓；它不是通用液体 EOS，也没有接入 HP、泵或循环。固定参考、焓零点和质量口径见[入口契约](liquid-feed-contract.md)，实际 C 成功/拒绝运行见[归档清单](../results/validation/liquid_table_v1/manifest.json)。

## 输入、实现与失败

[公共接口](../include/rocketperf/liquid_feed.h)接受固定数据集 ID、流体、单相声明、温度和压力。[实现](../src/thermo/liquid_feed.c)使用不可变 C 常量与双线性插值，无文件、网络、堆分配或 Python/CoolProp 运行时依赖。

| 流体 | 温度域（含端点） | 压力域（含端点） | 节点 / 内部参考 |
|---|---|---|---|
| Methane | 100–140 K | 1–20 MPa | 231 / 400 |
| Oxygen | 80–110 K | 1–20 MPa | 176 / 300 |

最大端点属于最后一个单元；不钳位、不外推、不自动换模型。NULL、非有限或非正温压返回 `invalid_argument`；未知 ID/流体、气相/两相声明与域外查询返回 `out_of_domain`。失败保持调用方输出；成功清除旧错误。CLI 成功只写 JSON，失败 stdout 为空，参数语法错退出 2，数值或适用域错误退出 4。

## 核验口径

- 测试覆盖全部407节点与700个直接 HEOS 内部参考，生产数据与测试参考分别生成。节点判据接近机器精度；内部密度相对误差 ≤0.05%，摩尔焓误差 ≤5 J/mol。实际内部最大密度误差0.010135%，最大焓差0.459415 J/mol；这是指定样本的最大值，不是连续域误差上界或实验精度。
- 输出分别保留 EOS 密度分子量和 CEA 化学分子量；质量焓按后者由摩尔焓换算。甲烷两种分子量相差约21.19 ppm，不能混用。CEA kg/kmol 到 kg/mol 的浮点换算也按固定来源复现，不据单个末位差异改动物性表。
- 覆盖端点外 `nextafter`、NaN/Inf、NULL、非法相态、未知来源与失败输出保持。CLI 另测6次成功与16次拒绝，核对输入对应、结果、来源、焓基准与重复输出。
- 归档固定已测试 Release 程序的构建/测试身份与22次原始 stdout/stderr。离线核验重新计算结果关系；篡改测试包括改结果后重算文件哈希、替换质量/焓基准、伪造输入、失败输出和重复 JSON 键。哈希证明字节身份，不是科学结论的签名。

HEOS 原始模型、独立 Helmholtz 系数复算和 NASA9 理想零点对照仍是同源模型的软件核验；不能称实验或另一位人员的独立科学审查。查表生成参考需要固定 CoolProp，验证与 C 执行不需要。

## 复跑

从项目根目录执行：

```powershell
python tools/liquid_table.py check
python tools/pipeline.py test --configuration Release
.\build\release\rocketperf.exe liquid-feed coolprop710-cea334-liquid-molar-v1 Methane liquid 120 10000000
.\build\release\rocketperf.exe liquid-feed coolprop710-cea334-liquid-molar-v1 Oxygen liquid 100 10000000
.\build\release\rocketperf.exe liquid-feed coolprop710-cea334-liquid-molar-v1 Methane two-phase 120 10000000
python tools/liquid_table.py verify results/validation/liquid_table_v1
python tools/quality.py
```

两个节点成功输出分别约为：甲烷密度419.793800 kg/m³、摩尔焓−88521.901918 J/mol；氧气密度1116.286536 kg/m³、摩尔焓−12252.605872 J/mol。负焓来自声明的化学零点，不表示负绝对能量。第三条命令应拒绝，不产生成功 JSON。

`build/release/rocketperf.exe`只是便捷别名；正式归档工具从新鲜已测构建清单定位具体程序，并拒绝覆盖已有归档。后续接 HP 时须另立模型 ID、质量/元素/能量边界和验证，不能修改旧固定液态锚点或把温压假设补成型号事实。
