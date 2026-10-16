"""One-off: enrich the live-panel config (drop run counters, add thrust gauge and cycle mode)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "docs/architecture/rocketperf-live-panel.config.json"
cfg = json.loads(p.read_text(encoding="utf-8"))

# Output box: conservation residuals + CEA comparison instead of run counts
for el in cfg["elements"]:
    if el.get("type") == "box" and any(l.get("t") == "输出与验证" for l in el.get("lines", []) if isinstance(l, dict)):
        el["lines"][2] = {"t": "守恒残差全量核对", "c": "mute"}
        el["lines"][3] = {"t": "CEA同源对照", "c": "mute"}

# Footer: quality facts instead of check counts
for el in cfg["elements"]:
    if el.get("type") == "text" and el.get("y") == 1458:
        el["runs"] = [{"t": "守恒账  ", "c": "dim"}, {"t": "[", "c": "gr", "b": 1},
                      {"t": "质量·元素·焓·轴功", "c": "gr", "b": 1}, {"t": "]", "c": "gr", "b": 1},
                      {"t": "   越域拒算不外推  ·  失败不写结果", "c": "dim"}]

# Verify lane log
mach = cfg["machines"]["r30_输出与验证_l"]
mach["log"]["msgs"] = [["mass|elements|enthalpy|shaft closed", ""], ["CEA |dT| <= 0.0044 K (HP)", ""]]

# Credit line without counts
cfg["credit"]["text"] = "循环为条件性研究原型 · 数值为归档算例结果 · 失败与越域显式拒绝，不外推"

# Thrust/Isp gauge: archived propellant & cycle results alternate
cfg["machines"]["isp_gauge"] = {
    "type": "gauge", "period": 6.0, "threshold": 318.0, "decimals": 1, "t0": 1.2,
    "values": [324.4, 310.6, 296.3, 291.1],
    "low": {"label": "RP-1 口径"}, "high": {"label": "甲烷口径"},
    "lowColor": "ye", "highColor": "gr", "log": None,
}

# Cycle scenario alternation
cfg["machines"]["cycle_mode"] = {
    "type": "cycle", "period": 12.0, "t0": 0.0,
    "values": [
        {"m": "GG 开式外排  F=290.5 kN  Isp=296.3 s", "who": "cycle", "c": "ye"},
        {"m": "ORSC 富氧补燃  F=285.5 kN  Isp=291.1 s", "who": "cycle", "c": "bl"},
    ],
    "log": None,
}

p.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("config updated:", p)
