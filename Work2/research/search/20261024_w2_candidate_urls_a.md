# 20261024_w2_candidate_urls_a

检索日期：2026-10-24；证据截止：2026-10-24；来源：Grok联网检索。此文件是检索返回内容，需结合正文来源审核。

**1. Reaktoro Machine Learning（Allan Leal, 2022）**  
官方URL: https://reaktoro.org/tutorials/machine-learning/index.html  
实际检索：已检索；原文可得（完整官方教程页）。  
支持片段：Reaktoro implements machine learning accelerated solvers... SmartEquilibriumSolver... on-demand machine learning (ODML) algorithm first introduced in Leal et al. [2017], then improved in Leal et al. [2020]... first-order Taylor approximation... mass conservation... intrinsically mass conservative because mass balance equations are linear.[[1]](https://reaktoro.org/tutorials/machine-learning/index.html)

**2. Ultra-Fast Reactive Transport Simulations When Chemical Reactions Meet Machine Learning: Chemical Equilibrium（Allan M. M. Leal, Dmitrii A. Kulik, Martin O. Saar, 2017）**  
官方URL: https://arxiv.org/html/1708.04825v1  
实际检索：已检索；原文可得（arXiv HTML全文）。  
支持片段：we present a machine learning method that enables new equilibrium states to be quickly and accurately estimated... smart chemical equilibrium method... on-demand machine learning method... implemented in Reaktoro... reaktoro.org.[[2]](https://arxiv.org/html/1708.04825v1)

**3. Accelerating Reactive Transport Modeling: On-Demand Machine Learning Algorithm for Chemical Equilibrium Calculations（Allan M. M. Leal, Svetlana Kyas, Dmitrii A. Kulik, Martin O. Saar, 2020）**  
官方URL: https://link.springer.com/article/10.1007/s11242-020-01412-1  
实际检索：已检索；原文部分可得（Springer摘要/预览；DOI 10.1007/s11242-020-01412-1）。  
支持片段：an on-demand machine learning algorithm that enables quick and accurate prediction of new chemical equilibrium states... mass conservative by construction... implementation and numerical tests are carried out in Reaktoro (reaktoro.org).[[3]](https://link.springer.com/article/10.1007/s11242-020-01412-1)

**4. Reaktoro GitHub / 项目仓库（Allan Leal, 2014–2024）**  
官方URL: https://github.com/reaktoro/reaktoro  
实际检索：已检索；原文可得（README + LICENSE）。  
支持片段：a unified framework for modeling chemically reactive systems... support to chemical equilibrium and kinetics calculations with general constraints... License: LGPL v2.1... Copyright © 2014-2024 Allan Leal. reaktoro.org.[[4]](https://github.com/reaktoro/reaktoro)

**5. KINSOL Documentation（Alan C. Hindmarsh, Radu Serban, Cody J. Balos, David J. Gardner, Daniel R. Reynolds, Carol S. Woodward 等）**  
官方URL: https://sundials.readthedocs.io/en/latest/kinsol/  
实际检索：已检索；原文可得（官方文档）。  
支持片段：KINSOL, a solver for nonlinear algebraic systems. It includes a Newton-Krylov solver as well as Picard and fixed point solvers... KINSOL is written in C, with C++ and Fortran interfaces. N_Vector module... serial, MPI-parallel, OpenMP and Pthreads thread-parallel N_Vector implementations, as well as multiple N_Vector implementations designed to leverage GPU architectures.[[5]](https://sundials.readthedocs.io/en/latest/kinsol/)

**6. Using KINSOL for the Solution of Nonlinear Systems（SUNDIALS 官方用法文档）**  
官方URL: https://sundials.readthedocs.io/en/latest/kinsol/Usage/  
实际检索：已检索；原文可得。  
支持片段：users are required to supply a function of type KINSysFn that defines the nonlinear system... KINInit(..., KINSysFn func, ...)... optionally supply... KINLsJacFn... Jacobian construction (matrix-based)... KINSetJacFn()... Jacobian-vector product (matrix-free)... KINLsJacTimesVecFn. N_Vector implementations... not all SUNLinearSolver and SUNMatrix objects are compatible with all N_Vector implementations... OpenMP... Pthreads.[[6]](https://sundials.readthedocs.io/en/latest/kinsol/Usage/)

**7. SUNDIALS License and Notices / KINSOL（LLNL 官方）**  
官方URL: https://sundials.readthedocs.io/ 及 https://computing.llnl.gov/projects/sundials/license  
实际检索：已检索；原文可得。  
支持片段：All SUNDIALS packages are released open source, under the BSD 3-Clause license... LLNL-CODE-665877 (KINSOL)... serial, MPI, OpenMP and Pthreads thread-parallel N_Vector... GPU. 线程安全方面：官方文档明确提供 OpenMP/Pthreads 向量后端及多线程环境初始化说明，但未检索到对同一 KINSOL 求解器实例并发调用的完整“thread-safe/reentrant”独立声明（无法进一步核实该点）。[[7]](https://sundials.readthedocs.io/)

**8. Differentiable Thermodynamic Phase-Equilibria for Machine Learning（Karim K. Ben Hicham, Moreno Ascani, Jan G. Rittig, Alexander Mitsos, 2026）**  
官方URL: https://arxiv.org/html/2603.11249v4  
实际检索：已检索；原文可得（arXiv HTML）。  
支持片段：Physics-consistent machine learning methods... equilibrium data arising from an extremum principle, such as liquid-liquid equilibria... differentiable algorithm for phase-equilibrium calculation that guarantees thermodynamic consistency... constrained minimization of the Δg mix... global optimality of Δg mix and stability conditions... algebraic（Gibbs 能量极值/相平衡，区别于有限速率积分或 PDE 代理）。其他检索到的 PINN/守恒学习多针对化学动力学 ODE/源项（如 over-equilibrium dynamics、NeuralODE kinetics），已按用户要求区分。[[8]](https://arxiv.org/html/2603.11249v4)

以上为截止检索范围内直接相关的原始官方/作者来源（Reaktoro 官网/论文/仓库；SUNDIALS KINSOL 文档/许可证；代数 Gibbs/TP-HP 类相平衡物理约束学习）。无聚合搜索页。Reaktoro 的 ODML 直接针对化学平衡（Gibbs 能量最小化/参数化约束，含质量守恒）。KINSOL 为 C 语言非线性代数求解器，用户提供 residual（KINSysFn）与可选 Jacobian。
