# 数据边界

首版参数台账见 `data/parameters/baseline.json`。它把来源事实、派生换算和教学基准分开；真实型号记录只承担构型与边界说明，未公开字段不会被自动填入求解器。研究假设必须另建带范围、理由和模型ID的记录，不能覆盖事实记录。

当前真实型号资料在`调研/证据与参数台账.md`及原始来源中，本目录尚无可直接投入计算的真实发动机参数集。

教学输入在`cases/benchmarks/`，参考值在`tests/reference/`。DATA-001/002已完成首版台账、逐字段复核与来源ID/单位/数据角色检查；未知型号字段仍保持null，校验通过不等于有完整真实输入。

`parameters/feed_property_candidates.json`是RES-006的研究候选档案，不是生产输入。它保留CEA单温度液态反应物锚点、CoolProp EOS身份、NIST surrogate和未知的真实发动机字段；运行`python tools/feed_candidates.py check`可按固定原始来源重生成并核对。

ANA-008只从固定CEA原文提取CH₄(L)/O₂(L)两条记录生成`src/thermo/reactants_generated.h`，供独立固定锚点HP接口使用；`generate-header`/`check-header`检查其身份。整个候选JSON、CoolProp EOS、RP-1和surrogate不是生产运行时输入；[方法边界](../docs/liquid-anchor-validation.md)不含液体密度/压力修正或真实型号字段。

初版CLI只支持`synthetic_benchmark`和`research_scenario`。增加真实型号类别前须先设计并验证字段级证据契约，而非仅增加一个标签。
