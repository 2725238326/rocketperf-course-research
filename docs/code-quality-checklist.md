# 代码质量与可读性检查指南

**日期**：2026-10-13  
**目的**：确保C核心代码满足工程标准、文档完整、单位明确、边界清晰  
**范围**：src/、include/下的计算核心与参数I/O

---

## 一、物理约束与假设

### 检查项 1.1：平衡求解边界

**文件**：`src/combustion/hp.c`  
**当前状态**：平衡求解正确，但边界条件说明不足

**检查内容**：
```c
// 需要补充的说明
// - 固定Pc/At的含义：给定主室压力和喉部面积
// - NASA9数据库覆盖范围：温度下限/上限、物种集合
// - 失败路径：当平衡不收敛时的处理（该拒绝还是降级？）
// - 单位基准：焓基准温度（298.15K）、压力基准（1 atm？）
```

**推荐改进**：
1. 在函数头注释中明确写出：
   ```
   /**
    * hp_equilibrium: 受限热力平衡求解
    * 
    * 物理约束：
    *   - 主室压力Pc = 给定值 (Pa)
    *   - 喉部喷管处流量由喉面积At和当地音速确定
    *   - NASA9平衡数据（298.15K参考焓）
    * 
    * 失败条件（返回非零码）：
    *   1: 温度迭代不收敛 (>100次迭代)
    *   2: 温度低于NASA9下限 (<300K)
    *   3: 含氧不足导致不完全燃烧 (检查)
    * 
    * 使用场景：
    *   - 给定Pc/O-F/燃料时计算HP温度与成分
    *   - 不用于变工况、冷却或不同反应物批次
    */
   ```

2. 在关键变量旁标注单位：
   ```c
   double T_combustion;  // [K] chamber temperature
   double p_chamber;     // [Pa] main chamber pressure (fixed input)
   int n_species;        // [-] count of active species (<=50 in NASA9)
   ```

### 检查项 1.2：喷管冻结假设

**文件**：`src/nozzle/ideal.c`  
**当前状态**：冻结喷管实现完整，但假设限制没有明确写进注释

**检查内容**：
```
需要补充说明：
- "冻结"意味着从喉部向下游，成分不变
- 不考虑重合成分、碳烟析出、两相流
- 喉部流量由音速和密度确定（不是熵流量概念）
- 背压高于理想膨胀压力时将发生分离（诊断建议，非计算结果）
```

**推荐改进**：
```c
/**
 * nozzle_isentropic_frozen: 理想冻结膨胀喷管
 * 
 * 物理模型：
 *   1. 喉部（At）：阻塞流（p*分子所有项）
 *   2. 出口（Ae/At）：等熵膨胀，成分冻结
 * 
 * 约束与不适用：
 *   X 不计重合成分（H2O/CO2解离）
 *   X 不计固体析出（C/烟）
 *   X 不考虑两相流或液滴携带
 *   X 固定压力比（p_exit/p_chamber），不计喷射速率影响
 * 
 * 超膨胀诊断：
 *   当 p_exit < p_ambient 时给出"分离参考"
 *   基于 Summerfield 0.4*pa 经验公式
 *   提示性质，不代表实际分离位置
 */
```

### 检查项 1.3：循环闭合的质量/功/热量账

**文件**：`src/cycle/adiabatic.c`（新Q=0模型）和 `src/cycle/prescribed.c`（给定热历史模型）

**检查内容**：验证每个循环的闭合方程是否在源码或文档中明确

**推荐改进**：
在 `docs/engineering.md` 的"循环模型"部分明确写出方程：

```
### 新循环：Q=0单轴开式/补燃

方程组（闭合性）：
  (1) 质量守恒：ṁ_fuel + ṁ_oxidizer + ṁ_bypass = ṁ_turbine_inlet
  (2) 功率平衡：W_turbine - W_pump = 0 (单轴)
  (3) 焓流平衡：h_fuel_inlet + h_ox_inlet = h_turbine_exit + Δh_losses
  (4) 成分混合：(回流焓/元素库存) × 质量分数 = 混合态

求解顺序：
  a) 给定：Pc, O/F, ṁ_fuel（或ṁ总）, 入口条件
  b) 求HP平衡 → T_combustion
  c) 求喷管冻结 → c*, F = ṁ * c*
  d) 求涡轮出口（冻结）→ T_exit, h_exit
  e) 闭合检查：质量是否守恒？轴功是否平衡？

失败条件：
  - 涡轮出口温度低于冷却极限
  - 涡轮压比过高（超过可实现范围）
  - 回流焓低于入口焓（热力不可达）
```

---

## 二、单位一致性与参数映射

### 检查项 2.1：压力单位

**问题类型**：Pa/MPa/atm混淆

**关键检查点**：
- [ ] 输入参数：`baseline.json` 中所有压力字段标注单位 (Pa/MPa)
- [ ] 代码变量：所有压力类变量命名中或注释中包含单位
- [ ] 输出格式：CLI/JSON/表格中明确显示 (MPa or Pa)
- [ ] 常数定义：`ATM_TO_PA = 101325.0` 等标准值在头文件中一次定义

