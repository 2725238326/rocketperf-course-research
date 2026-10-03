# Windows验收修复与阶段交接

日期：2026-10-04（北京时间）。任务QA-001；从7621620继续，分支codex/quality-handoff。修复范围与逐项证据见[补审](../docs/review.md)。没有联网检索、WSL构建、原始资料清理或外部推送。

## 修复产物

参数检查进入Debug/Release流水线；严格JSON、逐字段假设范围与引用存在性检查落地。循环报告新增物性、元素、cstar/Mach/通量和尺度化残差复算，基准执行132条关系。归档全部文本进入测试身份；输入缺失、目录输入与超时均留失败记录。工程行尾规范化与原始字节保护分开。

历史v1归档仍报告原86条证据，额外执行新检查而不改写原文件；新增归档为`results/validation/prescribed_cycle_v2_20261004_qa001/`。模型ID不变；校验版本为2，不把校验增强说成新增真实发动机能力。

`tools/handoff.py`提供create/verify/receive；交接方法见[接收与讲解](../docs/receiving.md)。正式包只接受干净提交、新鲜完整质量和已测程序，保存source.bundle、输入、NASA CEA许可、报告、哈希及隔离PATH演示。具名receive实际运行成功和预期失败，不能代替科学审查。

## 已执行的定向验证

- Release实际执行core207、adapters29、thermo1175、combustion2512、cycle241项和CLI22组，零失败、零跳过。
- 治理18组、运行管理19组、交接6组通过；覆盖缺文件、路径逃逸、损坏程序、错误清单及具名复跑。
- 固定Cantera单物种状态对照与循环校验6组通过；数据检查增加无效值、逐字段范围、重复键、指数溢出和伪引用反例。
- CMake/Ninja Release新目录`build/cmake-qa001/`通过6/6 CTest，GCC14.2严格警告无错误。
- 三张架构图渲染为`build/architecture-qa001-{business,components,workflow}.png`并逐图视觉核对；业务、计算、执行与人员交接边界清晰，未裁切或遮挡。

## 遇到的问题与处置

早期交接测试夹具未包含新增校验工具；补齐夹具，不放宽生产清单。新增归档或工具后旧测试证据明确过期，随后重新执行质量入口，不沿用旧PASS。跨检出工程文本指纹只规范CRLF/LF，原始档案任何字节变化仍使验收失效。

尝试在独立JavaScript环境加载Windows图像库不可用，改用Windows已有Node运行时直接渲染SVG；没有启用浏览器UI或下载替代依赖。

## 最终验收和交接

所有本轮实现与规范稳定后运行`python tools/quality.py`，以`build/quality/latest.json`及任务提交时的不可变快照为依据。独立源码检出、正式交接包和实际接收验证放在`build/`，不会把生成包或重复源码加入Git。完成后追加新的验收快照，不改写本记录或旧资料。

后续继续ANA-002的同条件改进、代价和敏感性研究。当前外排循环仍是给定热状态合成方法；约302 s不是目标型号性能，液态入口、回流与真实循环未闭合。PPT/报告仍后置。
