# 项目交接

从[当前工作面](worknow.md)读取任务，运行`python tools/project.py doctor`核对Git实况。领取和验收命令见[治理说明](docs/governance.md)。

## 研究产物

| 需要理解的内容 | 阅读入口 | 使用边界 |
|---|---|---|
| 两型工作方案、能力和参数缺口 | [四级段研究](docs/two-vehicle-study.md)、[要求映射](docs/requirements-map.md) | 遥一与长十乙首飞一二级分别记录；两型原文截止2026-10-03 |
| 甲烷燃烧与喷管 | [连续液体HP核验](docs/liquid-combustion-validation.md) | C17单相入口表→九气相HP→固定面积冻结喷管；温压为研究假设 |
| 煤油方法 | [固定RP-1入口](docs/kerosene-validation.md)、[边界研究](调研/专题/RES-008_煤油计算边界.md) | C公共API/CLI已有；10 MPa/O-F2.2–4.0指定反应物，国产燃料批次仍未知 |
| 改进计算 | [改进分析](docs/improvement-analysis.md)、[入口响应](docs/adiabatic-inlet-study.md) | 同条件收益、几何代价和输入响应；真实改装量或寿命仍缺证据 |
| 方法比较 | [甲烷/RP-1成对研究](docs/propellant-method-comparison.md) | 同Pc/At/几何/背压，差值由C返回，保留各自入口/O-F身份 |
| 循环 | [循环核验](docs/cycle-validation.md)、[热边界](docs/research-thermal-boundary.md) | 给定热状态外排原型；泵后供给、回流组成与完整循环尚未闭合 |
| 保存输入、结果与参考 | [研究档案](results/research/README.md) | 每个版本带清单/哈希与失败记录，按其自身日期和构建身份使用 |

[架构三视图](docs/architecture/README.md)说明业务和模块边界。[模型契约](docs/engineering.md)维护物理假设；源码清单由`project/modules.json`维护。

## 复跑

```powershell
python tools/quality.py
python tools/liquid_combustion.py verify results/validation/liquid_combustion_v1
python tools/kerosene_reference.py verify results/research/kerosene_products_v3_20261006
python tools/kerosene_validation.py verify results/validation/kerosene_anchor_v1
python tools/propellant_comparison.py verify results/research/propellant_comparison_v1
python tools/pipeline.py run --model prescribed-cycle --case cases/benchmarks/prescribed_cycle.ini
```

研究归档复核使用已保存文件；重新生成参考需要固定上游构建或可选物性环境，要求见相应工具说明。正式运行使用manifest指向的新鲜已测试构建。`build/release/rocketperf.exe`是便捷别名；新RunId/研究版本不能覆盖旧记录。

## 必须解释的限制

- RP-1、NIST surrogate和国产煤油批次是不同输入身份；四对象映射关联证据和方法，尚不足以构成真实性能卡。
- 推力室、整机、整箭口径分别使用。单喷管HP不闭合支路轴功、回流、喷注或泵后过程。
- 约302 s和约193.65 MW来自给定热状态合成循环；后者是模型所需排热，不能直接当作冷却设计负荷。
- 面积和背压研究不计算质量、侧载、流动分离或寿命。局部扰动是情景响应，不能称概率置信区间。
- CEA/Cantera等同源数据对照验证软件方法；机械PASS不构成独立实验或具名科学审查。
- 日常构建与交付使用Windows。历史WSL sanitizer结果只覆盖当时版本；远端CI配置不等于执行记录。

公开字段缺失时继续独立方法研究，并记录其影响。具体任务顺序以worknow为准，PPT和最终报告暂缓。

组员参数审阅见[RES-009](调研/专题/RES-009_组员参数审阅.md)：产品参数与试验产品保留各自身份，TQ-15B能力误归属和长十乙后缀推断不能进入输入。最终Windows计算程序直接由C运行，辅助工具单列于开发/参考附件。

## 交给其他组员

此次私有GitHub阶段交付的源码包、运行包与详细解读见[交付说明](docs/delivery.md)和[项目解读](docs/project-guide.md)。用户已明确授权本次远端同步和Release；日常工作仍不默认推送。压缩包固定一个干净提交，源码重建和exe运行记录随交付保留。

按[接收说明](docs/receiving.md)固定干净提交后生成运行包与离线源码bundle，接收者实际复跑成功与拒绝案例，并说明确认与未确认内容。新包v3使用`checks`记录接收检查，v2保留任务快照，v1/v2可读；旧包只代表其固定版本。

近期批次：[参数审阅与RP-1接口](taskshot/2026-10-06_042-parameters-and-rp1.md)、[RP-1研究](taskshot/2026-10-06_040-kerosene.md)、[维护整顿](taskshot/2026-10-06_041-maintenance.md)。历史过程见taskshot；风险与补审见[review](docs/review.md)。每个实质批次审查并本地提交；外部推送需另有授权。
