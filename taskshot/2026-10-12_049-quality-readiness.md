# QA-002：汇报前质量整改

日期：2026-10-12（北京时间）。用户授权集中解决代码、研究表述、交付和整体质量问题；最终稿/PPT暂不确定，具名贡献不代填，外部推送未执行。

## 已修复与复现

- `gamma→1` 时原面积反解发生相减消去；新增解析极限回归后改用 `expm1/log1p` 与对数比。
- 冻结喷管域评估原先把负背压改成真空再处理，返回了错误分类；现提前拒绝负值/NaN并保持输出。
- 域评估JSON原先接受NaN、未知枚举和非法可用标记；现先校验全部诊断字段，失败不写半份JSON。
- 液态交互原先在附着求解处终止，无法进入过膨胀诊断，并重复求喷管；现只求HP一次，再走共用喷管/诊断路径。
- 菜单超长输入原先拆成多轮，浮点转整型也可能越范围；现整行排空，先检查0..7再转换，取消只接受完整q/Q。
- 报告与展示草稿纠正算法、10种物性/9种平衡组分、版本、吨力、O/F条件、验证差值范围和海平面L0假设；更新现行入口的过时“未开始/煤油未选定”状态。历史原始资料、taskshot和参考归档未改写。

## 验证证据

- 完整六组质量 `build/quality/latest.json` PASS，结束2026-10-11T19:43:46Z；输入指纹 `23456f7156edc05733ef249fb50da83c71d18818e2dad5406c43b210f0ae550f`。
- Debug/Release：core250、adapters41、thermo8978、combustion3922、cycle353断言；CLI45组。参数17、物性26、CEA16、循环参考13组执行通过，数量不代表独立实验工况。
- 当前Release构建身份 `39d2e5e1735c4d1e938dc4e27100c3da`；使用不可变目录里的exe，便捷路径只作别名。
- `build/qa002/analyzer-v1/analysis.json`：GCC14.2.0 `-fanalyzer` 与严格警告对登记的28个生产C源文件PASS；不代替运行时sanitizer或科学审查。
- `build/qa002/benchmark-v2/benchmark.json`：旧提交 `5d95c1e` 与当前源在同GCC/-O2下，9组交替、每组2000次固定A10/A40冻结求解。CPU中位时间0.159→0.085 s（本机下降46.54%），所有累计推力校验值360319492.45191073 N；只覆盖此基准。第一次脚本漏内部头文件的失败编译日志保留在benchmark-v1。
- `build/qa002/demo-preflight/`：隔离PATH下11项当前交付演示通过；交接14项测试PASS。旧 `build/delivery-imp002-20261007` 用当前校验器通过，固定提交仍为27e29fac，不更新旧包。
- `build/qa002/assignment.png`：sharp渲染当前SVG并实际查看，文字无裁切或重叠；报告草稿/PPT状态与实际一致。

## 复跑

```powershell
python tools/quality.py
python tools/static_analysis.py --destination build/qa002/analyzer-NEW
python tools/benchmark_frozen.py --destination build/qa002/benchmark-NEW --baseline 5d95c1e --samples 9
python tools/delivery.py create --destination build/delivery-qa002-20261012
python tools/delivery.py verify --directory build/delivery-qa002-20261012
```

新阶段包基于代码/文档检查点生成；最终固定提交、纯C重建与打包验收结果将在以下追加，不能提前称其为课程最终四项交付。当前仍缺真实组员贡献、最终稿/PPT/演练，以及真实型号输入和整机/实验参考；这些缺口不伪装为软件待实现功能。

## 本地阶段包最终验收

- 最终包：`build/delivery-qa002-20261012/`，协议v2，status PASS，校验命令 `python tools/delivery.py verify --directory build/delivery-qa002-20261012` 通过。
- 固定源码提交：`a31465f4bc1ad0b65bcc3c829a4168f7cf222d9d`；质量指纹 `9434344ab543107db12c6fb17699d859d48b214456d093406c166bf1139be096`。包生成和校验时仓库干净，包后只有本快照/任务状态记录。
- C源码ZIP 87文件、220349字节，SHA256 `83a21f0346ca562dac00f4ea93e423f4fbde591b304db2e19d8a7b383311b3cb`；Windows x64 ZIP 77文件、241247字节，SHA256 `bec665a8dabea85e02722501ed2f85616eae99aad24603910419ce260064e69d`。
- Windows程序SHA256 `0c9a93c75713e31559d7cc9175e6d89a81a0c7ade65faad4e3d502dc9f13a807`；隔离PATH下DLL仅系统库。源码包在解压目录独立配置/构建并执行纯C CTest 5/5；源码和运行包各11项演示通过，菜单列出的六个输入均已包含。
- 本轮没有远端同步、Release发布或最终课程发布。正式任务仍需真实组员贡献确认、报告/PPT定稿与排练；本地阶段包不替代课程四项交付。
