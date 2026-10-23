# 作业二操作说明

共用根[治理规范](../../docs/governance.md)。所有示例从仓库根执行；若终端位于Work2，先 `Set-Location 'E:/Work/火发原理'`。不要把Work2传成 `project.py --root`，它不是独立仓库。

## 查看、领取、验收

```powershell
python tools/project.py doctor
python tools/project.py show WBASE-001
python tools/project.py task start WBASE-001 --actor YOUR-ACTOR --note "说明本轮要核验的问题"
```

WIP为1，依赖未完成不能开工；既有负责人不可静默替换。当前可领取项以[生成任务板](tasks.md)为准，示例ID不构成永久起点。

完成产物、来源/决策、handoff及taskshot后运行统一质量，再顺序提交机械验收：

```powershell
python tools/quality.py
python tools/project.py task submit WBASE-001 --actor YOUR-ACTOR --note "逐项说明产物与验收及限制" --evidence build/quality/latest.json
python tools/project.py task complete WBASE-001 --actor YOUR-ACTOR --note "说明证据覆盖和下游可用范围"
```

质量指纹包含可维护文档和原始资料；检查后再改有效文件会让证据过期。根/Work2的生成工作面、任务板、历史taskshot和验收快照排除自引用。REVIEW只表示提交验收准备，不代表另一个人完成科学审查。

新增任务使用根工具的 `add`，指定依赖、产物、验收和优先级；产物位于Work2就自动出现在本阶段任务板。契约修改用 `amend`，工作面背景用活动任务的 `context`；不要手改根tasks或四份生成视图。用 `python tools/project.py render` 恢复生成视图。

## 原件与归档

`python tools/work2_sources.py verify`检查9份原件的路径、大小和SHA256，统一质量亦执行该检查。初始capture只可执行一次；新增或修订资料必须用新日期身份和相应登记，不覆盖初始清单。Git按原字节保存原始启动词、inp等，避免换行转换破坏身份。

作业一采用[原址保留](../archive/work1/README.md)，[baseline快照](../archive/work1/baseline-20261023.json)列出162项固定交付和四项锚点。原图、课程资料、历史研究、交付包不属于临时清理对象。清理先运行根 `project.py inventory`，核对精确路径、引用和可再生性。

## 指定检索入口

```powershell
pwsh -NoProfile -File ./调研/scripts/research.ps1 -Topic 20261023_w2_methods_a -PromptFile ./Work2/research/prompts/20261023_w2_methods_a.txt -OutputDirectory ./Work2/research/search -CutoffDate 2026-10-23 -MaxCalls 3 -Brief -DryRun
```

新请求先使用唯一Topic和实际截止；核对DryRun未读凭据/未联网/未写结果，再执行去掉DryRun的同一命令。初始Topic已经尝试且失败，不覆盖其记录，重试另建后缀。MaxCalls只是提示目标。脚本保留默认根调研输出，新增OutputDirectory参数用于本阶段隔离。

有真实检索轨迹仍只代表找到线索；关键原文通过HTTP读取核验，并保存题名、版本、适用范围和定位。HTTP403、502或无轨迹返回如实记录，不能当已核来源。

2026-10-24脚本已兼容主机根、`/v1`或`/v1/responses`地址，固定只构造一次`/v1/responses`，不改凭据文件。研究请求可加`-RequireSearchTrace`：同时请求必需工具调用并在缺轨迹/正文时保存process_only且失败退出；路由不支持该选项时仍可用默认请求，但无轨迹内容不得升级为检索证据。HTTP失败仅保存脱敏状态，不回显地址/头/密钥。

新增原文通过根`tools/work2_research.py`保存并登记哈希/阅读范围，调查精选数据通过`tools/work2_survey_data.py`生成；[数据说明](../research/data/README.md)列出命令和身份层次。统一项目检查验证原件、引用、未知值和精选数据漂移；缺全文和挑战页保留而不伪装可用正文。

## 批次收尾

检查 `git diff --check`、完整diff、原件核验和 `python tools/project.py check --staged`，只暂存本批审阅的完整文件，建立本地提交。原始资料本批首次纳入Git；用户已有的无关解压目录保持原样，不用 `git add -A`混入。不自动推送、发布或上传。
