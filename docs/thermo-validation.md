# NASA9 物性原型验收

状态：原型已运行；真实物种数据尚未冻结。

## 当前可运行产出

- `include/rocketperf/thermo.h`：单物种、分温区 NASA9 API。
- `src/thermo/nasa9.c`：按 NASA9 形式计算质量基 `cp`、`h`、`s`，检查有限数、温区和正定 `cp`。
- `tests/test_thermo.c`：11 项 C 测试，覆盖低温区、高温区、边界、越域和非法输入。
- `data/thermo/fixture_nasa9.tsv`：项目自有合成系数夹具，仅验证公式/API，不代表任何真实物种。

## 公式边界

输入系数按 NASA9 九系数形式保存。计算使用通用气体常数 `R_u=8314.46261815324 J/(kmol K)`，再按摩尔质量转换为质量基。每个温区独立选择；温度不在任何区间时返回 `RP_OUT_OF_DOMAIN`，不会静默外推。

## 尚未声称完成的内容

当前夹具不是 NASA CEA `thermo.inp`，也不是空气、液氧甲烷或液氧煤油的真实物性数据库。NASA CEA 仓库的 Apache-2.0 代码许可不能自动推出其热化学数据文件的独立许可。真实数据接入前还必须固定：数据文件来源、版本/提交、哈希、物种组成、温区、焓基准和独立参考值。

## 实际验证命令

```powershell
python tools/pipeline.py test --configuration Debug
python tools/pipeline.py test --configuration Release
python tools/quality.py
```

截至 2026-10-03，Debug 和 Release 均通过：核心 207、适配器 21、NASA9 原型 11、CLI 13 组。
