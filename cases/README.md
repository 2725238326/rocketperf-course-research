# 算例

`benchmarks/`包含两份定比热空气教学输入，以及`prescribed_cycle.ini`给定热状态循环基准。它们都不是目标型号参数。`research/`保存研究问题的显式场景；计算产物放results，不混入输入目录。

格式见[输入契约](../docs/case-format.md)，参考值和公式见[基准说明](../docs/benchmarks.md)。新增研究场景须提供来源定位及模型适用条件；未知真实参数不能直接用教学值填入。

运行：`pwsh -NoProfile -File ./scripts/run-case.ps1`；默认算例为真空教学基准。程序可直接输出JSON，也可通过运行脚本保留完整追溯文件。
