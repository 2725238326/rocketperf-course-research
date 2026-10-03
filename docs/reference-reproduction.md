# CEA 固定算例复现

日期：2026-10-03。已在 Windows x64/MinGW GCC、gfortran 14.2.0 实际构建 CEA v3.3.4，并记录/复跑四个固定算例。它是外部参考，不进入项目 C 核心运行链。

## 固定了哪些条件

源码 commit：4c5c612efa2002a94e3a5a1f33b1674d55c65340。thermo.inp SHA256：fa7746572952d74e249e818a82a35c113829742fb421a308e167185528884363。许可、NOTICE 与物性源码已归档，见[物性验证](thermo-validation.md)。

四个输入卡使用气態 CH4/O2、298.15 K 入口、100 bar、质量 O/F=3.4，仅允许 H2/O2/H2O/CO/CO2/CH4/H/O/OH 九个中性气体。TP指定3000 K；HP绝热定压；两喷管卡分别是沿程平衡和燃烧室冻结 nfz=1，均为无限截面燃烧室、超声速出口面积比10和40。没有N2、离子或凝聚相；不是全数据库组分空间，不能据此判断结焦。

气态入口是方法基准，不是液氧/液甲烷发动机入口状态；这些压力、混合比、面积比也不是对目标型号的参数补齐。液态入口焓和煤油替代组分需要另行核验。

输入、原始输出、编译数据库/二进制哈希和结构化打印值见[参考manifest](../tests/reference/cea/manifest.json)。构建输出和每次不可覆盖运行另保存在被忽略的 build 内；重新运行不会覆盖正式参考。

## 本机命令

已有固定源码位于 build/reference/cea-v3.3.4。首次取得源码时可执行：

~~~powershell
git clone --branch v3.3.4 --depth 1 https://github.com/nasa/cea.git build/reference/cea-v3.3.4
git -C build/reference/cea-v3.3.4 rev-parse HEAD
~~~

先核对提交，再构建。下面命令假设在项目根目录，且已有本机CMake/Ninja/MinGW：

~~~powershell
./build/tooling/cmake/data/bin/cmake.exe -S build/reference/cea-v3.3.4 -B build/reference/cea-build-v3.3.4 -G Ninja -DCMAKE_MAKE_PROGRAM=E:/Work/火发原理/build/tooling/bin/ninja.exe -DCMAKE_Fortran_COMPILER=D:/program/mingw/mingw64/bin/gfortran.exe -DCMAKE_C_COMPILER=D:/program/mingw/mingw64/bin/gcc.exe "-DCMAKE_Fortran_FLAGS=-fimplicit-none -ffree-line-length-none" -DCMAKE_BUILD_TYPE=Release -DCEA_ENABLE_BIND_C=TRUE -DCEA_ENABLE_BIND_CXX=FALSE -DCEA_ENABLE_BIND_PYTHON=FALSE -DCEA_ENABLE_BIND_MATLAB=FALSE -DCEA_ENABLE_BIND_EXCEL=FALSE -DCEA_BUILD_TESTING=OFF
./build/tooling/bin/ninja.exe -C build/reference/cea-build-v3.3.4 -j 1
python tools/cea_reference.py --check
python tools/cea_reference.py
~~~

--check只验证归档和解析，不要求CEA运行环境；最后一条才实际调用参考程序，复制固定卡和数据库到唯一目录、检查版本/返回码/诊断、解析表和模式、核对打印数值，并保存运行清单。任何失败保留FAIL记录。三组归档/缺陷/模式反例测试已接入Debug/Release流水线。--record仅供首次建参考，已有目录时拒绝覆盖。

## 原始输出与可用数值

| 同条件算例 | 燃烧室温度 K | c* m/s | 面积比40的真空有效排气速度 m/s |
|---|---:|---:|---:|
| HP | 3673.61 | 不适用 | 不适用 |
| 平衡喷管 | 3673.61 | 1878.97 | 3696.84 |
| 燃烧室冻结喷管 | 3673.61 | 1839.39 | 3435.41 |

这些是该受限参考算例打印值。项目C实现现已完成TP、HP、燃烧室冻结A10/A40的同条件对照，见[热化学与喷管验证](thermo-nozzle-validation.md)；未实现沿程平衡喷管。CEA的Ivac和Isp栏单位是m/s；转为秒必须除以标准重力加速度，不能把3696.84写作秒。平衡和冻结差异只体现所选化学路径，不直接代表可实现的改进收益。

## 实际发现和处理的缺陷

- 关闭C绑定的纯Fortran配置链接缺两个异常恢复符号。采用官方C绑定构建配置后通过，没有改上游算法。构建记录在 build/reference/cea-build-v3.3.4。
- 最初trace=1e-12时TP/HP所有物种都超输出阈值，空微量物种列表却打印非法字节。源码main.f90第2468–2472行在num_trace=0时仍访问列表。初始输入/输出原样保存在 raw 顶层，反例测试明确拒绝它。正式参考只把输出阈值改为1e-8，使CH4进入微量列表；不改物理求解输入。正式输出存在 raw/trace1e8，四个算例重新运行并数值复核通过。
- 反应物ENERGY表头写KJ/MOL，而CH4打印-74600，不能按该标签直接使用；原文形成焓是-74600 J/mol。计算主表H使用kJ/kg，与入口质量加权焓一致。已保留并标注输出标签问题，不修改原文。
- 冻结喷管燃烧室Cp行仍打印平衡导数值，但Gamma_s对应冻结性质；MOD-002验证冻结物性应从固定组分NASA9重新算，不把这个Cp行当作冻结热容参考。

本次外部程序退出与软件检查不等于独立科学审查。原CEA卡/输出没有为匹配C实现而修改；C输出、残差和比较误差独立记录。真实液態输入、沿程平衡、整机循环与实验核验不在本阶段证明范围内。
