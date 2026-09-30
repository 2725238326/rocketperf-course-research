# 运行结果

日常运行由tools/pipeline.py（PowerShell兼容入口run-case.ps1）写入local/RunId，忽略版本控制。RunId原子占用，禁止覆盖。

每次记录输入、具体已测试二进制、构建/测试manifest、stdout/stderr、结果与哈希。PREPARING或RUNNING阶段失败也要形成FAILED记录；仅能解析JSON不能算成功，必须满足协议及输入对应关系。

现行manifest为v2，旧v1记录原样保留。正式研究结果选定后另建版本目录并说明证据，不把所有试跑都当课程成果。当前基准依旧是教学理想气体，不是朱雀三号或长征十号乙性能。
