# 算例文件和结果契约 v1

CLI：`rocketperf run CASE.ini`。成功时stdout只有UTF-8 JSON，stderr为空；失败时写stderr并返回非零，不先打印半份物理结果。

## 输入字段

平坦的`key=value`格式，所有字段必填。行首`#`为注释；支持空行、两侧空格、LF/CRLF及文件开头UTF-8 BOM。不支持行内注释、INI分节、自动单位转换或未知字段。

| 字段 | 类型/单位 | 约束 |
|---|---|---|
| schema_version | 字面整数 | 必须为`1` |
| case_id | ASCII标识符 | 1—63字符，小写字母/数字/下划线/连字符 |
| case_kind | 枚举 | `synthetic_benchmark`或`research_scenario`；不支持“已验证真实发动机”类别 |
| source_ref | 来源定位文字 | 1—255可打印ASCII字符；字段存在不是来源真实性认证 |
| model | 模型ID | `ideal_constant_gamma_v1` |
| gamma | 无量纲 | 当前模型`1<gamma<=2` |
| gas_constant_j_kg_k | J/(kg·K) | 比气体常数，有限正数；不是通用气体常数 |
| stagnation_temperature_k | K | 储室总温，有限正数 |
| stagnation_pressure_pa | Pa | 储室总压，有限正数；与静压口径分开 |
| area_ratio | Ae/At | `1…10000` |
| throat_area_m2 | m² | 有限正数，用于流量和推力尺度 |
| ambient_pressure_pa | Pa | 有限非负且位于模型支持的背压范围 |

数字为十进制/科学计数法，无单位后缀。NaN/Inf、十六进制、溢出/下溢、逗号小数和多余字符拒绝。重复、遗漏、拼错字段也拒绝，不靠缺省值掩盖。

每个文件最多128行，每行最多510字节（CR/LF占用字节计入），嵌入NUL拒绝。元数据字段当前使用ASCII，文件路径支持Windows中文及空格。这是初版输入边界，不是未来中文元数据的永久限制。

## 结果字段

JSON包含schema版本、程序版本、模型ID、算例标识/类别/来源、完整实际输入、SI单位命名的结果、求根迭代和面积残差、模型限制。相同程序和输入的stdout确定，不混入时间戳；时间与文件哈希由运行manifest记录。

结果核心量：出口Mach、温度、压力、速度、出口面积、c*、流量、推力、CF、秒制Isp。主室理想模型结果不可重新标为整机真实性能。

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功或帮助/版本输出 |
| 2 | 命令用法错误 |
| 3 | 文件/格式/输出错误 |
| 4 | 参数适用域、数值、求解等模型错误 |

库API返回更具体的`RpStatus`，可选错误详情使用调用方结构体；失败不覆盖输出结构体。调用方必须先检查状态再读取结果。

## 追溯运行

`tools/pipeline.py run`（或兼容脚本`run-case.ps1`）复用新鲜且已测试的具体构建；证据缺失/过期则默认先构建测试，`--no-build`要求直接拒绝。它原子占用RunId，复制实际输入、二进制及构建/测试记录，保留stdout/stderr和v2运行清单。准备/启动/超时/协议校验任何阶段失败均写FAILED，不生成成功result.json。

输出不仅要能解析为JSON，还必须满足字段、版本、有限数值、诊断和来源契约，并与实际输入快照对应。输入、二进制、构建/测试清单和结果保留SHA-256。同名RunId拒绝覆盖。已有v1历史运行保留不改写。

manifest证明文件关联和执行情况，不代替物理验证，也不保证不同平台的浮点结果逐位一致。解析source_ref、获取文献和真正型号数据的字段级证据属于后续DATA-001。

## 气态燃烧与冻结喷管CLI

该接口独立于L0的INI协议，不接受真实型号名称作隐式参数：

