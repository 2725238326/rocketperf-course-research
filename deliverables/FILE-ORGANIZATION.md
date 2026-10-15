# 项目文件快速整顿清单

## 当前散乱文件
```
./deliverables/ppt1_draft.pptx    ← 旧草稿,已有正式版
./PPT/终版ppt.pptx                 ← 可能是参考模板
./代码.zip                         ← 组员交付,已审阅
./第2章推力室和发动机的主要参数20260911.pptx  ← 课件
```

---

## 🟢 保留不动(重要文件)
- `deliverables/` 下所有.md和demo/
- `docs/` 下所有架构文档和研究报告
- `src/` `include/` 源码
- `build/release/rocketperf.exe` 已编译程序
- `project/` `tools/` 治理和工具
- `PPT/PPT/【第2步】PPT模板文件(真正使用)/` 模板库
- `调研/原始来源/` 受保护资料

---

## 🟡 整理到archive/(5分钟)

```bash
# 创建归档目录
mkdir -p archive/old-drafts
mkdir -p archive/reference-materials

# 移动旧文件
mv deliverables/ppt1_draft.pptx archive/old-drafts/
mv 第2章推力室和发动机的主要参数20260911.pptx archive/reference-materials/

# 组员代码已审阅,保留原件
# (已在 调研/原始来源/20261013_classmate_code/)
```

---

## 🔵 deliverables/下只保留最终交付

### 当前deliverables/(22个文件)
```
核心交付:
- report.md                    ← 报告正文
- defense-script.md            ← 最终讲稿
- ppt-structure.md             ← 逐页制作指南
- demo/index.html              ← 演示页(710KB)
- ppt-materials/               ← 图表数据

答辩准备(新增):
- EMERGENCY-QA.md              ← 问答速查卡
- PPT-SPLIT-WORK.md            ← 分工制作指令
- CODE-QUICK-OPT.md            ← 代码优化清单
- TIMELINE-URGENT.md           ← 时间表

辅助文档:
- FINAL-CHECKLIST.md           ← 检查清单
- START-HERE.md                ← 一页纸启动
- presentation.md              ← 讲解思路
- timing-chart.md              ← 时间预算
- defense-qa-card.md           ← 原问答卡
- demo-choreography.md         ← 演示编排

备用(可选):
- SOLO-EXECUTION-PLAN.md       ← 单人答辩方案
- defense-script-solo.md
- defense-cheatsheet-solo.md
- software-optimization-plan.md
- diagrams-guide.md
- URGENT-TODO.md
- PREPARATION-SUMMARY.md
- contributions.md             ← 真实贡献待填
- README.md                    ← 入口索引
```

### 建议操作: 无需删减
所有文件都有用途,保持原样。

---

## 🔴 根目录整顿(可选,5分钟)

### 如果想保持根目录干净:
```bash
# 只在根目录保留
README.md          ← 项目入口
AGENTS.md          ← 协作规则(已存在)
worknow.md         ← 工作面(已存在)
rules.md           ← 执行规则(已存在)
handoff.md         ← 交接说明(已存在)

# 源码和构建
src/ include/ build/ cases/

# 文档和交付
docs/ deliverables/ 调研/ PPT/

# 治理和工具
project/ tools/ .github/

# 配置
.gitignore .git/ .claude/
```

### 不要删除的
- `代码.zip` (组员交付原件,虽然已解包到调研/)
- `taskshot/` (历史快照)
- `results/` (研究归档)

---

## 🟢 答辩前不做大整理

**原因**:
1. 时间紧,优先答辩准备
2. 文件移动可能破坏相对路径
3. Git状态干净,无需整理

**答辩后再整理**:
- 删除重复文件
- 归档旧草稿
- 更新README索引

---

## 📂 快速文件查找(答辩时)

### PPT制作需要:
```
模板: PPT/PPT/【第2步】PPT模板文件(真正使用)/北京航空航天大学模板-31.pptx
指南: deliverables/PPT-SPLIT-WORK.md
曲线图: deliverables/ppt-materials/figures/*.png
架构图: docs/architecture/*.svg
数据: deliverables/ppt-materials/*.csv
```

### 答辩时需要:
```
演示页: deliverables/demo/index.html
问答卡: deliverables/EMERGENCY-QA.md (打印或手机)
讲稿: deliverables/defense-script.md
检查: deliverables/FINAL-CHECKLIST.md
```

### 代码演示需要:
```
程序: build/release/rocketperf.exe
算例: cases/vehicles/*.ini
交互: 直接运行 ./build/release/rocketperf.exe interactive
```

---

## 🎯 整顿优先级

**P0(现在就做,2分钟)**:
```bash
# 只做这个,确保文件不被误用
mv deliverables/ppt1_draft.pptx deliverables/.ppt1_draft_old.pptx
# (改名加点,隐藏,防止误编辑)
```

**P1(答辩前,5分钟)**:
```bash
# 创建最终交付文件夹
mkdir -p 答辩交付
cp deliverables/demo/index.html 答辩交付/
cp deliverables/EMERGENCY-QA.md 答辩交付/
# PPT完成后复制到这里
```

**P2(答辩后,30分钟)**:
- 归档旧文件到archive/
- 更新根目录README.md
- 清理.pptx草稿

---

## 立即执行(如果有5分钟)

```bash
# 1. 隐藏旧草稿
mv deliverables/ppt1_draft.pptx deliverables/.ppt1_draft_old.pptx

# 2. 创建答辩交付目录
mkdir -p 答辩交付
cp deliverables/demo/index.html 答辩交付/演示页.html
cp deliverables/EMERGENCY-QA.md 答辩交付/问答速查卡.md

# 3. 确认关键文件存在
ls -lh build/release/rocketperf.exe
ls deliverables/ppt-materials/figures/*.png
ls docs/architecture/*.svg

echo "✅ 整顿完成,可以开始做PPT"
```

---

**总结**: 
- 当前文件已经很整洁,无需大动
- 只隐藏旧草稿,创建交付目录
- 答辩前不动Git,不删文件
- 优先完成PPT和问答准备
