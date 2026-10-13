# GitHub与Windows阶段交付

当前工作只生成本地可核验的阶段源码/Windows包；远端同步、GitHub Release和外部下载仍须用户另行明确授权。仓库地址作为历史交付背景保留；最终课程报告/PPT和后续计算按任务推进。

## 下载内容

| 文件 | 用途 | 所需环境 |
|---|---|---|
| rocketperf-c-source.zip | C17源码、C测试、CMake登记、算例、固定数据声明和项目解读 | Windows GCC、CMake、Ninja；不要求Python |
| rocketperf-windows-x64.zip | 已测exe、演示输入/输出、说明和源数据许可 | Windows x64；不要求编译器/Python |
| delivery-manifest.json、SHA256SUMS.txt | 固定提交、二进制、ZIP与逐文件哈希、重建/运行检查记录 | 下载后核对 |
| project-guide.md | 详细研究/程序/验证解读；两包也内含 | 文本/Markdown阅读器 |

完整资料与维护工具留在仓库，GitHub源码下载保留完整提交快照。轻量C源码包没有Python/Fortran文件或凭据、缓存、原始大课件；固定NASA9/液体数据已编入C。ZIP和exe通过Release附件分发，不提交Git历史。

## 包的生成与核验

```powershell
python tools/delivery.py create --destination build/delivery-NEW-ID
python tools/delivery.py verify --directory build/delivery-NEW-ID
```

create要求干净提交、新鲜完整质量和已测Release构建，生成两个ZIP后重新解压。源码在解压目录通过CMake禁用Python测试构建，并实际运行五个C测试；运行包在隔离PATH下运行菜单列出的算例、域评估、文本/交互、成功/拒绝及RP-1例。交付v3增加菜单8中的五个车辆研究算例和ASCII双击启动器，均纳入文件哈希；源码重建与运行包各有17项演示，其中启动器从其他当前目录调用并依次运行全部五例。车辆JSON使用已保存状态关系校核，不只看退出0。v1/v2保持可读，各自只代表当时固定能力。清单保存构建/测试身份、重建日志、输出哈希和Git提交。verify核对ZIP结构、哈希、源包C范围与记录，不等同另一个人的科学审查。

本机CMake/Ninja位于build/tooling；可用参数指定本机路径。接收者使用其自己的工具安装路径。不要把本机绝对路径当成每个人的配置。

## GitHub维护

如用户另行授权远端交付，再将固定提交推送到指定私有仓库并建立预发布；本地工作不执行推送。届时资产包括两个ZIP、清单、校验和和解读，所有更新保留Git历史，不强推、不删除旧分支/来源，不擅自增加开源许可证。

用户此前“未获授权不推送”的约束继续用于日常工作。历史远端交付不代表本轮新增更改已上传；后续自动推送不因此成为默认行为。

下载后先对照Release列出的SHA256与提交；仅相信包内自己的哈希不能证明出处。Windows包README给出直接运行命令，源码包README给出纯C编译命令。项目解读见[文档](project-guide.md)，型号/方法边界以既有专题为准。
