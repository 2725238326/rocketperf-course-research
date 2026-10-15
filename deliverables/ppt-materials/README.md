# 手工制作PPT的图表数据

这些CSV由`python tools/presentation_materials.py`从离线演示保存的C结果导出，不生成或修改PPT。来源可用`python tools/demo_data.py --check`实际复算。导出身份与文件哈希见[manifest](manifest.json)。

| 数据 | 使用位置 | 选择的列与处理 |
|---|---|---|
| [template5-plan.jpg](template5-plan.jpg) | 组合PPT | P1–P13与致谢页对应的模板5原页缩略图 |
| [p5-program.csv](p5-program.csv) | P5程序页 | 各模块非空C/H行数与文件数、C检查与CLI组数、静态分析单元、HP提速与迭代次数、编译选项；来自演示页保存的工程记录 |
| [p6-chamber.csv](p6-chamber.csv) | P6燃烧室 | `of`作X，`cstar_m_s`作Y；`tc_k`用于温度峰标注，不与c*共用纵轴 |
| [p7-propellants.csv](p7-propellants.csv) | P7表格 | 单位已列；F用kN，其他按原单位，正文显示两位小数 |
| [p8-nozzle-vacuum.csv](p8-nozzle-vacuum.csv) | P8喷管曲线 | `epsilon`作X，`isp_s`作Y；`exit_area_m2`用于收益/面积核对 |
| [p9-ambient.csv](p9-ambient.csv) | P9环境对照 | 同ε10的两个背压比较；ε40海平面被拒算，不填假比冲 |
| [p10-cycle.csv](p10-cycle.csv) | P10及循环备答 | GG开式、ORSC富氧补燃；压力给定/求解角色与残差单位分别列出 |
| [backup-backpressures.csv](backup-backpressures.csv) | 多背压备答 | 四个不同背压系列；空格代表拒算，图表“空单元格显示间隙” |

主线液甲烷条件：燃料120K、液氧100K，两路入口10MPa；主室Pc=10MPa、At=0.01m²。P6扫描O/F，P7–P9固定O/F2.6。P8改变面积比，P9再改变背压。RP-1比较保留其固定入口298.15K/90.170K，不能改写为国产煤油实测。

主线关键核对：c*采样峰2.7，温度采样峰3.7；比冲差13.85s，流量约少4.46%；ε10真空/海平面差19.04s；真空ε40相对ε10增益23.32s。表格显示精度导致末位差异时，以保存的原始数值计算再四舍五入，不用已圆整值重复相减。

CSV用UTF-8 BOM保存，Windows Excel可直接打开。制作PowerPoint图时复制所需列到“编辑数据”窗口，先删模板示例系列，再插入散点折线图。空值不能补0。这里没有要求你们先制作所有图：可先搭页面与主要表格，再依逐页指南替换图。
