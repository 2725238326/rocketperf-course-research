# 标签检出交接身份修正

日期：2026-10-07，GOV-004。阶段18e351b在远端main与维护分支的两次Windows CI成功；tag触发的run37499015905在handoff组失败。checkout标签使用detached HEAD，`git branch --show-current`为空，而包核验要求非空身份。

交接记录对detached HEAD使用`HEAD`，bundle只保存已有HEAD引用；普通分支仍保存分支引用并核对，两种路径不混用。新增回归覆盖空本地分支但固定提交的接收包。C生产源码和阶段ZIP未改变，stage-20261007仍固定18e351b；最新维护提交经本地完整质量和远端Windows CI核验后同步。
