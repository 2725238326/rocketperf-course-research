# 2026-10-02_008：IMP-001 S1 实现切片

任务：IMP-001。目标是把主选题“喷管面积比随环境压力变化的准一维性能权衡”做成可验证的 C17 研究入口，并保持现有 L0 单算例兼容。

## 交付

- 新增 `rp_nozzle_scan_area_ratio_ambient`：显式网格、容量检查、有限数/范围检查、逐点失败诊断。
- 新增 `rocketperf study area-ratio-ambient CASE.ini`，支持默认网格和 CSV 网格轴。
- 新增扫描 JSON 契约：基准输入、网格顺序、每点状态、成功结果或越域错误、模型限制。
- 新增 [实现说明](../docs/model-implementation.md) 和 [S1 数据边界专题](../调研/专题/IMP-001_S1面积比环境压力实现与数据边界.md)。
- 新增研究情景算例 `cases/research/s1_area_ratio_ambient.ini`，明确不是已验证发动机数据。
- 增加 C 核心与 CLI 测试：网格点数、背压导致推力下降、越域状态、非法轴参数。

## 验证

```text
python tools/project.py check       PASS
git diff --check                    PASS
python tools/quality.py             PASS
```

质量入口包含 project、governance、Debug、Release 和 runner 五项；扫描示例 2×3 网格得到 5 个 `ok` 点和 1 个 `out_of_domain` 点。该证据只验证 L0 数学/协议实现，不代替真实发动机验证。
