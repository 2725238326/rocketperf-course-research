# 2026-10-13组员代码接收证据

工程接收清单见[manifest](manifest.json)，解释见[审阅](../../../docs/incoming-code-review.md)。本目录固定包内exe运行、源码重建、正常批处理逐提示输入、预期失败与跨构建数值核对；原ZIP和交接在日期化原始来源目录保存。`source_dirty=true`描述采集时待提交的治理/文档/打包修改，不冒充原包的Git提交身份。

`baseline_relation_count`为旧基准保存状态的关系检查数；`baseline_relation_names`保留实际比较项。新增补燃没有被传给旧外排validator；其七条质量/轴功/推力/能量代数复算及394项C循环检查各按自己的范围使用。温度由输入指定、燃料为甲烷代理，守恒残差不是实机或独立实验验证。

核对本目录文件哈希：

```powershell
@'
from pathlib import Path
import hashlib, json
p = Path('results/research/incoming_code_v1_20261013')
m = json.loads((p / 'manifest.json').read_text(encoding='utf-8'))
for f in m['files']:
    data = (p / f['path']).read_bytes()
    assert len(data) == f['bytes']
    assert hashlib.sha256(data).hexdigest() == f['sha256']
print('All declared incoming evidence hashes match.')
'@ | python -
```

manifest的PASS仅表示接收检查完成。`original_test_evidence_covers_current_exe=false`保留旧报告绑定错误，`original_bat_buffered_stdin`保留EOF超时；失败没有被清洗为成功。本机GCC14.2.0与交接方工具链不同，只证实622字段数值一致，不宣称exe字节相同。
