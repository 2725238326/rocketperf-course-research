# 运行结果

日常运行由tools/pipeline.py（PowerShell兼容入口run-case.ps1）写入local/RunId，忽略版本控制。RunId原子占用，禁止覆盖。

每次记录输入、具体已测试二进制、构建/测试manifest、stdout/stderr、结果与哈希。PREPARING或RUNNING阶段失败也要形成FAILED记录；仅能解析JSON不能算成功，必须满足协议及输入对应关系。

现行运行manifest为v2，旧v1记录原样保留。`validation/`固定方法证据，`research/`固定研究版本，`local/`仅试跑。现有方法包括空气、气态热化学/冻结喷管与合成外排计账；全部都不等于朱雀三号或长征十号乙实测性能。
