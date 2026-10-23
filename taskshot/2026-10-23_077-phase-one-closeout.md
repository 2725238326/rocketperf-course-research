# 077：第一阶段收官与文档入口整顿

日期：2026-10-23。任务：GOV-005。用户要求读取文档群，明确第一阶段已经收官。

## 范围与实况

接手HEAD为`e4d8ac3`，分支`research/audit`；已有未跟踪目录`deliverables/第五组_第一次大作业_分工更新版_20261020/`，保留原状，不纳入本次提交。读取工作面、规则、交接、治理、文档导航、任务契约、要求映射、项目说明、四级段/循环研究入口及074—076记录。运行doctor和只读inventory，未清理目录或原始资料。

## 文档与任务处理

- 根README、交付目录README、文档导航、交接和收官总览统一到v3冻结提交；交接原时间线及旧双人制作导航明确标为历史，旧排期不再决定当前工作。
- 要求映射、最终交付清单和项目简介修正“报告/PPT尚待制作”等旧状态。保留平台上传、演练、签收和GUI原生视觉的证据边界。
- 贡献表同步2026-10-20用户确认：纪博闻承担报告撰写、核心算法及程序集成，何明轩负责富氧补燃介绍与分析，宋俊辉负责结构整理与校对；未代签各组员。
- 项目规划/解读同步已有绝热循环、石墨活度守卫、HP Illinois割线与热启动；成对比较明确固定Pc/At下推力由CF决定。数值与C代码未改。
- 经project工具新增并领取GOV-005；取消已被后续产物替代的DOC-004及REL-001，事件说明取消不等于原契约验收。DOC-001保留原负责人buaabw及历史BLOCKED记录，GUI-001保留待补项，不替其他负责人流转或补签。清空旧接续顺序，阶段设为已收官、后续待定。

## 冻结包复核

只读脚本`build/phase-one-closeout/verify_submission.py`逐项校验v3 manifest的162项材料哈希，并校验ZIP大小、SHA256、CRC和对应条目字节，结果PASS；报告位于同目录`submission-check.json`。

- manifest SHA256：`1222a9980e6165c997104e8d874f453ff006b52d4fb4711f483cb9be54f28b2f`。
- ZIP SHA256：`c6a29a5f411e10772a9d033845ac352819fc1e873a66ea2b1c3891bd56bce013`；11,977,891字节。
- 固定源码：`3d4130c6db862c652bae7318cb85813ce0596d2e`；报告20页，PPT17页。
- 原manifest中的源码重建5项C测试、每构建17项CLI演示、GUI桥接及前端证据按其原范围使用；此次哈希复核不冒充重建或原生窗口验收。

v1/v2/v3包、报告源和PDF、PPT、课件、论文、原始网页及研究归档保持原字节。未修改模块登记，无需重生成架构；没有在线检索、浏览器操作、子agent、平台上传或外部推送。

统一质量第一次在project组停止：执行期间用户新增`Work2/`第二次大作业原始资料，该根目录未分类，且可见文件仍在整理。新增allowed_roots及archive_prefixes登记，并在项目地图说明其为待整理原始资料；不移动、改写、删除或暂存其中课件、图片、数据库压缩包和视频，不开启第二阶段分析。首次FAIL保留于`build/phase-one-closeout/quality-before-work2-registration.json`及对应project日志；登记完成后重新执行统一质量入口。

登记后曾完整六组PASS，随后发现交付目录README仍指向旧制作方案，补齐该入口并重新执行。该次六组检查均PASS，但用户在运行期间继续整理`Work2/`：移除嵌套目录层、调整文件清单并解压数据库资料，最终输入指纹变化，质量工具如实给出FAIL。此报告保留于`build/phase-one-closeout/quality-work2-changed.json`，不作为验收证据；待资料目录稳定后再次验收。本次助手未操作上述原始资料。

## 本轮验收

用户确认Work2整理完毕后，重新运行`python tools/quality.py`，最终六组全部PASS：project、governance、Debug、Release（含GUI构建与桥接）、runner、handoff；没有把前轮指纹失效的报告用于验收。最终报告位于`build/quality/latest.json`，验收快照由GOV-005登记引用。

已逐组审查文档、目录策略和任务事件变更，`git diff --cached --check`通过；仅暂存本轮文档、策略、生成任务视图、任务登记、质量快照及本记录。已有中文交付目录与Work2均保留未跟踪，不混入提交。GOV-005按ACTIVE→REVIEW→DONE完成语义说明及新鲜质量验收，并以`Close phase one and align current documentation`建立本地检查点；提交身份用`git log -1`查询，未推送。
