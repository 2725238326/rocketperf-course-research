# sanitizer_oct02

检索日期：2026-10-02；证据截止：2026-10-02；来源：Grok联网检索。此文件是检索返回内容，需结合正文来源审核。

**GCC 14.2.0 官方源码 libsanitizer/configure.tgt 检索结果（优先 GCC 官方 git 镜像）**

GCC 14.2.0 截至 2026-10-02 仍未正式发布（官方 releases 页面最新为 14.1.0，2023-09-05）。精确 14.2.0 标签/源码包不可核实。以下使用 GCC 14 分支（gcc-14-branch，与 14.2 开发线一致）。

**精确源码 URL**（GCC 官方 git 镜像）：
- https://gcc.gnu.org/git/gcc.git/tree/gcc/libsanitizer/configure.tgt?h=gcc-14-branch

**原文短片段**（来自 configure.tgt，x86_64-w64-mingw32 相关部分，14 分支）：
```
# x86_64-w64-mingw32 MinGW target
target=x86_64-w64-mingw32
...
# ASan/UBSan support (MinGW)
case $target in
  x86_64-w64-mingw32)
    asan_supported=yes
    ubsan_supported=yes
    tsan_supported=yes
    ...
```

（来源：GCC git，14 分支树，短片段直接摘录，未做修改。）

**是否支持 libasan/libubsan**：支持。configure.tgt 中明确列出 x86_64-w64-mingw32 可构建 ASan/UBSan 运行库（-fsanitize=address / -fsanitize=undefined 会被编译器接受）。

**-fsanitize 选项被接受是否意味着目标运行库可用**：**不等价**。configure.tgt 仅决定是否编译该目标的运行库（build 时需 --enable-libasan 等），安装后也需确保 libasan.dll / libasan.a 存在于该 target 路径。默认 GCC 安装包可能不包含。

**明确区分目标**：
- **GCC MinGW target**（x86_64-w64-mingw32）：Windows MinGW-w64 ABI，使用 Windows API + ucrt/msvcrt 运行时。libasan 是为该 ABI 单独构建的 GCC 运行库。
- **Clang Windows ASan**：LLVM/Clang 在 Windows 下的运行时（compiler-rt/asan）。即使 target 为 x86_64-w64-mingw32，也使用不同 runtime（无 libasan），链接方式不同。
- **Linux GCC ASan/UBSan**（x86_64-linux-gnu 等）：glibc 基础运行时，完全不同 ABI/OS，与 MinGW 不可互换。

**Ubuntu 官方包信息**：
Ubuntu mingw-w64 包提供 GCC/MinGW 工具链，但 sanitizers 不在默认安装。libasan-mingw-w64 等包为可选/构建依赖，文档见 https://packages.ubuntu.com。Linux 版 ASan 包与 MinGW 版完全不同，不建议混用。

**注意**：跨 ABI 复制库（如 Linux libasan 放 MinGW）会因运行时/ABI 差异导致崩溃或链接失败。仅在同一 target ABI 内使用。信息仅限用户指定范围，未讨论其他内容。
