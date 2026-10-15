# C代码快速优化清单(可选,1小时内)

## ⚠️ 优先级判断
**如果PPT未完成**: 先做PPT,代码优化放答辩后
**如果PPT已完成且时间>2小时**: 按下面顺序做

---

## 1. CLI输出对齐(30分钟)

### 目标文件
- `src/cli/combustion_commands.c`
- `src/cli/cycle_commands.c`  
- `src/adapters/text_report.c`

### 快速改法
找到所有`printf`输出结果的地方,改成:

```c
// 改前
printf("Isp: %.2f s\n", isp);
printf("Thrust: %.2f kN\n", thrust);

// 改后  
printf("%-24s %12.2f %s\n", "比冲 Isp", isp, "s");
printf("%-24s %12.2f %s\n", "推力 F", thrust, "kN");
```

格式说明:
- `%-24s`: 标签左对齐,宽度24字符
- `%12.2f`: 数字右对齐,宽度12,保留2位小数
- 单位独立列

### 验证
```bash
./build/release/rocketperf.exe combustion regime-liquid cases/vehicles/zq3_y1_stage1.ini --text
```
检查输出是否对齐。

---

## 2. 拒算提示友好化(15分钟)

### 目标文件
- `src/thermo/equilibrium.c` (凝聚碳拒算)
- `src/nozzle/frozen.c` (过膨胀拒算)

### 快速改法

**凝聚碳拒算**(约145行):
```c
// 找到判断 graphite_activity > 1.0 的地方
if (graphite_activity > 1.0) {
    fprintf(stderr, "警告: O/F=%.2f 进入凝聚碳区 (a_C=%.3f>1.0), 气相模型失效\n",
            of_ratio, graphite_activity);
    return ERR_CARBON_CONDENSATION;
}
```

**过膨胀拒算**(约nozzle适配器):
```c
if (exit_pressure < ambient_pressure) {
    fprintf(stderr, "提示: 出口压力 %.1f kPa < 背压 %.1f kPa, 附着模型拒算\n",
            exit_pressure/1000, ambient_pressure/1000);
    return ERR_OVEREXPANDED;
}
```

### 验证
```bash
# 测试凝聚碳
./build/release/rocketperf.exe combustion regime-liquid --of 0.8 --pc 10 --text

# 测试过膨胀
./build/release/rocketperf.exe nozzle frozen --epsilon 40 --pa 101325 --text
```

---

## 3. 编译与测试(15分钟)

```bash
# 重新编译
python tools/pipeline.py build --configuration Release

# 快速测试
python tools/quality.py

# 如果有错误,只改输出部分,不动计算逻辑
```

---

## 4. 代码流程图(可选,答辩后做)

### 方案A: 用现有SVG
直接使用 `docs/architecture/report-flow.svg`,包含:
- 五条求解链
- 输入检查
- 失败返回

**口头解释脚本**:
"输入经过检查后,按命令进入五条求解链。求解成功才写结果,失败只返回退出码,不会给出错误的数字。"

### 方案B: 补充关键函数注释(20分钟)
不画图,在关键函数头注释加流程说明:

```c
/**
 * @brief HP平衡求解主函数
 * 
 * 流程:
 * 1. 初始化迭代器(温度、压力)
 * 2. Illinois法求解焓守恒
 * 3. 收敛后计算石墨活度
 * 4. 凝聚碳检查(a_C>1拒算)
 * 5. 返回九气相组成
 */
int hp_equilibrium_solve(...);
```

---

## ❌ 不要做的

1. **重构代码结构**: 答辩前不改架构
2. **新增功能**: 不加GUI/绘图/数据库
3. **性能优化**: 6.4倍提速已经够讲
4. **完美主义**: 代码已经可交付

---

## 时间分配建议

**如果剩余时间<1小时**: 不做代码优化,直接跳到最终检查
**如果剩余1-2小时**: 只做CLI输出对齐
**如果剩余2-3小时**: 输出对齐+拒算提示

---

## 对老师的说辞(如果没优化)

"CLI是核心计算引擎,严格验证通过13722项检查。HTML演示页是可视化辅助,展示了理想形态。两者配合使用。"

"代码优化在答辩后继续,当前版本已经满足课程要求。"

---

## 流程图答辩应对

**如果老师问"有流程图吗"**:
→ 翻到备用材料,展示 `docs/architecture/report-flow.svg`
→ "这是五条求解链,输入检查后分别处理"

**如果老师问"能不能看代码"**:
→ 打开 `src/thermo/equilibrium.c` 或 `include/rocketperf/combustion.h`
→ 指出函数签名、注释、错误处理
→ "6627行都按这个规范写的"

---

**总结**: 代码已经合格,优化是加分项不是必须项。优先保证答辩准备完成。