```powershell
rocketperf combustion tp T_K P_PA OF TF_K TO_K
rocketperf combustion hp P_PA OF TF_K TO_K
rocketperf combustion frozen P_PA OF TF_K TO_K AREA_RATIO AMBIENT_PA
rocketperf combustion frozen-tp T_K P_PA OF TF_K TO_K AREA_RATIO AMBIENT_PA THROAT_M2
rocketperf combustion hp-h nasa9-cea-v3.3.4 gas P_PA OF HF_JKG HO_JKG
rocketperf combustion frozen-h nasa9-cea-v3.3.4 gas P_PA OF HF_JKG HO_JKG AREA_RATIO AMBIENT_PA THROAT_M2
```

全部为SI值，OF为氧化剂/燃料质量比；TF/TO为气态CH4/O2入口温度。使用完整十进制数，不接受NaN/Inf、十六进制、尾随文字、缺项或多余参数。JSON带`schema_version=1`、明确模型ID、mode、固定dataset、实际输入、燃烧室组分/冻结cp/h/s、残差和限制；冻结模式另带冻结位置、喉部/出口状态与c*、有效排气速度m/s。TP焓差可以非零；HP焓残差必须满足0.01 J/kg。

`frozen`保持气态入口HP含义；`frozen-tp`先求指定主室TP，再在主室冻结。新模型ID为`ch4_o2_tp_frozen_fixed_area_v1`，必须给正有限喉面积m²；`geometry`返回喉/出口面积m²、由阻塞通量求得的流量kg/s、推力N和单喷管比冲s。面积比/背压适用域继承冻结核心；这不是轴功/分流/入口闭合。指定TP的焓差可以非零，但HP迭代数必须为0。

`hp-h`/`frozen-h`是独立显式入口焓路径，模型ID分别为`ch4_o2_hp_enthalpy_v1`和`ch4_o2_hp_enthalpy_frozen_fixed_area_v1`。基准必须为`nasa9-cea-v3.3.4`，相态必须为`gas`；HF/HO是包含形成焓的纯CH4/O2质量比焓J/kg，可以为负。两种焓须在各自200–6000 K气相拟合端点范围内；未知基准/相态显式失败，不自动转换液体或任意零点。JSON不编造入口温度，另带`boundary.inlet_mixture_h_j_per_kg`及`heat_transfer_j_per_kg=0`；HP求温度，不能再将给定TP当作绝热。`frozen-h`同样返回固定面积`geometry`，不是全循环闭合。

模型与测试边界见[验证说明](thermo-nozzle-validation.md)和[显式焓验证](adiabatic-inlet-validation.md)。`tools/combustion_reference.py`检查固定方法基准，`tools/adiabatic_inlet.py`归档显式焓/固定面积基准。任意参数的通用追溯入口尚未接入，不能把现有L0运行manifest套到新模型结果。

## 给定热状态循环协议

`rocketperf cycle prescribed CASE.ini`使用独立模型`prescribed_thermal_cycle_v1`。字段清单以[合成输入](../cases/benchmarks/prescribed_cycle.ini)为准：5个元数据字段与28个SI数值字段全部必填；未知/重复/缺失字段、NUL、超长行、非有限或非十进制数全部拒绝。UTF-8 BOM、CRLF和中文文件路径可用，元数据值为有界可打印ASCII。泵流量不允许覆盖，由总流量/O/F推导。

输出包含`boundary/case/inputs/flows/pumps/turbine/main_nozzle/branch_nozzle/performance/energy/diagnostics/limitations`；零支路的`branch_nozzle`为null，不输出伪造零温度状态。推力单位N、有效速度m/s、比冲s、功率与热交換W；入口h为J/kg且与NASA9形成焓同基准。`generator_required_heat_w`、`chamber_required_heat_w`是保持给定温度所需交换，不是燃烧预测。

`python tools/pipeline.py run --model prescribed-cycle --case cases/benchmarks/prescribed_cycle.ini`共用正式运行生命周期；从当前已测具体构建启动，重算86条方程后才保存成功结果。退出码2/3/4沿用既有含义。加载/求解失败stdout为空，外排和回流边界见[模型说明](cycle-validation.md)。
