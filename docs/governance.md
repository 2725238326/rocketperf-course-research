# 工程治理：任务、文档、Git与目录

本轮改造将“约定”落实为可执行检查。机械检查仍不替代科学判断、真实参数核验或独立人员审查。

## 1. 唯一来源与派生视图

| 内容 | 唯一维护位置 | 生成/引用位置 |
|---|---|---|
| 任务状态、依赖、负责人、产物、验收、事件 | `project/tasks.json`，通过工具变更 | `worknow.md`、`docs/tasks.md`自动生成 |
| 生产模块、源码清单、允许依赖、维护角色 | `project/modules.json` | GCC和CMake构建清单、架构图、边界检查 |
| 文档职责、目录分类、WIP/Git约束 | `project/policy.json` | 项目检查和提交检查 |
| 接手叙述、已知风险和方法 | `handoff.md` | 链接当前状态，不复制实时状态表 |
| 历史执行事实 | `taskshot/` | 当前任务引用，不覆盖旧快照 |
| 老师要求和研究证据 | `作业要求/`、`调研/` | 研究报告/参数库引用，原始文件保持不变 |

机器生成文件的顶部有GENERATED标记。手工改它们会被检查判定为漂移；应改任务契约或模块登记，再重新生成。

## 2. 一项任务的完整周期

先查看契约：

```powershell
python tools/project.py show RES-001
python tools/project.py task start RES-001 --actor root --note "本轮核对型号版本与影响计算的参数缺口"
```

领取必须满足依赖、READY状态和WIP上限；默认同时仅一项ACTIVE/REVIEW。不同负责人不能静默修改正在执行的任务。组员并列研究可在确认协作方式后调整WIP，但不等于授权agent自动派生其他agent。

有产物后运行质量入口，再提交机械验收：

```powershell
python tools/quality.py
python tools/project.py task submit RES-001 --actor root --note "逐项解释验收标准与产物对应" --evidence build/quality/latest.json
python tools/project.py task complete RES-001 --actor root --note "验收完成；说明遗留限制及下游可用范围"
```

submit检查产物非空、完整PASS质量报告、输入指纹和状态，复制一份不可变验收快照到`project/evidence/`。complete再检查证据新鲜度，防止测试后修改代码/文档却沿用旧PASS。REVIEW表示已提交验收准备，**并不声称另一个人已独立审查**；负责人仍须解释验收内容。

任务状态和事件链一起原子写入；OS文件锁防止并发覆盖，进程退出自动释放锁。事件哈希链用于发现意外重写，不是数字签名或对抗仓库管理员的安全机制。生成视图若中途写入失败，用render恢复；不要重复执行已经成功登记的状态变更。

### 阻塞、转交、重开

```powershell
python tools/project.py task block RES-001 --actor root --note "原因：缺少某原文；解除条件：取得原文或明确替代方案"
python tools/project.py task handoff RES-001 --actor root --to maintainer --note "交代已查来源及剩余问题"
python tools/project.py task unblock RES-001 --actor maintainer --note "解除条件已满足，重新检查依赖"
```

unblock回到READY或PLANNED，不自动开工。REVIEW重开回ACTIVE；DONE重开会撤销尚未启动的下游READY。若已有下游执行/完成依赖，则拒绝破坏依赖关系，应先明确重规划，而不是改状态绕过检查。

新任务使用`add ID --title ... --actor ... --depends ... --artifact ... --acceptance ...`；artifact/acceptance可重复传入。任务不能没有可交付物或验收条件。取消必须说明原因，后续依赖不会被假装完成。

修改任务契约用`amend ID --actor ... --note ...`，再传需要替换的title/depends/artifact/acceptance/priority；重复列表参数表示完整替换该列表。before/after进入事件链。REVIEW/DONE契约被冻结，必须先重开，不能在验收后悄悄降低标准。

## 3. 质量入口与证明范围

`python tools/quality.py`顺序执行：

1. 状态/事件链、派生文档/架构漂移、文档链接、目录归属、秘密模式、源码依赖和原始证据哈希。
2. 治理行为测试：非法流转、循环依赖、WIP、负责人、锁、证据缺失/过期、状态篡改等。
3. GCC Debug核心和CLI测试。
4. GCC Release核心和CLI测试。
5. 运行管理测试：协议、输入对应、失败/超时/启动错误、旧通过状态、重复RunId和快照完整性。

