# 用户材料证据清单（只读，不代替删除决定）

2026-10-28 WGOV-001 盘点。以下条目均为用户自有材料或冻结历史，本任务不执行任何删除；逐项列出事实供用户决定。哈希获取日期 2026-10-28。

## 一、deliverables/ 四个交付 zip（版本互不相同）

| 文件 | 大小(字节) | SHA256 |
|---|---|---|
| `deliverables/第五组_第一次大作业_20261020.zip` | 13,811,743 | DE4F0806B21D4EB1D051B487A22ED517BBDA5A61E80CAEC273212F23C3FFD387 |
| `deliverables/第五组_第一次大作业_修订版_20261020.zip` | 11,977,515 | 2E025E0227A04A9499F9EB2F8F5A7E7004832CFCCECD28673BF08FF39759BBA0 |
| `deliverables/第五组_第一次大作业_分工更新版_20261020.zip` | 11,977,891 | C6A29A5F411E10772A9D033845AC352819FC1E873A66EA2B1C3891BD56BCE013 |
| `deliverables/第五组_第一次大作业_分工更新版_20261020/第五组_第一次大作业.zip`（未跟踪目录内） | 11,982,802 | 3F54D15C251E2A272E6B57E58659AB61F4F54B2FAFC028967BBD0E82B1F9B3E1 |

- 四个哈希互不相同：不是机械重复，是四个不同版本，不能按"重复文件"自动删。
- 现行版本依据：`deliverables/README.md` 指向 v3 分工更新版（`submission-20261020-v3/`）。
- 未跟踪目录 `deliverables/第五组_第一次大作业_分工更新版_20261020/` 内含一个解压目录 `第五组_第一次大作业/` 和上述第四个 zip；Git 状态为未跟踪，不属于任何任务产物。
- 待用户决定：旧 zip 保留几个、未跟踪目录是纳入管理/删除/保持原样。

## 二、PPT/ 模板库（872 MB 自有材料）

- `PPT/PPT/【第2步】PPT模板文件（真正使用）/` 嵌套层占约 549 MB，疑似解包多套一层；顶层另有 6 个散文件（含 16.9 MB 模板-31.pptx）与 `PPT/主图PPT/` 子目录。
- 待用户决定：扁平化嵌套、按模板编号去重、或保持原样。此项不在工程清理范围。

## 三、根目录散件

| 文件 | 事实 |
|---|---|
| `代码.zip`（519,776 B） | `.gitignore` 第29行显式排除，按排除意图保留，不处理 |
| `第2章推力室和发动机的主要参数20260911.pptx`（19.7 MB） | 课程材料原件，保留 |

## 四、deliverables/ 顶层作业一过程稿（冻结历史）

`START-HERE.md`、`URGENT-TODO.md`、`SOLO-EXECUTION-PLAN.md`、`PREPARATION-SUMMARY.md`、`FINAL-CHECKLIST.md`、四版 defense-script、`ppt-plan-solo.md`、`ppt-making-final.md`（45.7 KB）、`ppt-quickstart.md`、`report.md` 等为作业一制作过程稿，属历史快照性质：建议保留原字节不改写；导航已由 `deliverables/README.md` 收编。若用户认为属冗余可另行决定删除，需连同 README 链接一并处理。

## 五、明确保留区（无需决定）

- `调研/`（92.5 MB，含 44 MB `O07_pyskyfire_validation.txt` 原文快照）：作业一原始证据，受保护。
- `taskshot/`、`docs/` 历史文档、`results/validation`、`results/research`：归档证据，按原址保留。
- `Work2/` 全部：当前阶段工作区，目录职责在 project-map 中登记，无冗余。

清理执行记录与保留/删除判定依据见同目录 `manifest.json`。
