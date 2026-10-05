# 连续液体入口 HP 与固定面积喷管

日期：2026-10-05；任务 ANA-010；Windows 本机；未调用 WSL、浏览器 UI 或子agent；PPT/最终报告继续后置，不推送远端。

## 实际产出

- 新增 `RpContinuousLiquidFeed`、连续入口状态、HP结果和固定面积喷管结果接口。核心计算保持 C17：查表化学焓与 C/H/O 元素库存 → 九气相绝热 HP → 已有燃烧室冻结的固定喉面积喷管。
- 连续入口只接受登记的数据集、焓基准和单相液体域。密度保留 EOS 质量口径；化学焓、O/F 和元素库存使用声明的 CEA 质量口径。内部库存归一化显式拒绝上溢和下溢。
- CLI 新增 `hp-liquid-state` 与 `frozen-liquid-state`，成功结果输出边界、诊断、喷管和几何关系；错误使用非零退出和 stderr，后续失败不覆盖调用方输出。
- `results/validation/liquid_combustion_v1/manifest.json` 保存47次 C 运行（29成功、18预期拒绝）与18次显式 J/mol 化学焓 CEA 对照。归档同时保存构建、测试、源码、CEA卡、stdout/stderr和文件哈希；`python tools/liquid_combustion.py verify results/validation/liquid_combustion_v1` 通过。

## 基线和研究解释

固定研究假设：Pc=10 MPa、At=0.01 m²、真空、面积比10、O/F=3.4、CH₄=120 K、O₂=100 K、两路入口压力10 MPa。结果为室温约3602.756 K、c*约1811.000 m/s、质量流量约55.218125 kg/s、推力约173.721212 kN、比冲约320.811939 s。

将两路入口升温到 CH₄=140 K、O₂=110 K，固定几何下比冲约增加0.280323 s，但推力约减少9.718 N；这只是小范围、受限模型的条件响应，不是“预热提高推力”的结论。面积比、喉面积和背压关系只说明理想几何模型的代数变化，不能推出硬件质量、分离、侧载、冷却裕度或寿命。

## 质量证据

- `python tools/quality.py`：六组检查全部 PASS，报告输入指纹为 `625eefa0da7d417847f4a1ec8bd9e3723aeb3cb590d3c63c0c6a0f533ce4aa50`，报告 SHA256 为 `ed63563244b4aacc84a02860d4bab0f0e31cb39ce3ecab303c692c407e045d7c`。
- Windows 独立 CMake/Ninja Release 构建 CTest：6/6 通过；日志 SHA256 为 `3fea6b1e392c84ba4c74a79574bb0a2b74bd69fcfeaf744a8b0ab9d4c0330967`。
- GCC14.2.0 使用 `-std=c17 -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -fno-common -Werror -fanalyzer -O0` 编译21份登记生产 C 源，零诊断；清单 SHA256 为 `de750b45b5e6fc444f4a13da210c80d457386843b23c815aba1f267190138dda`。
- 架构总览、业务、组件和任务四张 SVG 已用本机 Bundled sharp 渲染为 PNG 并逐图查看，文字、连线和边界没有发现裁切或遮挡。

## 审阅边界

这不是真实发动机或独立实验验证。入口温压是研究假设，产品压力只作为理想气体燃烧室压力；没有泵升压路径、喷注压差、闪蒸/两相、煤油、凝聚相/积碳、电离、冷却、分离、轴功、分流和完整循环闭合。CEA 对照与 C 使用同一物性来源和受限物种集合，属于软件方法对照，不是实验。

两型实际型号、批次、级段和工况仍按参数台账单独核验；不得用本算例填补朱雀三号或长征十号乙缺失参数。后续优先工作是泵后入口边界、煤油物性/批次证据和完整循环的可验证边界，而不是继续扩展无来源的温压扫描。

## 验收与接续

ANA-010 已完成，验收快照为 `project/evidence/ANA-010_651a74f4cc72.json`，SHA256 为 `ed63563244b4aacc84a02860d4bab0f0e31cb39ce3ecab303c692c407e045d7c`。补齐审阅/交接文档后重新运行完整质量，不沿用补记之前的报告。首轮静态分析漏加 `src/adapters` 搜索路径，CLI 编译因找不到内部头文件停止；加入与构建一致的头文件搜索路径后，全部21份生产源重新分析通过。前次尝试未删除，也不将它报告为算法缺陷。

后续登记 ANA-011，将两型一二级的已保存证据、已有 C 算例和必要输入缺口合并为可审阅研究落点；明确不直接启动 PPT/最终报告。本轮盘点不删除原始资料、旧档案和构建；只提交已审阅的本地成果。
