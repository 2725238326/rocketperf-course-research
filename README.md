# 火箭发动机原理 · Rocketperf

本项目研究朱雀三号与长征十号乙动力系统，用C17程序做热化学、喷管和条件性循环分析。公开资料不足以组成四级段真实性能卡；凡带型号名称的可运行输入都是研究情景，不能据此声称飞行实测性能。

**第一次接手：**[当前进度](worknow.md) → [四级段研究](docs/two-vehicle-study.md) → [文档导航](docs/README.md) → [项目解读](docs/project-guide.md)。

任务、代码、来源和算例职责见[项目地图](docs/project-map.md)；构建/任务/交付规范见[治理说明](docs/governance.md)。

## 目前能运行的循环情景

新模型提供绝热发生器开式外排和全氧化剂富氧补燃两条拓扑；两条都是真实物理机制下的研究原型，参数由算例明确假设。长十乙一级的补燃是发动机家族层面的构型支持，不是首飞具体子型性能卡；长十乙二级循环保持待判。模型方程与版本边界见[循环实现对照](docs/cycle-integration.md)，算例和试跑见[循环验证](docs/engine-cycle-validation.md)。

```powershell
python tools/pipeline.py test --configuration Release
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/zq3_y1_stage1.ini --text
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage1.ini --text
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage2.ini --text
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage2_orsc.ini --text
```

朱雀三号一级和二级的甲烷开式情景分别见`zq3_y1_stage1.ini`、`zq3_y1_stage2.ini`；长十乙一级使用指定RP-1替代物，二级同时提供开式/补燃两种待判情景。所有输出都标明研究输入，不代表该型号真实流量、推力或比冲。汇报前应复核最新质量报告和研究归档，不能把单项构建或测试当作任务验收。

## 其他计算入口

```powershell
python tools/quality.py
python tools/pipeline.py run --case cases/benchmarks/air_mach2_vacuum.ini
./build/release/rocketperf.exe combustion hp 10000000 3.4 298.15 298.15
./build/release/rocketperf.exe study propellants 2.6 2.6 10 0
```

理想喷管基线、NASA9/九气相TP/HP、燃烧室冻结喷管、连续单相液体入口和固定RP-1入口各有不同适用域；入口及验证入口集中在[文档导航](docs/README.md)。正式研究归档放`results/research/`，验证归档放`results/validation/`，临时尝试放忽略的`build/`或`results/local/`。

## 源码与交付

生产物理解算由C17直接运行。Python仅用于构建编排、归档和独立复算。完整阶段包的生成与核对见[交付说明](docs/delivery.md)；生成阶段包要求干净版本和完整新鲜质量证据。项目工程通过不等于两型真实性能验证，也不等于课程最终报告/PPT已完成。
