# 20261028_wbase_frontier_b

检索日期：2026-10-28；证据截止：2026-10-28；来源：Grok联网检索。此文件是检索返回内容，需结合正文来源审核。

**精选3项（2024–2026，优先原始arXiv/期刊/GitHub官方，截止2026-10-28前；C17高温CHO气相TP/HP Gibbs/元素势+稳健Newton/延拓相关，排除液液平衡与2017 ODML）。** 均为理想气体/元素守恒+质量作用或Gibbs最小化框架，可处理少量气相物种（9种CHO如H₂/O₂/H₂O/CO/CO₂/OH/H/O/N₂等典型燃烧产物直接适用，无需冷凝或电离扩展即可跑HP/TP；FastChem面向多物种大气但气相求解器同样适用小系统）。无法核全文处已注明。无残差校正/回退学习法在此范围内针对高温气相CHO的公开原文。[[1]](https://arxiv.org/abs/2409.15086)

**1. Combustion Toolbox: An open-source thermochemical code for gas- and condensed-phase problems involving chemical equilibrium**  
Alberto Cuadra, César Huete, Marcos Vera. arXiv:2409.15086 (2024-09-23提交)，期刊Computer Physics Communications 320 (2026) 110004，DOI 10.1016/j.cpc.2025.110004。原始全文：https://arxiv.org/pdf/2409.15086 ；期刊https://www.sciencedirect.com/science/article/pii/S0010465525005053 ；代码https://github.com/CombustionToolbox/combustion_toolbox 。  
支持片段：“The kernel of the code is based on the theoretical framework set forth by NASA’s computer program CEA … while incorporating new algorithms that significantly improve both convergence rate and robustness. … CT-EQUIL, minimizes the Gibbs/Helmholtz free energy of the system using the technique of Lagrange multipliers combined with a multidimensional Newton-Raphson method, upon the condition that two state functions are used to define the mixture properties (e.g., enthalpy and pressure).” 文档进一步说明HP/TP等用二阶NR解附加约束，解耦后灵活性高于CEA。  
对象/假设：理想气体（NASA 9系数多项式，Third Millennium/ATcT数据，T至20000 K），气相+纯冷凝相，元素守恒+Gibbs/Helmholtz最小化（Lagrange乘子），指定两状态函数（TP/HP/SP/TV/EV/SV）。直接适用于小型9气相HP（文档有CH₄-空气23物种含CHO的3000 K/1 atm TP及LH₂/LOX HP示例，小系统无问题）。稳健性改进针对CEA类NR发散。无法核期刊全文排版细节，但arXiv与摘要/文档一致。[[1]](https://arxiv.org/abs/2409.15086)

**2. FastChem 4: New chemical elements and improved convergence behaviour**  
D. Kitzmann, J. W. Stock, A.B.C. Patzer. arXiv:2605.18264 (2026-05-18/19)。原始全文：https://arxiv.org/pdf/2605.18264 ；代码https://github.com/NewStrangeWorlds/FastChem （v4，含PyFastChem）。  
支持片段：“We extend the gas-phase solver with a multidimensional Newton-method convergence accelerator that mitigates the slow convergence previously encountered for strongly non-solar elemental abundances. We further reformulate the gas-phase equations in logarithmic element densities, removing the dependence on quadruple-precision arithmetic … The condensate solver is upgraded with adaptive Levenberg–Marquardt regularisation, a perturbed-Hessian fallback … and a combined gas–condensate Newton solver.” 默认层次法，Newton仅作加速器（>400次迭代后启用）。  
对象/假设：气相+冷凝（雨出近似可选），质量作用+元素守恒（对数元素密度作变量），T=100–6000 K、P=10⁻¹³–1000 bar（太阳能丰度测试，非太阳能亦改进），44元素/800气相物种。直接适用于小型9气相HP/TP（气相求解器独立，CHO系统如C/O变化示例可直接降维运行；高T区域Newton加速针对慢收敛）。FastChem Cond (Kitzmann et al. 2024, MNRAS 527, 7263, DOI 10.1093/mnras/stad3515) 为v3前身，气相基础相同。arXiv全文可核，期刊待刊未核。[[2]](https://arxiv.org/pdf/2605.18264)

**3. Parametrization and Cartesian representation techniques for robust resolution of chemical equilibria**  
Maxime Jonval, Ibtihel Ben Gharbia, Clément Cancès, Thibault Faney, Quang Huy Tran. Journal of Computational Physics 522 (2025) 113596，DOI 10.1016/j.jcp.2024.113596（2024投稿/2025刊）。原始：https://www.sciencedirect.com/science/article/pii/S0021999124008441 （摘要/高亮；HAL预印本https://hal.science/hal-04225504）。  
支持片段：“We propose two new formulations for single phase equilibrium problems. Both formulations yield bounded Jacobians, enhancing robustness of Newton’s method. The locally quadratic convergence of the Newton method is proved for our approaches. … accurate, allowing to compute equilibria with chemical species having very low concentrations. Moreover, the robustness of our methods combined with a globalization strategy is superior to that of the literature.” 参数化图或Cartesian增广系统，避免梯度爆炸/病态。  
对象/假设：单相（气相适用），Gibbs最小化或质量作用+元素守恒，Newton局部二次收敛，处理极低浓度物种。直接适用于小型9气相HP（通用单相求解器，无冷凝/多相等假设冲突；高温CHO低丰度自由基/离子场景可测病态Jacobian）。ScienceDirect全文需订阅，摘要/高亮与HAL一致，日期可核。[[3]](https://www.sciencedirect.com/science/article/abs/pii/S0021999124008441)

**最值得与传统热启动比较的小实验及失败判据**  
取标准9气相CHO（H₂、O₂、H₂O、CO、CO₂、OH、H、O + N₂或Ar稀释，当量比0.5–2，NASA 9系数热数据），HP问题（初始T=300 K、P=1 atm，目标高T 2500–5000 K燃烧产物）。传统热启动=CEA/CT类Lagrange-NR从低温/化学计量初值起步；对比FastChem层次+Newton加速、JCP参数化/Cartesian Newton、或CT改进NR（可加简单延拓：从已知低温平衡沿T/P路径步进）。运行100–1000个随机扰动初值或C/O变化点。失败判据：最大迭代（如100–400）后残差>10⁻⁸–10⁻¹⁰（元素守恒或Gibbs梯度）、出现负摩尔分数/数密度、Gibbs不单调下降、或对数变量下溢/溢出。记录收敛率、迭代次数与最终残差，量化热启动失败区（高T低P或非太阳能丰度）。此实验规模小、可复现（开源代码直接调用），直接检验稳健Newton/延拓相对热启动的增益，无SOTA声称。
