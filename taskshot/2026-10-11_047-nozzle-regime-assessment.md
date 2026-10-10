# 喷管过膨胀域评估与域外诊断

日期：2026-10-11，IMP-004；起始22dda59。剔除"pa>pe只返回out_of_domain"的最痛用户缺陷：海平面背压正是一级发动机工作点，此前什么都不给。方案是独立域评估路径，不弱化原附着求解契约。

`nozzle.h`/`frozen_nozzle.h`新增`RpNozzleRegime`三级分类（ideal_domain/overexpanded_possible/separation_hint）、`*RegimeResult`结构与`rp_nozzle_assess_ideal`/`rp_nozzle_assess_frozen`。实现以pa=0求理想附着解，报告理想pe/马赫/流量、含实际背压压力项的推力（可为负）、pa/pe、Summerfield型0.4pa经验分离参考压、由压力反解的匹配面积比与分离参考面积比。分离提示在头文件契约、JSON`basis`字段和文本"限制"行三处声明为经验提示而非分离/侧载预测。原`solve_*`对pa>pe仍返回out_of_domain，失败保持输出不动。

CLI新增`nozzle regime CASE.ini [--text]`（L0，复用算例文件解析）与`combustion regime-liquid-state ... [--text]`（连续液态CH4/O2链路）。JSON为新schema`ideal_constant_gamma_v1_regime_assessment_v1`/冻结对应版本，含`limitations`数组；既有命令输出未动。交互模式在燃烧室/L0求解返回out_of_domain时自动转域评估报告，不再干拒绝。新增研究算例`cases/research/s3_sealevel_regime.ini`（8 MPa/AR40/海平面，来源标注two-vehicle-study）。

tests/test_core.c新增`test_regime_ideal`（真空/欠膨胀/轻度/深度过膨胀分级，匹配与分离面积比回代后pe≈目标压）；test_combustion.c新增`test_regime_frozen`同型回代验证。test_cli.py新增regime JSON/text、regime-liquid-state、交互过膨胀管道回归。首轮调试修正两处测试侧问题：L0测试硬编码面积比按错误参数算出（改为公式精确值，回代验证本就通过），冻结area_ratio=0的期望从OUT_OF_DOMAIN改为INVALID_ARGUMENT以匹配冻结求解既有契约。

Debug/Release：core 247、adapters 29、thermo 8978、combustion 3918、cycle 353、CLI 44组全过。modules.json契约补域评估说明；架构SVG重生成后与模块结构一致（仅index.html时间戳变化）。project-guide运行章节与handoff复跑清单补regime命令与边界声明。

边界：域评估是理想等熵解加经验提示，不计算激波位置、分离点、侧载或真实推力损失；`pa>pe`只证明理想pe低于背压。真实型号性能仍未验证。
