"""Snapshot existing C outputs; plotting needs only the resulting local data."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(__file__).resolve().parents[1] / "data"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    page = ROOT / "deliverables/demo/index.html"
    match = re.search(r'<script id="rp-data"[^>]*>(.*?)</script>', page.read_text(encoding="utf-8"), re.S)
    if not match:
        raise ValueError("Saved demo payload not found")
    saved = json.loads(match.group(1))
    demo = {key: saved[key] for key in ("axes", "chamber", "grid", "cycles", "provenance")}
    sources = [{"path": page.relative_to(ROOT).as_posix(), "sha256": digest(page),
                "role": "saved C sweep, refusals and cycle balance; six significant digits"}]
    (DATA / "saved-demo-results.json").write_text(json.dumps(demo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    inlets = []
    for key, label, tf, to in (("base", "基线", 120, 100), ("fuel_hot", "仅甲烷升温", 140, 100),
                              ("oxidizer_hot", "仅氧升温", 120, 110), ("both_hot", "两路同时升温", 140, 110)):
        source = ROOT / f"results/validation/liquid_combustion_v1/{key}_A10-stdout.txt"
        result = json.loads(source.read_text(encoding="utf-8"))
        inlets.append({"case": key, "label": label, "fuel_temperature_k": tf,
                       "oxidizer_temperature_k": to, "result": result})
        sources.append({"path": source.relative_to(ROOT).as_posix(), "sha256": digest(source),
                        "role": "full-precision archived C result"})
    (DATA / "inlet-response.json").write_text(json.dumps(inlets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pair = ROOT / "results/research/propellant_comparison_v1/common_2_6_A10_p0_pair-stdout.json"
    (DATA / pair.name).write_bytes(pair.read_bytes())
    sources.append({"path": pair.relative_to(ROOT).as_posix(), "sha256": digest(pair),
                    "role": "full-precision paired C result; copied byte-for-byte"})
    manifest = {"schema_version": 1, "snapshot_date": "2026-10-16", "sources": sources,
                "notes": ["Snapshot does not refresh online vehicle evidence.",
                          "Refusal activities printed by C have three significant digits; no interpolated carbon boundary.",
                          "Prescribed-temperature cycle and ideal-gas diagnostic are not merged with HP results."],
                "files": [{"path": p.name, "sha256": digest(p), "bytes": p.stat().st_size}
                          for p in sorted(DATA.iterdir()) if p.is_file() and p.name != "manifest.json"]}
    (DATA / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(sources)} source identities and {len(manifest['files'])} local data files")


if __name__ == "__main__":
    main()
