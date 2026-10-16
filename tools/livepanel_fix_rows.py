"""Put the Isp bar back, scaled so it stays inside the nozzle box."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "docs/architecture/rocketperf-live-panel.config.json"
cfg = json.loads(p.read_text(encoding="utf-8"))

cfg["machines"]["isp_gauge"] = {
    "type": "gauge", "period": 6.0, "threshold": 318.0, "decimals": 1, "t0": 1.2,
    "values": [324.4, 310.6, 296.3, 291.1],
    "low": {"label": "RP-1 口径"}, "high": {"label": "甲烷口径"},
    "lowColor": "ye", "highColor": "gr", "log": None,
}

ROW = {"items": [
    {"w": 40, "runs": [{"t": "Isp", "c": "dim"}]},
    {"w": 140, "bar": {"gauge": "isp_gauge", "w": 140, "h": 18, "max": 340}},
    {"w": 90, "align": "right", "runs": [{"v": "isp_gauge", "c": "gr", "b": 1}]}],
    "indent": 8, "gap": 8}

for el in cfg["elements"]:
    if el.get("type") != "box":
        continue
    title = next((l.get("t") for l in el.get("lines", []) if isinstance(l, dict) and l.get("t")), "")
    if title == "nozzle · 喷管":
        el["lines"] = [l for l in el["lines"] if not (isinstance(l, dict) and l.get("items"))]
        el["lines"].append(ROW)

p.write_text(json.dumps(cfg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("gauge restored, scaled to 340")
