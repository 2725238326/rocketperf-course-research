# 显式同基准入口焓HP与固定面积验证

日期：2026-10-05。任务 ANA-006；Windows 本地推进。未使用浏览器UI、computer-use、WSL或子agent，未刷新在线型号事实，不做PPT/最终报告，不推送远端。

## 交付

- C17 新增 `RpCh4O2EnthalpyFeed`、`rp_ch4_o2_inlet_enthalpy` 和
  `rp_ch4_o2_equilibrium_hp_enthalpy`。显式声明气态和
  `nasa9-cea-v3.3.4` 形成焓基准；旧温度入口 TP/HP API 保持含义和结果。
- 内部 HP 求解接收已校验的压力、O/F 和目标混合焓，不用虚构温度把显式焓
  绕入旧入口；输出零热交换边界，不含入口动能或轴功。
- CLI 新增 `hp-h` 与 `frozen-h`；后者复用已验收的燃烧室冻结/固定喉面积单喷管，
  不闭合泵、涡轮、分流、回流或液态物性。
- 新增 `tools/adiabatic_inlet.py` 与
  `results/validation/adiabatic_inlet_v1/manifest.json`，保存15次成功/失败
  C运行、参数、stdout/stderr、构建/测试身份、固定CEA卡/原输出/日志和哈希。
- 更新输入/热化学契约、工具/测试导航、架构SVG/Mermaid/offline HTML、handoff、
  review 和交接演示说明；新档案不覆盖旧原始证据。

## 数值和边界

固定气态基准：`Pc=10 MPa`、`O/F=3.4`、CH4/O2 各取 NASA9 的 298.15 K
焓。C 查询得到：

- `h_CH4=-4650159.6379939355 J/kg`
- `h_O2=-0.00040024263231910033 J/kg`
- `h_mix=-1056854.4634897183 J/kg`
- 新旧入口 `T=3673.614567611 K`
- HP 焓残差 `-0.00412250659 J/kg`

固定喉面积 `0.01 m²` 的显式焓 A10 真空结果为流量
`54.3659320258404 kg/s`、推力 `173550.363030799 N`、单喷管比冲
`325.520252033195 s`；A40 推力 `186769.129421118 N`；A10 背压5000 Pa
推力 `173050.363030799 N`。面积翻倍使流量/推力翻倍、比冲不变，背压扣除
为 `p_a A_e`。这是固定单喷管关系，不是整机性能。

## 实际检查

- 首轮 Windows GCC Debug：燃烧/喷管2900、核心207、适配器29、物性1175、
  循环353，CLI27组，零失败/零跳过。之后补CLI和归档反例，须重新完整验收。
- 中途 Windows GCC Release：同一C组通过，CLI30组；后续端点反例和最终质量
  另记，不用中途PASS代替收尾证据。
- 独立 CMake/Ninja Release：6/6 CTest 通过（core、thermo、combustion、
  cycle、adapters、cli）。
- GCC14.2 `-fanalyzer`：17 个生产 C 源全部 PASS，无诊断，记录在
  `build/static-ana006/manifest.json`。
- `python tools/project.py check`：PASS；架构重新生成并对 assignment/components
  SVG 做 PNG 视觉检查。
- `python tools/adiabatic_inlet.py verify results/validation/adiabatic_inlet_v1`：
  `15 runs`，PASS。

显式 API/CLI 反例覆盖 NaN/Inf、非正/越域压力与O/F、错误相态/焓基准、物种焓
越200–6000 K气相拟合区间、HP未夹逼/预算耗尽、固定面积/背压协议和输出保持。
归档反例在重算文件哈希后仍拒绝错误Q、推力、命令、CEA原文、二进制身份和
布尔伪数值。

## 范围结论

该方法回答的是“统一 NASA9 形成焓基准下，气态 CH4/O2 零热交换平衡如何由入口
焓决定”。它不能回答液态入口、煤油、真实流体、冷却/分离/寿命、全循环固定硬件
轴功热闭合、真实两型绝对性能或飞行验证。CEA与C使用同源物性，属于方法对照；
温度入口等价性共享内部求解，也不是独立算法或实验验证。

下一任务为 ANA-007：固定几何气态入口焓响应与参考域扩展。PPT/最终报告仍待
研究输入和证据稳定后处理。
