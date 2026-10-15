# 关键演示态截图操作清单

六张默认态截图已在 `deliverables/demo/screenshots/`，但 P5/P6/P9 演示的**关键交互态**需要主讲在演练时手动截取。这些截图是 PPT 附录页的补充——现场演示翻车时翻过去讲，数字和主讲刚点出来的状态一致。

## 需要补截的三张（演练第一遍时完成）

### 1. P5_chamber_carbon_refusal.png（凝聚碳拒算态）

**操作**：
1. 双击打开 `deliverables/demo/index.html`，按 `A` 关动画
2. 已在页 1（燃烧室），点预设"凝聚碳区 O/F 0.4"
3. 等左上卡片显示红色"×C 拒算"，右侧活度图红线过 1
4. `F11` 全屏，`Win+Shift+S` 截图保存为 `deliverables/demo/screenshots/p5_chamber_carbon_refusal.png`
5. `F11` 退出全屏

**验证要点**：左上卡片显示 `out_of_domain`、活度 > 1、组成堆叠图消失（拒算态不显示组成）

---

### 2. P6_propellant_crossover.png（推力差变号点）

**操作**：
1. 按 `2` 切到页 2（推进剂）
2. 拖动"甲烷 O/F"滑块到 **2.9** 附近（推力差线过零的位置）
3. 等图表稳定，检查右侧相对差图：推力差黑线穿过零线
4. `F11` 全屏截图 `p6_propellant_crossover.png`

**验证要点**：右侧图推力差线在零线上、比冲差和流量差一正一负

---

### 3. P9_cycle_staged.png（补燃循环态）

**操作**：
1. 按 `4` 切到页 4（循环）
2. 点预设"补燃循环"（或切分段按钮到"补燃"）
3. 等左侧 schematic 重绘：全部氧化剂走预燃室、涡轮后回流主室
4. 检查右上涡轮出口压力显示 **17.95 MPa**
5. `F11` 全屏截图 `p9_cycle_staged.png`

**验证要点**：管线流向改变（氧化剂全走预燃室）、涡轮出口压力 17.95、右下四本账残差 < 1 W

---

## 三张截图的用途

| 文件 | 对应讲稿 | PPT 附录页 | 现场演示失败时的保底 |
|---|---|---|---|
| p5_chamber_carbon_refusal.png | P5 第 57 行"点凝聚碳区" | P13 | 翻到 P13 指图说"活度过 1 拒算" |
| p6_propellant_crossover.png | P6 第 69 行"推力差过零" | P14 | 翻到 P14 指图说"O/F 2.9 变号" |
| p9_cycle_staged.png | P9 第 105 行"切到补燃" | P16 | 翻到 P16 指图说"17.95 兆帕" |

**时机**：演练第一遍计时跑完，立即按上述操作补截三张。存入 `screenshots/` 后交给做 PPT 的组员放进附录页。

## 验收

截完后运行：
```bash
ls -lh deliverables/demo/screenshots/*.png | awk '{print $9, $5}'
```

应有 9 张 PNG（6 默认 + 3 关键态），每张 > 200 KB。
