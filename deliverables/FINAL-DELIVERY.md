# 大作业最终交付

本页汇总报告、答辩材料、计算程序和复现入口。报告与答辩稿以本页标出的终稿文件为准；研究输入和结论按其公开资料、研究假设与模型适用范围解释。

2026-10-20当前提交入口为[分工更新版](submission-20261020-v3/README.md)：按组员确认调整报告第10节，源码、程序与PPT保持审查修订版字节。[审查修订版](submission-20261020-v2/README.md)、[前一版提交目录](submission-20261020/README.md)和下列原定稿继续保留。使用分工更新版压缩包上传，固定源码提交、SHA256和检查范围以其manifest为准。

## 提交文件

| 交付物 | 文件与用途 |
|---|---|
| 课程报告 | [report-final.pdf](report_typst_v1/report-final.pdf)，A4 共 20 页；[Typst 源码](report_typst_v1/report.typ)、所用模板说明、插图和数据清单在同目录。 |
| 答辩演示稿 | [两型火箭动力系统_答辩终稿.pptx](presentation-final/两型火箭动力系统_答辩终稿.pptx)，16:9 共 17 页；包括动态架构取帧、四个 GUI 页面、结果表和参考文献。 |
| C17 源码与测试 | 仓库 `src/`、`include/`、`tests/` 及构建说明；计算核心和 CLI 为 C17。 |
| Windows 命令行程序 | `build/release/rocketperf.exe`，由本轮 Release 构建生成。 |
| Windows 图形界面 | `build/gui/dist/RocketPerf-GUI/` 便携目录，包含 `rocketperf-gui.exe`、循环研究算例和两项界面组件许可。需要系统提供 Microsoft Edge WebView2 Runtime。 |
| 报告与答辩配套材料 | `report_typst_v1/figures/`、`ppt-figures-package/`、`ppt-materials/`、`科研绘图整理_20261016/` 保存图表源、科研数据、动态架构页面和替换素材。 |

本轮快速收尾没有重新生成源码 ZIP 与命令行 ZIP；如需这两种接收包，按[阶段交付说明](../docs/delivery.md)在新鲜质量证据对应的干净提交上运行打包和核验。GUI 界面代码不进入 C17 核心或命令行程序。

## 复现与启动

在项目根目录运行统一检查和 Release 测试：

```powershell
python tools/quality.py
python tools/pipeline.py test --configuration Release
```

命令行程序可直接运行；源码按项目 CMake/Ninja 说明构建。GUI 便携目录双击 `rocketperf-gui.exe`，循环页面读取同目录 `cases/vehicles/*.ini`；页面调用进程内 C17 核心，显示数值可用相同输入的命令行结果复核。

## 研究结论的使用范围

报告分别讨论朱雀三号遥一和长征十号乙首飞构型所对应的公开资料与研究问题。用于计算的热力、几何、循环和推进剂输入按算例说明；资料未披露的真实发动机参数没有用同系列或产品资料补齐。因此 C 输出是声明输入下的研究结果，不作为两型发动机的实测或完整设计性能。

C17 核心涵盖气相热化学、喷管性能、推进剂方法比较和稳态循环研究。已有守恒检查和 NASA CEA 数值对照限定在具体物种、输入和模型范围；CEA 对照使用部分同源数据，不构成独立实验验证。程序未覆盖真实泵图谱、喷注与两相供给、完整冷却、瞬态控制、喷管流动分离及结构寿命。RP-1 研究输入也不代表国产煤油批次。

GUI 提供燃烧室、喷管、推进剂比较、循环等操作页面。C 桥接测试覆盖 GUI 与命令行数值一致、输入导出复算、非法 JSON 和扫描点数校验；GUI 使用系统 WebView2 Runtime。页面和截图用于展示操作，不替代计算归档与研究结论。

## 后续工作次序

1. 接收者在另一干净目录解压运行包，核对包外 SHA256，并分别复跑一个成功案例和一个预期拒绝案例；源码接收者再按 README 重建并运行 C 测试。
2. 对两型每个级段补充可定位且对应批次/工况的发动机参数、真实推进剂组成和供给状态；在证据不足时继续保留未知项。
3. 获得匹配工况的独立实验或异源参考后，再评估模型误差和不确定度。之后再考虑泵/涡轮特性、喷注、冷却、流动分离和瞬态等工程模型。
4. GUI 桌面窗口的最终原生截图与使用环境核对另行记录；浏览器预览和桥接测试不替代该视觉验收。

## 校验值

以下 SHA256 对应当前终稿 PDF、PPTX 和本机 Release 程序。命令行 ZIP 与源码 ZIP 未在本轮重新生成。

| 文件 | SHA256 |
|---|---|
| `report_typst_v1/report-final.pdf` | `574564441c3a999075c2e907a30719b5407718a44249691ffb11a11611d8fd49` |
| `presentation-final/两型火箭动力系统_答辩终稿.pptx` | `063b0175931ff65854147e9d02ae067a11144351d59c2aee4e2a9c2fc258153b` |
| `build/release/rocketperf.exe` | `a6504f5aec861acd2566d3ca18540768db4b95fc9852bf9f204b8ba9d6cb9c77` |
| `build/gui/dist/RocketPerf-GUI/rocketperf-gui.exe` | `11f566ee1f53484f2720a93941cc6e1a64556db907e7ac5140e47edb4e71c18e` |
