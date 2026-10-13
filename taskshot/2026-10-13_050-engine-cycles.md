# MOD-009：两型研究入口与绝热循环原型

日期：2026-10-13（北京时间），承接2026-10-12首次实现。五个情景不是飞行性能卡。

## 实现

- 新model ID `adiabatic_single_shaft_cycle_v1`、公共`RpEngineCycleInput/Result`和独立`src/cycle/adiabatic.c`。布尔拓扑切换发生器外排或全氧化剂富氧预燃室补燃；保留旧`prescribed_thermal_cycle_v1`原契约。
- C17经HP求Q=0预燃室/主室状态。新开式按泵/辅助轴功和冻结涡轮比功求分流；新补燃按轴功反解涡轮出口压力、执行回流元素/焓混合后重求主室HP。质量、CH/O元素、整机轴功、外排/回流口径均输出并核验；背压不可达、支路饥饿、超域和收敛失败明确拒绝。
- 新增严格CLI研究算例：朱雀三号遥一一/二级开式、长十乙首飞一级RP-1指定替代物补燃、长十乙二级开式与补燃待判两情景。文档另设证据地图，家族信息不升级成子型实机数据。
- `engine_cycles.py`复算保存的C/CEA状态、运行流、输入和哈希；修正归档器采集Git dirty状态的时机，新测试校验清洁/dirty标记逻辑。

## 验证

- 最终全量`python tools/quality.py`：六组PASS。运行管理验证已覆盖两款新工具的夹具输入指纹。
- GCC严格选项：Debug和Release当前核心检查分别包含core 250、adapters 41、thermo 8978、combustion 3922、cycle 505断言；CLI 48组，完整值见build报告。测试量不代表物理实验数量。
- `python tools/static_analysis.py --destination build/qa009/analyzer-v1`：30个生产C翻译单元GCC14.2.0 analyzer PASS。
- 架构图与更新SVG实渲染检查；`python tools/project.py check`本轮链接检查无问题，具体数量以对应质量日志为准。
- 正式[engine_cycles_v2_20261013](../results/research/engine_cycles_v2_20261013/manifest.json)：5成功+4预期拒绝、12张固定CEA卡、814项报告状态关系。C和CEA受限九气相HP温度差最大约0.004 K；扩展产物集合的差最大约0.392 K。软件同条件对照不是实验验证。
- 五例演示值仅为100 kg/s等情景：朱雀三号一级开式约290.54 kN/296.27 s；长十乙一级RP-1替代物富氧补燃约285.50 kN/291.13 s。不同输入不得排名，也不等于实机值。

归档manifest记有`source_head=83d13a5`及`source_dirty=true`。此标记保持归档时工作区事实；C可执行文件、Build/Test、原文参考及每个输入通过哈希绑定。根目录`代码.zip`在整理期间保留，既未解包混并也未纳入此C构建。v1早期档案与build probe保留，不覆盖；推荐核验v2。

## 科学和适用限制

开式/补燃对应的是明确假设下的部件拓扑研究。朱雀三号使用燃气发生器家族证据，长十乙一级只引用130吨级/相关发动机家族补燃证据；首飞具体子型后缀与性能工况未补造。长十乙二级循环身份仍未知。RP-1固定替代物不代表国产煤油组成。

受限模型为九种中性理想气相C/H/O、1000–6000 K HP、恒密度泵、冻结涡轮/喷管；缺少泵图谱、喷注/冷却、低温预燃室真实物性、凝聚碳、瞬态、损失标定和整机/实验参考。不能用残差或CEA对照替代实机验证。

复跑：先`python tools/quality.py`，再`python tools/engine_cycles.py verify results/research/engine_cycles_v2_20261013`。后续修改不得覆盖v1/v2；新输入、程序或验证规则要创建新的日期版本，并重新质量验收。
