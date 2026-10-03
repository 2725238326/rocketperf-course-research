# 2026-10-02_011：C核心代码质量复审

这不是普通质量入口的重复记录，而是针对 `IMP-001` 新增代码的独立边界审查。

## 发现并修复

1. S1 网格 CSV 解析器原先接受尾逗号（如 `1,`）；现已拒绝，并加入 CLI 回归测试。
2. `strtod` 原先接受十六进制浮点字面量（如 `0x1p0`），与算例契约的十进制/科学计数法要求冲突；现已加入显式十进制词法检查。
3. 扫描 API 原先在基础输入非法或网格容量不足时没有明确重置 `point_count`；现已失败时清零。
4. 扫描报告写出函数原先不检查点数是否等于笛卡尔积，也不检查点状态/错误诊断合法性；现已增加契约检查。
5. 增加成功/越域点 JSON 字段集合、坐标顺序和错误字段的黑盒断言。

## 已执行检查

- GCC 14.2：`-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes`。
- 加严编译：`-Wformat=2 -Wundef -Wnull-dereference -Wdouble-promotion -Wcast-qual -Wwrite-strings -Wformat-security -fanalyzer`，所有 C 源文件通过。
- Debug/Release 构建及 C 核心、CLI 测试通过；当前核心测试 202 checks，无失败。
- 32×32 网格压力测试通过，输出 1024 个点；超过32个网格轴值返回用法错误。
- CSV 边界集合通过：十进制/科学计数法合法值、空值、尾逗号、空元素、NaN/Inf、溢出、十六进制和尾随字符。

## 未完成而不能宣称通过的检查

当前 MinGW 工具链缺少 `libasan`/`libubsan`，AddressSanitizer/UndefinedBehaviorSanitizer 链接失败；因此本机不能宣称 Sanitizer 通过。Linux GCC sanitizer、Clang/clang-tidy、Valgrind 和远端 CI 仍应在相应环境实际执行后再更新结论。

## 剩余审查边界

当前 C 核心没有动态内存分配；CLI 的 Windows 参数转换和研究网格使用固定上限数组。JSON 写出仍直接面向 stdout，极端 I/O 故障可能产生截断输出，但正常成功/失败协议和运行追溯入口已经覆盖。若后续引入更长报告或文件输出，应改成临时缓冲后原子提交。
