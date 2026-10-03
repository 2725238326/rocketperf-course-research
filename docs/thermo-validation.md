# NASA9 单物种物性与数据验证

更新：2026-10-03。十种真实中性气体物性已经接入 C17；燃烧平衡、混合物和温变喷管仍未实现。

## 可直接运行的内容

~~~powershell
python tools/pipeline.py test --configuration Release
./build/release/rocketperf.exe thermo H2O 300
~~~

查询返回质量基 cp、h、s，单位分别为 J/(kg·K)、J/kg、J/(kg·K)，并注明数据库和 100000 Pa 标准压力。它不是燃烧温度、比冲或实际压力下的混合物熵。

- 接口：[thermo.h](../include/rocketperf/thermo.h)，失败不覆盖结果。
- 计算：[nasa9.c](../src/thermo/nasa9.c)；只读查询：[database.c](../src/thermo/database.c)。核心无 Python、文件或网络依赖。
- 数据：[manifest](../data/thermo/manifest.json)、[TSV](../data/thermo/cea_nasa9.tsv)。原合成 fixture 保留作历史/公式夹具，不进入真实数据库。
- 复现转换：[thermo_data.py](../tools/thermo_data.py)。正常构建无需 Cantera；生成独立参考时才使用被隔离的 Cantera 3.1.0 环境。

## 数据、温区和基准

CEA v3.3.4 固定到 commit 4c5c612efa2002a94e3a5a1f33b1674d55c65340。原始 thermo.inp、LICENSE、NOTICE 和公式源码原样保存在[来源目录](../调研/原始来源/20261003_cea_v3.3.4/NOTICE.txt)，哈希、物种原文行号及引用保存在 manifest。NOTICE 的 Data 节明确列出 thermo.inp；本次选取和格式转换保留许可、声明和物种引用，未改动系数。

包含 H2、O2、N2、H2O、CO、CO2、CH4、H、O、OH，共 28 个温区。所有物种从 200 K 开始，1000 K 为分界；H2O/CH4 止于 6000 K，其余八种在 6000 K 继续换区，止于 20000 K。使用 [Tmin,Tmax)，最终上界包含；不外推，接点归高温区。

与该版本 CEA 一致，R_u=8314.5100 J/(kmol·K)，使用其原始摩尔质量。形成焓已包含在 b1 中，物种头部的 Hf 不再次叠加；Hf 原文单位是 J/mol。s 是单物种标准态熵；后续混合物还需压力和混合熵项，当前接口未声称实现。

## 对照和测试证明什么

[Cantera 参考](../tests/reference/nasa9_cantera.json)有 134 个状态，覆盖区间上下界、边界两侧及内部温度。用 Cantera 3.1.0 的 C++ NASA9 实现计算相同系数；其默认气体常数与 CEA 不同，参考值明确按常数比例转换。独立 airNASA9.yaml 只对 O2/N2/O 三种逐项核对系数，不能宣称它独立覆盖其余物种。

这是独立软件实现对照，不是独立实验数据，也不是燃烧或发动机验证。主要 C 对照容差为相对 2×10⁻¹¹，辅以 cp/s 的 10⁻⁷ 和 h 的 10⁻⁶ 绝对容差。

[物性测试](../tests/test_thermo.c)还检查九项系数逐项贡献、dh/dT=cp、ds/dT=cp/T、温区拼接、十物种 298.15 K 形成焓（0.01 J/mol 绝对容差）、NaN/Inf、间隙/重叠、未选中区坏系数、数值失败和输出保持。当前 Release 实际执行 1175 项物性检查、15 组 CLI 黑盒测试（零跳过），另有 4 组数据/证据防误报测试。最新全量验收以质量报告为准，不沿用旧报告。

~~~powershell
python tools/thermo_data.py --check
python tools/quality.py
~~~

需要重生成参考时：

~~~powershell
python -m pip install --target build/reference_tooling cantera==3.1.0 --only-binary=:all:
python tools/thermo_data.py
python tools/thermo_data.py --reference
python tools/thermo_data.py --check
~~~

Python 环境只生成数据/独立校验值；发布程序的物性运算仍完全由 C 执行。
