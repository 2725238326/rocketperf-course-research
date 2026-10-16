"""Re-inject the live-panel config into the standalone HTML."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "docs/architecture/rocketperf-live-panel.html").read_text(encoding="utf-8")
cfg = (ROOT / "docs/architecture/rocketperf-live-panel.config.json").read_text(encoding="utf-8").strip()

new, n = re.subn(r'(<script id="live-config" type="application/json">).*?(</script>)',
                 lambda m: m.group(1) + cfg + m.group(2), html, count=1, flags=re.S)
if n != 1:
    raise SystemExit("inject failed: config script tag not found")
(ROOT / "docs/architecture/rocketperf-live-panel.html").write_text(new, encoding="utf-8", newline="\n")
print("injected, size", len(new))
