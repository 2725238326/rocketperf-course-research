# 提交后复验与本地交接

日期：2026-10-04。对已提交源码进行复验，不新增物理功能或改写原研究证据。

## 固定版本

- `f3d06b9`：数值验收、活跃文档补审和C循环研究。
- `b2c66e2`：实际六状态CEA TP参考、类型/trace/超时反例与研究交接。

两批均完成本地Git提交；提交后主工作区干净。没有推送或更新外部仓库，PPT与最终报告未开展。原始资料、旧快照和旧研究档案保留。

## 独立源码检出

`build/clean-ana002`是独立Git克隆，不是复制主工作区build；在干净状态从本地仓库快进到`b2c66e2`，重新执行`python tools/quality.py`。

结果：6/6 PASS，指纹`96683a1316d491fa40c90315c1424e6f8b4b2d0504499f05e4ebf42d728c4b19`与主工作区一致。Debug/Release各4201项C检查，CLI25组，参数8、物性5、CEA参考12、循环研究参考8组；治理19、runner25、交接6组，均实际执行、零跳过。报告`build/clean-ana002/build/quality/latest.json`。这证明干净检出可重新构建/校验，不等于另一位人员完成了科学审查。

## 固定提交交接包

`build/handoff-b2c66e2`已生成并验证，包含已测Windows程序、输入、成功/预期失败日志、哈希、第三方数据许可和离线`source.bundle`。程序只导入Windows系统DLL；隔离PATH运行成功退出0、越域预期退出4。

- 包固定提交：`b2c66e233147a1d9400ee5e92dfe0a94818aaf0e`。
- 包清单SHA256：`27fc288e80f83f90b1c9443ead9fabc2a77ca7a70e43c62b861c6b7b9b3733f9`。
- 源码bundle SHA256：`8f7cbb41cc2d5076c4252cf8aa2a9b9e2e1334530bb8000129b3f949cd703077`。
- 本机自检收据：`build/handoff-b2c66e2-self-check.json`，actor=root，maintenance。它不是实际组员接收，接手同学仍需按docs/receiving.md具名复跑。

包与日志保留在忽略目录，不进入Git，不公开上传。包固定第二批源码提交；本快照只是随后补记，不应据分支HEAD变化改写包版本或哈希。

## 下一项

ANA-003按六状态TP及边界说明合同DONE；ANA-004 READY，接续实际冻结喷管同条件参考和固定几何可行性。DOC-001仍依赖该研究，不开展PPT/最终报告。没有真实发动机完整循环、液态入口、煤油、冷却/分离或寿命验证；这些缺口不能由质量PASS抹去。
