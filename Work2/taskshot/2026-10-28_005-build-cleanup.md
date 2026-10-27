# 005 · 未引用构建产物清理与工作区证据盘点

日期2026-10-28，任务WGOV-001（负责人devin）。用户决定只清未引用的build候选、用户材料仅出证据清单不代删、清理走受治理任务；删除清单经用户在对话中逐项展示后确认继续。起始分支codex/work2、HEAD 7a3774b；工作树原有用户未跟踪目录`deliverables/第五组_第一次大作业_分工更新版_20261020/`保持原样未纳入。

## 实际执行与边界

先以只读扫描（`build/work2/cleanup_plan_scan.py`）对5339份文本核对引用：覆盖results归档清单、docs/taskshot、Work2、project、tools、tests、scripts、cases、data、.github、.githooks、调研及根级文档；另核对`build/<cfg>/latest.json`指针与RUNNING标记。散落目录加做裸名二遍核对，`build/delivery-course-20261020`与`build/test-tmp`被救回保留集。扫描全文与判定依据写入`Work2/results/cleanup_v1/manifest.json`。

执行删除76项候选中的73项：`build/artifacts/`下41个未引用debug构建、14个未引用release构建及3个空残留，加15个未引用作业一scratch目录（ppt-final、ppt-tables-20261016、live-panel-skill-reference、template-*、tpl-review、gui-dev、gui-probe、submission-20261020-v2-checks、blue-template-review、liquid-hp-rya4q73l、presentation-enrichment-20261015）。释放约1.43 GB，build/由约3.0 GB降至1.60 GB。`build/.cmake`、`build/CMakeFiles`、`build/Testing`三项删除后被当日验证构建/VSCode CMake查询重新生成（约0.5 MB，工具副产物），如实记入manifest而非重复追删。

首次删除在`live-panel-skill-reference`内`.git`只读pack文件上遇WinError 5；为清除只读属性后重试的处理（onexc回调）修正，脚本幂等重跑完成，事实保留于此。

被引用构建（36个，results归档manifest/taskshot引用及latest指针）、保留散落目录25个（含救回2项）经脚本逐项核对零缺失。原始资料、冻结交付、`调研/`、`taskshot/`、归档results、用户材料均未触碰；build/整体不进Git。

## 验证与证据

删除后重新构建并测试证明可再生：Debug构建PASS 6ae73d85，测试PASS 2e9c0672（250 core+41 adapters+8978 thermo+3948 combustion+505 cycle检查、50组CLI、零失败）；Release构建PASS 33be5856，测试PASS eb88213a同口径零失败。最终`python tools/quality.py`六组PASS（project/governance/debug/release/runner/handoff），报告`build/quality/latest.json`。

用户材料证据清单`user-materials-evidence.md`记录：四个交付zip哈希互不相同（版本差异而非机械重复，现行版为v3分工更新版）、PPT/PPT/嵌套约549 MB疑似解包多套一层、`代码.zip`被.gitignore显式排除、deliverables顶层作业一过程稿建议作历史保留。这些条目均未执行删除，决定权在用户。

## 范围说明与下一步

本批是工作区盘点与可再生产物清理，不构成科学验证或基线审查；WBASE-001数值审查、U-015补核均不受本批影响。任务经ACTIVE→REVIEW→DONE，验收快照见project/evidence登记。清理脚本留存于build/work2/（可再生，不进Git）。

按规则审查暂存区后建立本地检查点；不推送、不发布、不外发。
