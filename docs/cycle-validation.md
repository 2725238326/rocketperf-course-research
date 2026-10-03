# 稳态部件与整机边界

模型ID：`prescribed_thermal_cycle_v1`。接口为`include/rocketperf/cycle.h`，实现为`src/cycle/`。本模型用于解释泵功、支路消耗和主室/整机口径，不是两型真实发动机性能预测，也不是有限元计算。

## 控制体与适用域

控制体从两种推进剂的泵入口，到主喷管和外排喷管出口；辅助轴功与机械损失跨越控制体。稳态、入口动能可忽略、恒密度绝热泵、单轴、九物种理想气相、涡轮/喷管组分冻结。主室与发生器温度、压力及泵入口密度/焓均由输入给定，不求起动、泵图谱、冷却或液态物性。

总流量与总O/F确定两路入口；两路推进剂均先泵送。轴功闭合确定发生器支路，发生器O/F决定燃料/氧化剂分流；主室使用余下的CH4/O2元素库存计算TP状态。代码中的298.15 K气相feed用于建立TP元素库存，不代替已给定的泵入口焓或计算液体汽化。

首版只允许发生器外排。`return_fraction`和`return_pressure_drop_pa`保留为显式边界字段，但任何非零值返回`RP_OUT_OF_DOMAIN`。压力可达不是混合物闭合；未来若做回流，必须重建返回气体和新鲜推进剂的元素/焓库存，再求主室状态，不能只改流量。

TP数值守卫继承已有气相模型：1000–6000 K、100–1e9 Pa、各燃烧库存O/F在0.1–20；这些是软件边界，不是认证气相稳定域。涡轮与喷管还须在活跃物种共同NASA9温区内找到根；喷管仅接受匹配/欠膨胀。所有声明的热状态即使支路为零仍要合法。

## 方程与能量的含义

泵的流体焓升包含全部轴输入，不另加一次泵损失：

```text
w_p = (p_out - p_in) / (rho * eta_p)
P_p = mdot * w_p
h_out = h_in + w_p
```

冻结涡轮先在给定出口压力求等熵状态，再求实际状态：

```text
s(T_s, p_out, y) = s_in
w_t = eta_t * (h_in - h_s)
h(T_out, p_out, y) = h_in - w_t
eta_shaft * mdot_branch * w_t = P_fuel + P_oxidizer + P_aux
P_mechanical_loss = (1 - eta_shaft) * mdot_branch * w_t
```

`P_aux`定义为外部输出的非负辅助轴负载；机械损失是外排热，不回加流体。`h_in-h_out`才是实际轴功，不能再次乘效率扣除。零总负载给零支路；正负载、零涡轮压降无法闭合。

泵入口焓必须与NASA9形成焓同基准；入口h不是任意独立的零点。两项热交换是维持给定温度**所需**的热输入（负数为热排出），不是计算燃烧效率、热值或壁面热通量：

```text
Q_generator = mdot_branch * h_generator
              - mdot_branch_fuel * h_fuel_pump_out
              - mdot_branch_oxidizer * h_oxidizer_pump_out
Q_chamber   = mdot_main * h_chamber
              - mdot_main_fuel * h_fuel_pump_out
              - mdot_main_oxidizer * h_oxidizer_pump_out
H_exit     = sum[mdot_exit * (h_exit + velocity_exit^2 / 2)]
R_energy   = H_feed + Q_generator + Q_chamber
              - H_exit - P_aux - P_mechanical_loss
```

形成焓已在产品焓中，不能重复加低位热值。压力流功已包含在焓中，不能再把推力乘排气速度加入能量式。泵功是内部能量传递，涡轮抽出的轴功已在支路焓降中；全局式只保留外部辅助功和机械损失。程序与报告重新计算这些式子是**记账一致性检查，不是独立验证未知燃烧热量**。

推力是主喷管与支路轴向分量之和；分母采用总消耗，不能把主室比冲充当整机比冲。支路轴向投影为零时，支路流量和出口动能依然存在。喉面积由流量除以喉部质量通量得到，不是任意指定第二个流量。

## Synthetic inputs

[合成输入](../cases/benchmarks/prescribed_cycle.ini)全部是人为方法条件，无型号字段。100 kg/s、总O/F=3.4、主室5 MPa/3300 K、发生器6 MPa/1800 K、涡轮出口0.5 MPa。泵的422/1141 kg/m³、−4.65 MJ/kg/0 J/kg、效率和压升只是显式假设，不附会为某台发动机液体性能或实测状态。

本算例主室所需热排出约193.65 MW、发生器所需热输入约2.08 MW，表明给定热状态并不构成绝热真实循环。不能用闭合残差抹掉这项限制。

## 验证与实际结果

`tests/test_cycle.c`有241项检查：泵制造解/零流量、原子H恒cp涡轮解析解、效率1与0.6、熵生成、零负载/零支路、外排支路、横向排气、六个涡轮效率点、整体流量缩放、压力/预算/非有限输入与失败输出哨兵。恒cp测试低于1000 K采用固定原子H物性，不是发生器化学或真实工况。

Windows GCC14.2 Debug/Release实际运行；CMake/Ninja Release 6项CTest通过。22组CLI包含严格schema、BOM/CRLF/中文路径、输出确定性、错误码/空stdout和16种篡改结果反例。质量指纹覆盖所有新源码/测试。

`tools/cycle_validation.py`从输入和公开的泵/涡轮/喷管状态重新核对86条方程，检查两路质量、轴功、焓、推力、热交换和单位口径；不读取求解器内部局部变量，也不声称第三方物理实验对照。整机没有独立外部循环参考，待研究参数与流体闭合扩展后另验。

固定运行在[归档清单](../results/validation/prescribed_cycle_v1_20261004/manifest.json)，包含输入、输出、构建/测试/运行清单与SHA-256，不含exe。结果：

| 量 | 合成算例结果 |
|---|---:|
| 两泵总轴功 | 1,137,201.607646 W |
| 涡轮轴功 | 1,207,580.639628 W |
| 发生器外排流量 | 0.674224777 kg/s |
| 主室净流量 | 99.325775223 kg/s |
| 整机推力 | 296,254.198769 N |
| 整机等效比冲 | 302.095209647 s |
| 全局能量记账残差 | 约3.09e−8 W |

复现（从项目根目录）：

```powershell
python tools/pipeline.py test --configuration Release
python tools/pipeline.py run --model prescribed-cycle --case cases/benchmarks/prescribed_cycle.ini --no-build
python tools/cycle_validation.py --archive-id NEW-UNUSED-ID
```

归档ID必须新建，不能覆盖固定结果。API失败保持output不变；JSON仅在加载和求解均成功后写出，流写入失败可能留下半份文本，运行工具不会保存成功`result.json`。

部件参考及检索失败记录见[源码核验专题](../调研/专题/MOD-003_循环边界与部件参考.md)；后续改进要报告效率、分流、所需热交换与推力的共同变化，不只比较主喷管数字。
