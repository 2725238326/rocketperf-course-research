"""One-off: wire the new gauge/cycle machines into the panel layout."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "docs/architecture/rocketperf-live-panel.config.json"
cfg = json.loads(p.read_text(encoding="utf-8"))

for el in cfg["elements"]:
    if el.get("type") == "box" and any(l.get("t") == "nozzle · 喷管" for l in el.get("lines", []) if isinstance(l, dict)):
        el["lines"].append({"items": [
            {"w": 60, "runs": [{"t": "Isp", "c": "dim"}]},
            {"w": 160, "bar": {"gauge": "isp_gauge", "w": 160, "h": 20}},
            {"grow": 1, "runs": [{"v": "isp_gauge", "c": "gr", "b": 1}]}]})
    if el.get("type") == "box" and any(l.get("t") == "cycle · 循环原型" for l in el.get("lines", []) if isinstance(l, dict)):
        el["lines"].append({"runs": [{"v": "cycle_mode", "b": 1}]})

# run log hears the scenario switches
cfg["machines"]["cycle_mode"]["log"] = {"who": "cycle", "c": "ye"}
for v in cfg["machines"]["cycle_mode"]["values"]:
    v["g"] = ""
p.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("layout wired")
