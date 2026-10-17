# 067：最终交付汇总与复现包

日期：2026-10-18。目标：把课程报告、答辩稿、C17/CLI、GUI 和接收复验入口集中到一份交付清单，保留研究边界和剩余工作。

## 已固定产物

- `deliverables/report_typst_v1/report-final.pdf`：20页 A4 课程报告；Typst 源码、模板说明、科研图源、动态架构页和 GUI 页面图同目录保存。
- `deliverables/presentation-final/两型火箭动力系统_答辩终稿.pptx`：17页 16:9 答辩稿；动态架构、GUI 页面、结果表和参考文献已纳入。
- C17核心、CLI和 GUI 源码已登记；第三方 webview 0.12.0 与 WebView2 SDK 头文件、许可和哈希已登记。
- `build/quality/latest.json`：project、governance、Debug、Release、runner、handoff 六组 PASS；Release 步骤同时执行 GUI Release 构建和 `tests/test_gui.py`。
- `deliverables/FINAL-DELIVERY.md`：最终文件、复现命令、许可、研究边界、GUI/C体系后续工作和校验值入口。

## GUI核验

`python tools/gui_build.py --dist` 生成便携目录，`python tests/test_gui.py` 9项通过，覆盖四个功能模块的 C 桥接、CLI 数值一致性、循环输入导出复算、非法 JSON、重复键和非整数扫描点数。浏览器预览已检查循环开式/补燃拓扑、输入修改后的结果刷新和连续切换竞态。

桌面 exe 已在本机启动并保持响应；本次自动采集得到的屏幕图像被其他前台窗口遮挡，未将其作为原生窗口截图证据。最终交接仍需在可控桌面环境保存一张原生窗口截图，并注明窗口尺寸、系统 WebView2 Runtime 和 GUI 包哈希。

## 交付包

交付包必须在干净本地提交上生成：

```powershell
python tools/delivery.py create --destination build/delivery-final
python tools/delivery.py verify --directory build/delivery-final
```

包内记录固定提交、质量报告、Release 构建身份、源码重建 CTest、成功/拒绝演示、输入与输出哈希；GUI 便携包另记录 exe、循环案例和界面层许可。不要把 `build/` 临时文件当作源码交付，也不要推送远端。

## 研究边界

报告中的两型对象、C算例和循环结果按各自来源、研究输入和模型条件解释。未公开的真实发动机参数没有补造；模型未覆盖液相供给闭合、泵图谱、喷注、完整冷却、流动分离、瞬态控制和寿命。GUI 用于展示和复核操作，科学结论仍以保存的 C 计算归档和报告口径为准。
