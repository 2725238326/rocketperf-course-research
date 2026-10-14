# 2026-10-14_059：甲烷富燃凝聚碳判据、代码规整与演示内容充实

- 关联任务：QA-006
- 本轮请求/范围：用户要求答辩控制在15分钟内、内容饱满；甲烷O/F域“按你的想法优化”；代码整体规整并保证运行无误。
- 起始状态：93b99bf（QA-005完成）。

## 实际检查和改动

- **凝聚碳判据**：九气相无C(gr)，原甲烷路径O/F 0.1–20全接受，O/F 0.5返回残余CH₄约49%的态。改为物理判据：平衡收敛后由碳元素势πC计算石墨活度`a_C=exp(πC−g°C(gr)/RT)`，`a_C>1`返回`RP_OUT_OF_DOMAIN`且不改输出；HP只判收敛温度，二分试探点不判。覆盖气态、显式焓、液态锚点、连续液体、RP-1及循环预燃室/主室全部路径。
  - C(gr)拟合由`tools/thermo_data.py`从固定thermo.inp（同哈希）生成到`src/thermo/graphite_generated.h`；固定气相数据集`cea-v3.3.4-neutral-cho-n-v1`的TSV、头文件、manifest字节不变，Cantera参考无需重建。
  - JSON diagnostics与`--text`诊断新增`graphite_activity`；`combustion_reference.py`、`engine_cycles.py`同时接受无该键的旧归档和带该键的新输出。
  - 结果：液甲烷10 MPa下O/F 1.0为0.883、0.9为1.09（拒算）；开式发生器0.869；补燃预燃室约10⁻¹⁸。
  - 核对：测试中由Boudouard平衡独立重算a_C，对数差<10⁻⁶；Python用CEA九气相归档组成重算RP-1 O/F 1.0得a_C≈3.2，对应CEA扩展产物析出石墨0.059；O/F 2.2为7×10⁻⁵。
- **代码规整**（行为不变，全部测试回归）：g0统一为`RP_STANDARD_GRAVITY_M_S2`（4处）；冻结膨胀温度下限合并为`rp_cho_minimum_temperature`（frozen.c/components.c）；首行BOM处理合并为`rp_text_strip_bom`（4个解析器）；JSON字符串转义合并为`rp_text_write_json_string`（2处）。编译选项`-Wall -Wextra -Wpedantic -Werror -Wconversion -Wshadow`零警告。
- **运行缺陷**：交互菜单8在非仓库根目录启动（直接双击exe、快捷方式）时io_error。新增`rp_find_bundled_case`：先查当前目录，再查exe所在目录及最多四级父目录；加CLI回归测试。
- **演示页**增至五页：新增“燃烧室与积碳边界”（O/F 0.5–4.0组成堆叠图、a_C对数曲线与拒算区）和“CEA对照”（读取两份验证归档的2148项字段，偏差/容差散点与关键量表）；甲烷推进剂页O/F放宽到2.0–4.0。修复JS中整数O/F键（`String(3.0)=="3"`）查表失败。1920×1080与1366×768均无滚动，五页全部滑块逐点驱动无NaN/undefined、无控制台错误。
- **讲稿**12页、主讲约13分45秒；每页标题结论+表+要点+讲稿；新增P5燃烧室页、判断第5条；检查项总数更新为13759（live panel同步）。报告第2节、7.1、7.7、判断5相应补充。

## 验证结果

- Release测试：core 250、adapters 41、thermo 8978、combustion 3935、cycle 505、CLI 50组，全部通过。
- `python tools/demo_data.py --check`：2501次C运行逐字段复现。
- `python tools/thermo_data.py --check`：三个生成产物无漂移。
- 统一质量入口结果见QA-006验收证据。

## 未解决和下一步

- 判据只说明平衡下固体碳是否稳定，不计算析出量、积碳速率或位置；未逐点比较CEA凝聚相组成。
- 讲稿未实测计时；PPT、组员确认分工、演练由小组完成；PPT定稿后重跑quality。

## 交接更新

handoff、tools/README、engineering.md、review已同步；任务经工具登记QA-006。