**检查命令**：
```bash
grep -r "pressure" src/ include/ | grep -v "^.*//.*pressure" | head -20
# 看是否每个变量都有单位注释
```

### 检查项 2.2：温度、焓、比冲

**关键检查点**：
- [ ] 温度：始终为 K (Kelvin)，不能混 °C
- [ ] 焓：单位 J/kg 或 kJ/kmol，基准温度明确 (298.15K)
- [ ] 比冲：Isp 单位 s (秒)，推力 N (牛)，不混 kgf

**检查示例**：
```c
// 正确写法
double specific_impulse;  // [s] Isp = Thrust / (mass_flow_rate * g0)
double g0 = 9.80665;      // [m/s^2] standard gravity

// 错误写法（需要改）
double Isp;  // 缺少单位说明
double gravity;  // 为什么不用9.8或9.80665？
```

### 检查项 2.3：参数库与计算参数的对应

**文件**：`data/parameters/baseline.json` → 计算函数参数表

**检查内容**：
```
对于每个车辆情景（ZQ3-Y1-ST1等），检查：
1. 参数来源是否标注？
2. 是"采用"还是"候选"？
3. 缺口是否保留为null而不是假设值？
4. 单位是否与代码中的假设一致？
```

**示例表格**（应补充到report-flow或notes中）：

| 参数 | ZQ3-Y1-ST1 | 来源 | 身份 | 代码单位 |
|------|-----------|------|------|---------|
| Pc (main chamber) | 15.7 MPa | 产品规格 | 采用 | Pa (转换) |
| O/F | 2.6 | 试验参数表 | 采用 | ratio |
| At (throat area) | 0.15 m² | 衍生/设计 | 采用 | m² |
| Ae/At | 12.5 | 计算 | 派生 | ratio |
| T_inlet (oxidizer) | 80 K | 物性基准 | 假设 | K |

---

## 三、失败路径与诊断信息

### 检查项 3.1：越域拒绝

**问题**：当参数超出模型范围时，应明确拒绝而非默默改结果

**检查点**：
- [ ] 温度低于300K → 立即返回错误，不降级到NASA9下限
- [ ] 压力>50 MPa（超出设计范围）→ 警告或拒绝
- [ ] O/F<1或>5（超出常规）→ 明确说明"超出验证范围"
- [ ] 平衡迭代不收敛 → 返回诊断码，不用上次结果

**推荐改进**：
```c
// 当前可能的做法
if (temperature < T_MIN) {
    temperature = T_MIN;  // X 不好：默默改值
    // 应该改为：
    *error_code = ERR_TEMPERATURE_OUT_OF_RANGE;
    return NULL;  // 返回NULL或空结构，让调用方处理
}

// 记录诊断信息
snprintf(diag_buffer, 256, 
    "Temperature %.1f K below NASA9 minimum (%.1f K)\n"
    "Action: Computation rejected. Check inlet conditions.",
    temperature, T_MIN);
log_diagnostic(diag_buffer);
```

### 检查项 3.2：错误消息可读性

**检查内容**：
- [ ] 每个错误都有用户可理解的说明（不是代码行号）
- [ ] 包含"这是哪个物理约束被突破了"
- [ ] 如果是恢复性错误，给出建议（例如"请降低压力"）

**示例**：
```c
// 不好的诊断
fprintf(stderr, "Error code 7 at line 243\n");

// 好的诊断
fprintf(stderr, 
    "ERROR: Turbine outlet temperature (%.1f K) is below "
    "coolant effectiveness limit (%.1f K).\n"
    "This indicates over-expansion in the nozzle or "
    "unrealistic cooling.\n"
    "Suggestion: Check nozzle area ratio (Ae/At=%.1f) "
    "or inlet temperature.\n",
    T_outlet, T_coolant_min, area_ratio);
```

---

## 四、文档内链与Manifest对齐

### 检查项 4.1：报告交叉引用

**文件**：`deliverables/report.md`

**检查内容**：
- [ ] 第7.6节中的每个数字都能追溯到 `engine_cycles_v2_20261013` 中的具体算例INI
- [ ] 推力、比冲、轴功的数值与菜单8中显示的一致（六位有效数字）
- [ ] 表格注脚说明"研究假设，不代表飞行性能"
- [ ] 参考公式与`docs/engineering.md`中的失败语义一致

**推荐改进**：
```markdown
### 7.6 两个一级情景的循环计算结果

**情景1：朱雀三号遥一一级**
- 输入INI：`cases/vehicles/zq3_y1_stage1.ini`
- 循环模型：Q=0单轴开式（新循环）
- 热源：给定主室条件，计算得HP焓/成分
- 验证：与 `engine_cycles_v2_20261013` manifest 的第1条对齐
  （哈希：SHA256-...）

**表3.1 计算结果对标**

| 指标 | 数值 | 单位 | 来源 | 说明 |
|------|------|------|------|------|
| 推力 | 285.50 | kN | C计算 | c*由喉部阻塞流确定 |
| 比冲 | 291.13 | s | C计算 | 相对真空（1 atm背压） |
| 轴功 | 15.3 | MW | C计算 | 泵功假设为0（给定热） |

**限制**：该结果基于给定HP温度；
真实发动机的泵功、冷却、两相流不在模型范围内。
```

