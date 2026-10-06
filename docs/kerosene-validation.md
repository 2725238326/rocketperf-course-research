# 固定RP-1公共入口核验

方法：固定CEA RP-1 C₁H₁.₉₅与O₂(L)，九种中性理想气体HP，燃烧室冻结单喷管。产品压力10 MPa，O/F=2.2–4.0，RP-1=298.15 K、O₂(L)=90.170 K。边界依据[RES-008](../调研/专题/RES-008_煤油计算边界.md)，保存输入和新C/CEA对照见[归档](../results/validation/kerosene_anchor_v1/manifest.json)。

## 纯C接口和运行

`RpAssignedReactantFeed`表示指定反应物输入，旧`RpCh4O2AnchorFeed`保留兼容别名。`RpKeroseneAnchorFeed`额外要求独立数据集ID；`rp_kerosene_anchor_inlet`生成每kg元素库存和指定化学焓，`rp_kerosene_equilibrium_hp_anchor`复用现有内部HP。CH4/RP-1接口各自验证温度和燃料ID，不能通过改名字切换燃料。

```powershell
./build/release/rocketperf.exe combustion hp-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 'O2(L)' 10000000 2.6 298.15 90.170
./build/release/rocketperf.exe combustion frozen-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 'O2(L)' 10000000 2.6 298.15 90.170 10 0 0.01
```

成功JSON使用独立`rp1_o2l_hp_assigned_v1`/`rp1_o2l_hp_frozen_fixed_area_v1`模型ID，返回输入、反应物身份、化学焓/库存、燃烧室、残差、喷管/几何与限制。C17程序直接完成求解，无Python、Fortran、CEA、Grok或外部物性库运行依赖。Python工具和CEA只生成/核验开发参考，未链接发布程序。

未知ID、非液态声明、温度偏离、压力非10 MPa、O/F越界返回OUT_OF_DOMAIN；非有限/非正数或空必要字段返回INVALID_ARGUMENT。夹逼/迭代失败沿用明确状态，公共C调用失败保持输出。CLI语法错误码2、计算拒绝码4，stdout为空，stderr留诊断。额外指定焓参数属于非法语法，不能覆盖固定数据库。

## 参考与限制

O/F=2.2/2.4/2.6/2.9/3.2/3.6/4.0七点，各有HP和A10/A40 C运行；同条件CEA受限HP/冻结喷管和扩展产物HP分别保存。打印感知容差：燃温0.02 K、组分2e−6、c*/有效速度0.03 m/s；另复算元素质量、焓、物性、声速、能量/熵和几何/推力关系。软件核验与同源物性差异均不能替代实验。

这些参考支持指定方法范围内的数值实现；七点不是全相态稳定性证明。富燃料失败/凝聚碳仍由RES-008保存。入口不含连续温压物性、密度、压缩焓、泵、喷注、回流和整机轴功，真实国产煤油批次未知。不能将公开140吨级或YF-100K量级贴到当前JSON作为真实预测。

档案包含33次C运行（21成功、12预期拒绝）、21张CEA卡和812项参考/关系比较。新增内部点的产物集燃温差0.31/0.42/0.46 K（O/F=2.4/2.9/3.6）；扩展卡未打印超过1e−7阈值的凝聚碳。公共API与CLI成功拒绝、相邻浮点边界、夹逼/迭代失败和输出保持，以及归档重算哈希后的语义篡改均纳入回归测试。

O/F=2.6、At=0.01 m²真空A10：燃温约3724.0068 K、c*=1760.6575 m/s、流量56.79696 kg/s、F=172.98471 kN、Isp=310.57173 s。A40比冲333.59645 s、F=185.80920 kN；出口面积0.1/0.4 m²的变化未计喷管质量、冷却或分离代价。

归档复核命令：`python tools/kerosene_validation.py verify results/validation/kerosene_anchor_v1`。开发参考重建另用新目录，已有归档保持字节。最终课程发布源代码以src/include的C及必要构建/算例为核心，工具与参考单列为复现附件，避免把Python工具误写成生产求解链。
