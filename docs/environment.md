# 环境与运行说明

盘点日期：2026-10-01。项目根目录：`E:/Work/火发原理`。默认使用PowerShell 7，命令示例从根目录执行。

## 已实际检查

| 项目 | 结果 | 限制 |
|---|---|---|
| PowerShell | `pwsh --version`：7.6.5 | 不加载用户profile，避免提示增强/代理配置副作用 |
| GCC | MinGW 14.2.0，路径`D:/program/mingw/mingw64/bin/gcc.exe` | 已通过C17严格警告Debug/Release构建、核心测试和CLI测试 |
| Git | 2.46.2.windows.1 | 已初始化本地main，无提交和远端 |
| Python | `C:/Python313/python.exe` | 已运行标准库黑盒测试；pypdf等文档依赖另行按需定位 |
| CMake/Ninja/Clang/MSVC cl | 本轮PATH查询未发现 | 不表示整机未安装；只有实际需要时再检查/配置 |
| 网络接口 | 有9月29日使用记录 | 本轮未发送新的Grok请求，不能声称10月1日接口可用性已验证 |

## 工程构建与验证

```powershell
pwsh -NoProfile -File ./scripts/build.ps1 -Configuration Debug
pwsh -NoProfile -File ./scripts/test.ps1 -Configuration Debug
pwsh -NoProfile -File ./scripts/test.ps1 -Configuration Release
pwsh -NoProfile -File ./scripts/run-case.ps1
```

GCC入口不要求CMake安装。`build.ps1 -Compiler ...`可指定GCC路径；`test.ps1 -Python ...`可指定Python。Windows命令行和文件适配层显式处理UTF-8/UTF-16，因此中文绝对路径和空格已测试。

另提供CMakeLists：具备CMake环境后可用`cmake -S . -B build/cmake`、`cmake --build build/cmake`、`ctest --test-dir build/cmake --output-on-failure`。本轮PATH未提供CMake命令，未执行该构建；这些命令和远端CI不计入本轮已通过结果。

## 离线项目检查命令

```powershell
pwsh -NoProfile -File ./scripts/check-project.ps1
```

检查根入口/必要文件、治理文档与专题的相对链接、PowerShell语法，以及来源索引中available=true的文件哈希。available=false的历史来源列为known gaps，不直接使检查失败。

## 新检索：先预览，再请求

已准备好RES-001的一条起始问题：[问题文件](../调研/prompts/20261001_res001_versions.txt)。

离线预览（不读密钥、不联网、不写结果）：

```powershell
pwsh -NoProfile -File ./调研/scripts/research.ps1 -Topic 20261001_res001_versions -CutoffDate 2026-10-01 -Brief -DryRun
```

实际联网，移除DryRun：

```powershell
pwsh -NoProfile -File ./调研/scripts/research.ps1 -Topic 20261001_res001_versions -CutoffDate 2026-10-01 -Brief
```

执行日期变化时，使用新的Topic/问题文件和明确的CutoffDate。Topic已有输出时会拒绝覆盖。`-PromptFile`允许指定另一份已准备的问题文件，`-ConfigPath`可显式指定配置位置；不要在命令里写密钥。

默认配置仍为 `E:/Demo/IDEA_collector/apikey/grok.txt`。模型默认沿用既有可用配置`grok-4.6`；若服务端变更，应据真实报错检查接口，不臆造成功。

`-MaxCalls`只控制提示中的目标调用次数，实际服务端可能超出，**不是硬限额**。超时/网关错误先记录并缩小问题；不能凭空把失败请求当作完成的搜索。

## 其他现有辅助脚本

| 脚本 | 作用 | 注意 |
|---|---|---|
| `调研/scripts/fetch_sources.ps1 -Manifest ...` | 按清单HTTP读取公开原文 | 已有同名文件会跳过；新日期用新ID；200也要判断是否真为正文 |
| `调研/scripts/index_sources.ps1` | 根据清单重建来源索引/哈希 | **不是只读核验工具**；先查旧索引，不能用重建掩盖不明文件变化 |
| `调研/scripts/fetch_papers.ps1` | 下载已列的5份PDF | 现有文件跳过；目前均已有，无需重下 |
| `调研/scripts/extract_papers.py` | PDF转文本 | 需要pypdf；只提取文字，不能替代公式/图表视觉核对 |
| `调研/工具/Invoke-GrokResearch.ps1` | 历史研究入口 | 会按OutputStem写文件，保护措施较少；保留供追溯，不推荐新任务使用 |

## 后续环境工作

OPS-001的本地GCC路径已完成。后续按实际需要验证CMake、Linux/CI或新增依赖，不把配置文件存在当成测试已通过。当前没有后台计算服务、任务调度或自动监控安排。重复运行同一RunId会拒绝，必须使用新ID保留历史结果。