### 检查项 4.2：讲稿命令一致性

**文件**：`deliverables/presentation.md`

**检查内容**：
- [ ] "菜单8"的五个选项与代码中的cases实际对应
- [ ] 命令行演示（如果有）与当前可执行路径一致
- [ ] 秒数计划与实测时间不超10分钟

**推荐改进**：
```markdown
## 演讲计划（共10分钟）

1. **研究背景与问题**（1分钟）
   - 老师要求三大核心内容
   - 理由：为什么需要这个模型

2. **方法选择**（2分钟）
   - 为什么用零维热化学+喷管而不用CEA
   - 为什么两个循环模型并存
   - *直观演示*：`./build/release/rocketperf.exe interactive`
     选菜单8 → 选项1（朱雀三号一级）

3. **关键结果**（4分钟）
   - [现场从菜单读数值，对标报告表3.1]
   - 朱雀三号：推力285.5 kN, 比冲291.1 s
   - 长十乙一级：推力250.0 kN, 比冲303.5 s
   - 为什么二级数值相同？→ 输入和循环拓扑相同

4. **改进与缺口**（2分钟）
   - 面积比优化的收益示例
   - 当前模型不覆盖的范围（冷却、寿命）
   - 建议的后续研究方向

5. **结论**（1分钟）
   - 研究的学术价值和工程意义
   - 源码/运行包/报告的可用范围

*总计：540秒，留60秒作缓冲或提问过长时用*
```

---

## 五、交付包完整性检查

### 检查项 5.1：Manifest与源码一致性

**文件**：`build/delivery-final-overview-20261013/manifest.json`

**检查内容**：
```bash
# 运行verify
python tools/delivery.py verify --directory build/delivery-final-overview-20261013

# 应该看到：
# - 源码提交哈希：c92403a
# - INI文件完整性检查：PASS
# - 菜单vs JSON数值对比：PASS
# - 所有五个情景演示：PASS
```

**手工检查**：
- [ ] manifest.json中的source_commit是否与当前repo的c92403a匹配？
- [ ] 打包的exe是否是Release编译？
- [ ] 包内的cases/vehicles/*.ini是否与源码repo中的一致？

### 检查项 5.2：三套包的版本追踪

| 包名 | 日期 | 源码提交 | 主要变更 | 验证状态 |
|------|------|--------|---------|---------|
| delivery-imp002 | 2026-10-07 | ? | 成对研究算例 | PASS |
| delivery-qa002 | 2026-10-12 | ? | 菜单JSON对比 | PASS |
| delivery-final-overview | 2026-10-13 | c92403a | 报告技术审稿 | PASS |

**检查**：
- [ ] 三套包是否都在禁止读取当前cases/的条件下成功verify?
- [ ] 版本递进是否清晰（不是互相覆盖）？

---

## 六、快速检查脚本

```bash
#!/bin/bash
# quick-check.sh - 代码质量快速检查

set -e

echo "=== 1. 编译检查 ==="
cmake --build build/Release --config Release -- /m:4

echo "=== 2. 单元测试 ==="
./build/Release/test_core

echo "=== 3. CLI演示 (五个车辆情景) ==="
for case in cases/vehicles/*.ini; do
    echo "Testing: $case"
    ./build/release/rocketperf.exe cycle adiabatic "$case" --text | head -20
done

echo "=== 4. 菜单演示 ==="
# 交互式菜单不能自动化，但可以记录期望的数值
# 对标 deliverables/report.md 第7.6节

echo "=== 5. 质量检查 ==="
python tools/quality.py | tail -20

echo "All checks passed!"
```

---

## 七、验收清单（汇报前3天）

- [ ] **代码部分**
  - [ ] 所有C文件的函数头都有明确的物理约束说明
  - [ ] 所有数值变量的单位都有注释
  - [ ] 没有硬编码的魔数（应该定义在常数表中）
  - [ ] 越域条件都返回错误码，不默认改值

- [ ] **文档部分**
  - [ ] 报告7.6节与manifest对齐
  - [ ] 讲稿命令与当前源码可执行
  - [ ] 没有说"真实性能"，只说"研究假设"

- [ ] **交付包部分**
  - [ ] 三套包都通过verify
  - [ ] README清晰说明使用方式和限制
  - [ ] exe在禁读当前repo cases/的条件下正常运行

- [ ] **时间/人员部分**
  - [ ] 演讲计时≤10分钟
  - [ ] 人员分工已确认
  - [ ] PPT排版完成

---

这份清单将在代码最终审阅和汇报前执行。重点是**明确边界、可追溯参数、清晰诊断**，而不是代码量或行数。
