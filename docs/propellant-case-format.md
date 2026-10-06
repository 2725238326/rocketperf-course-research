# 成对推进剂算例文件

文件命令：`rocketperf study propellants --case CASE.ini`。它把成对比较需要的共同压力、喉面积、面积比、背压和两种方法的混合比存成一份严格输入，交接时不必逐个传参数。

## 字段

| 字段 | 内容 | 约束 |
| --- | --- | --- |
| schema_version | 版本号 | 必须为`1` |
| case_id | 算例标识 | 小写字母/数字/下划线/连字符 |
| model | 模型ID | 必须为`propellant_fixed_geometry_v1` |
| source_ref | 来源定位 | 可打印ASCII |
| methane_of、kerosene_of | 两路混合比 | 十进制数 |
| pressure_pa | 共同室压 | Pa |
| throat_area_m2 | 共同喉面积 | m² |
| area_ratio | 共同面积比 | 无量纲 |
| ambient_pressure_pa | 共同背压 | Pa |

所有字段必填；缺项、重复、未知字段、非有限数和非法数据集/相态均拒绝并返回3。写入的 dataset、焓基准、相态和燃料标识只起核对作用：文件值与模型固定身份不一致即拒绝，防止把真实发动机参数或未知批次燃料静默塞进成对比较。

## 模型固定的部分

温度、入口压力、物性数据集和焓基准不写在文件里，由模型固定并在JSON中输出：

- 甲烷路：CH4=120 K、O2=100 K，两路查表压力10 MPa，连续单相液体表。
- RP-1路：燃料298.15 K、O2(L)=90.170 K，固定指定焓。

文件只改变混合比和共同几何。两种入口各自保留方法身份（连续表 vs 固定锚点），JSON的`inlets`段写明每路的温度、压力和数据集，便于核对没有静默替换。

## 运行与失败

```powershell
./build/release/rocketperf.exe study propellants --case cases/research/propellant_comparison.ini
```

成功返回完整JSON（两路状态、几何和CH4−RP-1差值）；任一路入口或喷管失败则stdout为空、退出4；文件/格式错误退出3；命令语法错误退出2。结果字段与研究归档`propellant_comparison_v1`同构，新研究版本另建目录，不覆盖旧记录。
