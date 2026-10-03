# 项目架构三视图

打开[离线架构浏览页](index.html)，可切换三张视图并查看模块维护契约。不依赖网络或CDN，可直接打印。

## 业务流程

![证据到结论](business.svg)

展示研究问题如何经过证据、模型、计算、验证形成交付，以及证据不足时回到哪里。它不是宣称所有研究阶段都已完成。

## 功能核心

![模块边界](components.svg)

实线表示主要编排/调用，虚线表示公共接口依赖。图中可见NASA9→TP/HP状态、冻结喷管及外排循环的连接；灰色框为给定热状态的循环原型，不支持回流混合。为避免连线遮挡，少量公共依赖用脚注说明，完整依赖图见[Mermaid源](components.mmd)。

## 任务流程

![任务与质量](workflow.svg)

展示任务状态、质量证据、阻塞/交接和Git检查点。REVIEW是提交验收准备，不表示已有独立人员审查。

## 维护图的方式

- 模块名、角色、状态、源码和允许依赖维护于`project/modules.json`。
- 有意设计的布局/说明维护于`tools/render_architecture.py`；业务图不机械画成文件树。
- 运行`python tools/render_architecture.py`生成SVG、Mermaid及HTML。修改图形后渲染检查文字、连线和边界，不能只凭生成成功。
- `python tools/project.py check`验证图与登记/生成源一致；生产依赖变化会要求同步布局，避免图看起来漂亮却失真。

当前三图已在本机渲染并视觉核对。各图保留SVG原图和Mermaid文本，便于编辑和在报告/讨论中复用。详尽模型假设仍以[工程契约](../engineering.md)为准，任务规则见[治理说明](../governance.md)。