每次先写RUNNING，结束写PASS或FAIL，保留日志。未执行检查不算PASS。质量指纹覆盖实现、工具、治理策略、有效文档和原始档案；动态任务状态、生成任务视图、历史快照和验收快照排除，以避免报告引用自身。原始来源另有对历史索引的完整哈希检查，验收后改变档案字节同样会令证据过期。

本轮已额外执行Windows CMake 3.31.10/Ninja 1.13.2构建及CTest；远端CI与Linux sanitizer未执行。配置存在不代表已经验证。

## 4. 构建、测试和运行记录

GCC和CMake共同读取模块登记的C源码清单，避免两套构建漏编不同模块。PowerShell脚本保留兼容入口，行为由Python标准库工具统一维护。

- 每次构建产生`build/artifacts/<配置>/<build-id>/`，保留日志和RUNNING/PASS/FAIL清单。
- `build/<配置>/latest.json`指向**最后一次尝试**，失败不会退回旧成功假装本次通过。
- 同配置构建使用OS锁；发布前检查编译期间源码没有变化。旧产物保留用于追溯。
- 稳定路径下的exe仅是兼容别名；正式运行工具从manifest找到并核验具体构建。
- 测试报告始终记录成功/失败；使用前核对构建和测试输入指纹。
- 运行原子占用RunId；缺少新鲜已测试构建时默认构建并测试，`--no-build`则拒绝。
- 只有退出成功、stderr符合约定、结果schema/数值/来源/输入对应一致时才保存成功result.json；任何准备、启动、超时或校验失败都保留FAILED运行清单。

## 5. Git的本地工作方式

已有基线提交`cc6428b`记录治理改造前的可运行基础。本轮在`work/gov-001-governance`工作分支上迭代，完成后形成独立治理提交。实时分支/提交/脏状态用`python tools/project.py doctor`查看，文档不硬编码“没有提交”等容易过期的事实。

建议以任务为单位创建分支、审查变更、运行质量入口，再做本地提交。不要用`git add`替代审查，也不把local commit说成已推送或已合并。

`.githooks/pre-commit`通过`git config --local core.hooksPath .githooks`启用，检查：

- 暂存区潜在凭据（只报告文件，不打印值）；生成产物；超限新增大文件。
- 原始档案的修改/删除；新增日期版本允许，旧原文不静默改写。来源索引本身允许正常增补。
- 部分暂存文件被拒绝，防止检查工作树、提交另一套字节；需要拆提交时先把完整可审查变更分组。
- 项目登记、文档和架构当前仍一致。

hooks是本地护栏，克隆后需启用；CI再次执行质量检查，不能把本地hook当不可绕过的安全边界。未获授权不添加远端、不推送、不发布。恢复历史优先对比/还原明确文件或通过新提交回退，不使用破坏性reset清除工作。

## 6. 目录与文档生命周期

活跃工程目录由policy分类；新根目录需说明职责并登记。物理公式/契约、操作指令、历史记录和原始证据各有位置，不全部堆到README。

文档分为规范、操作指南、研究结论、历史快照和生成视图。规范修改说明兼容性影响；研究结论带证据截止；历史快照不伪造新鲜度；生成视图只能由登记重新生成。

原始课件/照片/论文和历史证据保留原路径，已有链接不因“整理目录”失效。新专题归入`调研/专题/`。44MB的已有交互HTML属于历史档案，保留但不当普通源码频繁读取；新增超25MB资料需先作存储方案决定，避免悄悄扩大Git历史。

`build/`、`results/local/`、`project/.locks/`与Python缓存均不纳入版本记录；正式研究结果选定后连同输入/验证说明独立归档。清理时只处理明确的可再生产物，不能递归删除项目根或原始资料。

`python tools/project.py inventory`给出目录计数、体积、大文件和非当前构建的清理候选。它不执行删除；当前构建指针和RUNNING产物受到排除保护，清理前仍须确认引用、保留需要的证据及精确目标。

## 7. 迭代设计的规则

改动模块边界先修改module登记及相关契约，再更新架构布局并视觉核对；质量检查会识别未登记源码、禁止依赖或图源漂移。新增功能先定义失败语义和验收，再实现和验证。

不要求一次把未知真实发动机模型做完。当前治理与教学基线可使用，热化学、循环、参数证据仍按研究任务推进。维护设计质量的标准是边界、证据和验证持续一致，而不是目录或模式数量。
