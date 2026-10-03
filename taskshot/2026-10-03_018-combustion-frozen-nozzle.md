# 受限TP/HP与燃烧室冻结喷管

日期：2026-10-03。任务：MOD-002。起点：本地提交2fc2b40、工作树clean；本轮Windows主线，不使用WSL或浏览器UI，不派生子agent。

## 实际产物

- `include/rocketperf/combustion.h`、`src/thermo/mixture.c`与`equilibrium.c`：固定九物种及C/H/O矩阵，标准态/混合熵、气态入口焓、元素势TP、外层HP，带主元4×4消元、阻尼/回溯与温度连续化。
- `include/rocketperf/frozen_nozzle.h`、`src/nozzle/frozen.c`：保存燃烧室组分，以温变cp/h/s求等熵压力、喉部声速和超声速面积支；结果含守恒残差。
- CLI `combustion tp/hp/frozen`；解析完整十进制数，输出实际输入、数据/模型ID、组分、残差与限制。旧run/study/thermo回归不变。
- `tools/combustion_reference.py`：新鲜已测构建身份、二进制/参考快照、四次C实跑和CEA比对；失败留清单；新增版本拒绝覆盖。
- `results/validation/20261003_ch4_o2_frozen_v1`与`v2`：保存实际输出和误差；v2为回调初始化修正后版本。原CEA卡/数据/输出没有改写。
- 模块/依赖与三视图同步；PNG在build/architecture-review-mod002，已查看渲染结果，文本与边界没有遮挡。

## 数值与覆盖

HP：3673.614567611 K，焓差−0.004122507 J/kg。冻结c*：1839.387209484 m/s；A10/A40真空有效排气速度：3192.263179601/3435.407477836 m/s，与固定CEA打印值的误差均小于0.004 m/s。

Release实际执行207核心、21适配器、1175物性、2512燃烧/冻结检查和18组CLI，零跳过。燃烧测试覆盖36个TP与9个HP状态、六条独立反应驻点、混合物积分关系、CEA同条件对照、定cp解析Mach 2极限、背压/温区/相态/不收敛与失败保持输出。新增归档一致性测试保留历史产物，并检查哈希/输出/差值。

CMake Release（-O3）五项CTest已通过；GCC -fanalyzer对12个生产C源无诊断。静态分析日志在build/static-analysis-mod002-20261003，独立构建在build/cmake-mod002-20261003。

## 失败与修正

首次CLI对照检查错误地要求比较条目“>20”，TP实际为20，导致失败；改为至少20，没有放宽任何数值阈值。首次CMake -O3停止于两个喷管回调状态的maybe-uninitialized警告；显式零初始化后重跑五项通过，没有关闭警告。失败构建/测试记录保留，不计入PASS。新的runner模拟夹具补入工具文件并断言具体异常，防止准备缺失被当作预期执行失败。

## 验收与边界

`python tools/quality.py`五项全部PASS，结束时间2026-10-03 23:36:10（北京时间）。新鲜输入指纹为479336b24b21c5656259952a4006df050effd1a986724c4aa2c8a85e7f74374e。任务按ACTIVE→REVIEW→DONE完成；不可变验收证据为`project/evidence/MOD-002_90d5628706e1.json`。这份历史快照不代替未来重新运行的质量报告。

语义验收由本轮负责人解释，不冒充独立人员审查。只验证选定理想气相方法，未验证真实液态入口、凝聚相/结焦、电离、沿程平衡喷管、损失/分离、冷却、整机循环或真实型号绝对性能。后续按MOD-003/ANA-002契约继续；PPT/报告后置。实质产物审查后创建本地检查点，未推送远端；提交实况由doctor查询，不在快照中反复复制HEAD。
