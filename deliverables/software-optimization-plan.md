# 软件前后端快速对比与优化清单

## demo/index.html的优势（保留参考）

1. **视觉设计**：
   - 深色海军蓝渐变顶栏
   - 卡片式布局，圆角12px统一
   - 数字大字报（1.85rem字重650）
   - 分段色彩：燃料暖色、氧化剂冷色、燃气红、轴灰

2. **交互体验**：
   - 6页标签切换，键盘1-6快捷键
   - 滑块实时预览（带刻度和当前值）
   - 拒算状态明确标红
   - 计算链可视化（步骤→箭头→步骤）

3. **数据呈现**：
   - KPI大数字+小单位
   - 公式用sub/sup排版（如c*、ε）
   - 表格右对齐数字，左对齐标签
   - CSV数据内嵌2501条C运行记录

## 当前程序短板（按优先级）

### 🔴 P1：CLI输出可读性
**问题**：纯文本表格，数字不对齐，单位混在一起
**4小时能做**：
- [ ] 统一数字右对齐，单位独立列
- [ ] 添加分隔线（`---`）区分章节
- [ ] 关键结果加粗或颜色（如果终端支持）

**不做**：重写TUI界面

### 🟠 P2：错误提示不友好
**问题**：拒算时只返回错误码，不解释原因
**2小时能做**：
- [ ] 在 `src/core/errors.c` 补充友好提示
- [ ] 凝聚碳拒算时打印"O/F过低，进入凝聚碳区"

**示例**：
```c
// 改前
return ERR_CARBON_CONDENSATION;

// 改后
fprintf(stderr, "拒算：O/F=%.2f 过低，石墨活度>1，进入凝聚碳区\n", of_ratio);
return ERR_CARBON_CONDENSATION;
```

### 🟡 P3：交互菜单缺输入提示
**问题**：菜单只列选项，不提示单位和默认值
**1小时能做**：
- [ ] 在 `src/cli/interactive.c` 的提示中加单位
- [ ] 如："请输入室压 Pc (MPa) [默认: 10.0]: "

### 🟢 P4：无GUI（demo是网页，程序是CLI）
**现实**：4-6小时**做不了GUI**
**替代方案**：
- 保持CLI为主交付
- demo的HTML作为"可视化附件"
- 在报告中说明："CLI用于批量计算，网页用于演示"

## 快速优化行动（如果有2小时）

### 第1步（30分钟）：修复CLI输出对齐
```bash
# 编辑这些文件
src/cli/combustion_commands.c
src/cli/main.c
```

找到打印结果的`printf`，改成：
```c
// 改前
printf("Isp: %.2f s\n", isp);
printf("Thrust: %.2f kN\n", thrust);

// 改后
printf("%-20s %10.2f %s\n", "比冲 Isp", isp, "s");
printf("%-20s %10.2f %s\n", "推力 F", thrust, "kN");
```

### 第2步（30分钟）：补充拒算提示
```bash
# 编辑
src/thermo/equilibrium.c
```

在判断凝聚碳的地方加：
```c
if (graphite_activity > 1.0) {
    fprintf(stderr, "警告：O/F=%.2f 进入凝聚碳区（a_C=%.3f>1），气相模型失效\n", 
            of_ratio, graphite_activity);
    return ERR_CARBON_CONDENSATION;
}
```

### 第3步（30分钟）：菜单加单位提示
```bash
# 编辑
src/cli/interactive.c
```

改提示语：
```c
printf("室压 Pc (MPa, 默认10.0): ");
printf("混合比 O/F (默认2.6): ");
printf("喉部面积 At (m², 默认0.01): ");
```

### 第4步（30分钟）：测试和编译
```bash
python tools/pipeline.py test --configuration Release
./build/release/rocketperf.exe interactive
```

## 不建议做的（时间陷阱）

❌ **重写GUI**：至少需要2-3天
❌ **代码大重构**：答辩前改动风险太大
❌ **新增功能**：如绘图、数据库、Web服务
❌ **完美主义优化**：如性能调优、内存优化

## 现实建议

**如果只有4-6小时**：
1. 优先级1答辩准备（1小时）
2. 优先级2 PPT制作（2.5小时）
3. 优先级3讲稿对齐（0.5小时）
4. **剩余时间再考虑软件优化**

**软件优化的时机**：
- 答辩后有时间再完善
- 当前版本已经是可交付的（6627行+13722检查）
- demo的HTML已经展示了"理想形态"

**对老师的说辞**：
"CLI是核心计算引擎，严格验证；HTML演示页是可视化辅助，方便展示结果。两者配合使用。"
