"""Capture previously discovered cycle-source URLs; no search or credential access."""
from __future__ import annotations

import argparse
from pathlib import Path
import urllib.request

from projectlib import ROOT, atomic_json, digest, now, read_json


def capture(destination: Path):
    destination.mkdir(parents=True, exist_ok=False)
    index = read_json(ROOT / "调研/原始来源/来源文件索引.json")
    selected = ("V09_zq3_y1", "V11_tq15a", "V06_casc_engines", "L07_yf100_cmse", "L06_tq12a_crossref")
    manifest = dict(kind="existing_source_http_recheck", status="RUNNING", started_at=now(),
                    note="Grok topics 13/14 returned no web_search trace; only known original URLs are read here.", sources=[])
    atomic_json(destination / "manifest.json", manifest)
    for source_id in selected:
        source = next(s for s in index if s["id"] == source_id)
        entry = dict(id=source_id + "_20261012", original_id=source_id, url=source["url"])
        try:
            request = urllib.request.Request(source["url"], headers={"User-Agent": "CourseResearch/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                data = response.read(2_000_001)
                if len(data) > 2_000_000:
                    raise ValueError("Source exceeds capture size limit")
                entry.update(http_status=response.status, final_url=response.url)
            path = destination / (source_id + ".txt")
            path.write_bytes(data)
            entry.update(status="CAPTURED", file=path.relative_to(ROOT).as_posix(), sha256=digest(path), bytes=len(data))
        except Exception as exc:
            entry.update(status="UNAVAILABLE", error=str(exc))
        manifest["sources"].append(entry)
        atomic_json(destination / "manifest.json", manifest)
        print(source_id, entry["status"], flush=True)
    manifest.update(status="COMPLETE", finished_at=now())
    atomic_json(destination / "manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    capture(args.destination.resolve())
