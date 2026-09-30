# 环境与运行

本机验证：Windows、Python 3.13、MinGW GCC 14.2.0、PowerShell 7.6.5、Git 2.46.2。另已在项目临时目录安装CMake 3.31.10和Ninja 1.13.2，完成Release构建与CTest。Linux/远端CI仍需真实运行。

## 常用命令

从项目根目录执行：

```powershell
python tools/project.py doctor
python tools/project.py check
python tools/quality.py
python tools/pipeline.py run --case cases/benchmarks/air_mach2_vacuum.ini
```

只构建或单配置测试：

```powershell
python tools/pipeline.py build --configuration Debug
python tools/pipeline.py test --configuration Release
```

GCC命令可用--compiler指定。C运行时无Python物理求解依赖；Python标准库组织构建、测试、任务和运行证据。PowerShell脚本保留兼容参数，统一调用Python工具。

## 构建与报告位置

- 每次尝试：build/artifacts/配置/build-id/，包含状态manifest和日志。
- 当前指针：build/配置/latest.json。失败尝试不会自动回退旧PASS。
- 当前方便查看的build-manifest/test-report会同步，但正式运行按指针核验实际构建、二进制和测试输入。
- 运行：results/local/RunId/。--no-build要求当前已有新鲜的已测试构建，否则失败；默认缺证据时先构建测试。

旧工程的v1运行记录保留，现行运行/构建manifest为v2。不要把旧报告文件存在等同当前通过。

## CMake本机复现（Windows）

临时工具都在build中，不修改系统PATH，也不进入Git：

```powershell
python -m pip install --target build/tooling cmake==3.31.10 ninja==1.13.2
$ninja = (Resolve-Path build/tooling/bin/ninja.exe).Path
& ./build/tooling/cmake/data/bin/cmake.exe -S . -B build/cmake-verified -G Ninja "-DCMAKE_MAKE_PROGRAM=$ninja" -DCMAKE_C_COMPILER=gcc -DCMAKE_BUILD_TYPE=Release
& ./build/tooling/cmake/data/bin/cmake.exe --build build/cmake-verified
& ./build/tooling/cmake/data/bin/ctest.exe --test-dir build/cmake-verified --output-on-failure
```

已有工具时无需重装。Linux或已配置CMake的环境可直接使用cmake/ctest命令。构建源码列表来自project/modules.json，不在两份入口重复维护。

## 任务和Git

```powershell
python tools/project.py show RES-001
git config --local core.hooksPath .githooks
python tools/project.py check --staged
```

完整状态流转见[治理规范](governance.md)。实时分支/HEAD/脏状态看doctor；本地有提交不等于已经推送。

## Grok检索

配置仍在 `E:/Demo/IDEA_collector/apikey/grok.txt`，不输出或复制凭据。已有起始问题可预览：

```powershell
pwsh -NoProfile -File ./调研/scripts/research.ps1 -Topic 20261001_res001_versions -CutoffDate 2026-10-01 -Brief -DryRun
```

实际检索时去掉DryRun；新执行日期/问题使用新的Topic和明确截止。MaxCalls只是提示目标。构建、治理和架构工具不调用该接口。

原始来源索引重建脚本会写哈希记录，不能把它当只读验证或用于掩盖不明变化。现有资料无需重复下载。没有后台服务、自动监控或对外发布安排。
