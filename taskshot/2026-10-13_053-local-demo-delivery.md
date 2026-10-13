# 收尾演示包的实际交付复验

日期：2026-10-13，QA-003。实际打包固定干净提交 `59123e520146d7dfa8de3ed6ba9b19dbd58aabda`；核心C源码没有在接收批次改动。

`python tools/delivery.py create --destination build/delivery-final-overview-20261013`成功，manifest schema_version=3/status=PASS；`verify`随后通过。源码重新解压、CMake/Ninja 51个目标构建成功，纯C的CTest 5/5；源码重建程序及运行包在隔离PATH各17项演示通过，含五个车辆JSON关系复核和启动器依次运行全部五例。

| 文件 | 字节 | SHA256 |
|---|---:|---|
| rocketperf-c-source.zip | 241820 | `b9eedcc8edc9ea2d07d5a7d98dd65e2ead86d5a47dadd6156b994666d46438e9` |
| rocketperf-windows-x64.zip | 304800 | `652c20c19b842052583d0211f5cb94b4ed64bd810cc83ad6fe5844714b07d1d1` |
| delivery-manifest.json | 以本地文件为准 | `402a1d9eb1cdc42bdd60f5904c36135a2e09908e54e621d34b52fea7af6b1b6d` |

源码/运行包分别98/108个清单文件。运行exe为已测Release，SHA256 `f66ec06d6bfb9249e158fd207b13cc12a47e760456ef713e8b2ae8d32163e3e8`；与其build/test报告和两个ZIP清单绑定，解决接收原包的旧证据混用问题。

最后从实际Windows ZIP解到 `build/delivery-received-20261013/`，在项目根调用解出的启动器、隔离PATH、标准输入依次选择菜单8/1–5/退出，退出0、stderr为空、五次“整机研究比冲”、无失败诊断，exe身份仍相同。没有模拟桌面点击或声称具名组员已经接收；验证的是实际bat与ZIP字节的运行。

统一质量 `build/quality/latest.json`六组PASS，报告SHA256 `16ed1fb604b5006c17886b71c2386f3d40060409162a39456b4d335f688ff5e9`、输入指纹 `7a1cf67d9f2573cf4818f90c339b3047f2991a498bd30966eb1391821dc7bcc5`。打包后质量新鲜度再次检查通过；本次新增历史快照和任务流转不改变有效源码/文档/档案指纹。

语义验收：交接改动、启动原因、包内证据、两型来源/假设及当前模型差别均有实际定位和复现；收尾总览给出可运行路径与最终报告/PPT/贡献/演练缺口。原始来源和ZIP保持字节，未外发、未推送。QA-003完成只代表这次接收/总览/本地演示更新，DOC-001及REL-001按各自尚未满足的契约继续。
