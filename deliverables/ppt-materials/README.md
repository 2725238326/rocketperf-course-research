# 手工制作PPT的图表数据

这些CSV由`python tools/presentation_materials.py`从离线演示保存的C结果导出，不生成或修改PPT。来源可用`python tools/demo_data.py --check`实际复算。导出身份与文件哈希见[manifest](manifest.json)。

| 数据 | 使用位置 | 选择的列与处理 |
|---|---|---|
| [p5-chamber.csv](p5-chamber.csv) | P5燃烧室 | `of`作X，`cstar_m_s`作Y；`tc_k`用于温度峰标注，不与c*共用纵轴 |
| [p6-propellants.csv](p6-propellants.csv) | P6表格 | 单位已列；F用kN，其他按原单位，正文显示两位小数 |
| [p7-nozzle-vacuum.csv](p7-nozzle-vacuum.csv) | P7喷管曲线 | `epsilon`作X，`isp_s`作Y；`exit_area_m2`用于收益/面积核对 |
| [p8-ambient.csv](p8-ambient.csv) | P8环境对照 | 同ε10的两个背压比较；ε40海平面被拒算，不填假比冲 |
| [p9-cycle.csv](p9-cycle.csv) | P9及循环备答 | GG开式、ORSC富氧补燃；压力给定/求解角色与残差单位分别列出 |
| [backup-backpressures.csv](backup-backpressures.csv) | 多背压备答 | 四个不同背压系列；空格代表拒算，图表“空单元格显示间隙” |

主线液甲烷条件：燃料120K、液氧100K，两路入口10MPa；主室Pc=10MPa、At=0.01m²。P5扫描O/F，P6–P8固定O/F2.6。P7改变面积比，P8再改变背压。RP-1比较保留其固定入口298.15K/90.170K，不能改写为国产煤油实测。

主线关键核对：c*采样峰2.7，温度采样峰3.7；比冲差13.85s，流量约少4.46%；ε10真空/海平面差19.04s；真空ε40相对ε10增益23.32s。表格显示精度导致末位差异时，以保存的原始数值计算再四舍五入，不用已圆整值重复相减。

CSV用UTF-8 BOM保存，Windows Excel可直接打开。制作PowerPoint图时复制所需列到“编辑数据”窗口，先删模板示例系列，再插入散点折线图。空值不能补0。这里没有要求你们先制作所有图：可先搭页面与主要表格，再依逐页指南替换图。
