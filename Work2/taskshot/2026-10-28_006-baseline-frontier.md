# 006：C基线分层审查与定向前沿核读

2026-10-28，codex，WBASE-001。本批在用户确认“开始全面工作”后领取；用户额外强调前沿知识获取。submit与commit前分别确认仍有效，未据开工授权提前验收或提交。

## 实质产物

- [语义审查](../research/baseline-validation-v1.md)、[事前协议与偏离](../research/baseline-protocol-v1.md)、[前沿核读](../research/frontier-review-20261028.md)。
- [选定清单](../results/baseline_v1/selection-manifest.json)固定956文件：主运行a、层级c、两个失败驱动尝试、原异常报告/哈希和实际研究工具源码快照；可执行文件留build。
- 主矩阵84项逐一比较原始/整数插桩构建，67成功/17预期拒绝，全部一致；54独立实现比较状态过门槛，最大组分差8.11e-11以内、HP温差8.53e-7 K以内。另13层级参考、3CLI拒绝通过。
- 中心HP旧字段末次TP=1步，全程Newton=201步、TP调用11次；累计评估/回溯/冷热路径保留，未把研究插桩当生产API能力。未改生产src/include、未放宽C数值阈值。
- 两份独立Debug共60次循环新进程各505项通过；U-015未定位。发现原异常85a23407构建已被WGOV清单删除，无法精确重跑；失败报告、旧1+10次复跑、原哈希复制留证，未改历史清理清单。

## 研究和失败事实

Grok Topic a先DryRun后502，保留脱敏失败；Topic b先DryRun后7条工具轨迹（MaxCalls4不是硬限制）。HTTP新增W2-F01–07，6份可得，非6篇独立论文；JCP出版者403仍保留，作者开放稿34页读选定页并渲染3/25页。核FastChem4 v1§2.1–2.3、CT v1相关方法、JCP2025的稀水溶液/初始化与失败分母。纠正摘要混入N2/Ar和“直接适用HP”等表述。主索引75条、67条可核字节；首轮46条成员不变。

层级驱动a因误读trace=1e-7为1e-8被拒绝；驱动b因把C状态枚举当CLI退出码而失败；按原卡/源码契约修正后用新RunId c通过。前两次失败档案纳入selected，不覆盖。没有AI训练、GPU、大扫描、整库移植或新算法提速声明。

## 验证和剩余边界

第一份新Debug流水线通过：core250、adapters41、thermo8978、combustion3948、cycle505、CLI50组及其余数据/参考检查。新增7个证据校验测试已执行通过：真实档案、字节变化、重新哈希的破坏守恒状态、伪独立参考、累计重置、测试指纹和前沿成员一致性。

统一质量报告固定入口`build/quality/latest.json`，实际完成事实在下方补记；质量通过不替代独立科学审查。未触发暖启动失败冷回退，完整Jacobian/初值条件性、生产失败累计诊断、最新软件版本/2020 ODML及同批型号输入仍需后续契约。U-015不因复跑成功而关闭。

已维护来源/决策/U-013/015及新增U-018/019、交接和导航。选定档案按字节保护、有效研究文档可维护；pipeline测试指纹包含Work2新档案/检查器。未删除用户材料、未外发、未推送、未派生子agent。

## 统一质量与确认点

产物落定后运行根统一质量入口；在实际报告完成前不提前写PASS。当前验收/提交事实以任务登记及后续补记为准。

北京时间2026-10-28 02:34:15–02:41:20，`python tools/quality.py`实际完成：project、governance、debug、release（含GUI构建/测试）、runner、handoff六组PASS，报告`build/quality/latest.json`；输入指纹`de876ca7d8ffa7fd08c9a76776012ce801577ce93e4ff771eb92c86febd230f7`。本段仅补历史taskshot，按既有自引用排除规则不改变质量输入。质量不是独立科学审阅。

工作树初审与`git diff --check`通过，src/include无生产变更，暂存区为空，既有用户交付目录未混入。WBASE保持ACTIVE，等待用户submit前确认；尚未执行submit/complete、暂存或commit。commit前还需按用户要求审暂存区并单独确认，不推送。

用户随后回复“可以吧”，确认submit→complete；已按工具完成首轮流转并保存验收快照。暂存预检发现baseline_v1尚未在.gitattributes声明字节保留，可能在检出时换行转换破坏哈希，因此通过工具重开/重新领取，补`-text`规则、真实Git clean过滤的混合换行回归及规则测试指纹。保持选定956文件和计算结果不变，另跑完整质量再按既有确认重新验收；commit前仍单独确认。工作面阶段也改为不依赖瞬时确认状态的说明。

补核确认选定档案有16个含原始CRLF的文件，包含CEA输出/旧异常复跑记录。8项档案回归实际通过；北京时间2026-10-28 02:58:50–03:07:59第二轮统一质量六组PASS（含GUI），新指纹`bf291b659cf24d59afff02074abf689db3aca24d726263ccb5abedb8ddf24bc7`。随后按已获用户确认重新submit→complete，WBASE为DONE、WREF解锁；有效验收快照为[WBASE证据](../../project/evidence/WBASE-001_75e4166bb791.json)。首轮快照保留为历史，不替代本次新证据。

进入本地提交前暂存审查；提交说明已准备为`feat(research): validate Work2 C baseline and record frontier methods`，附`Generated with codex`。Git commit仍待用户单独确认，不外部推送。
