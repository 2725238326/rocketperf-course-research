"""Browser preview of the desktop GUI against the real C bridge.

Serves the page assembled exactly as rocketperf-gui.exe assembles it (order from
src/gui/gui.rc) and forwards POST /rp to a persistent gui_bridge_stdio
process, so every number in the preview comes from the same C code.

    python tools/gui_build.py --bridge-only
    python tools/gui_dev.py [--port 8735] [--root WORKTREE]
"""
from __future__ import annotations

import argparse
import http.server
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET = re.compile(r'^\s*(\d+)\s+RCDATA\s+"([^"]+)"', re.M)


def assets(root: Path) -> list[tuple[int, Path]]:
    text = (root / "src/gui/gui.rc").read_text(encoding="utf-8")
    return [(int(i), root / "src/gui" / p) for i, p in ASSET.findall(text)]


def assemble(root: Path) -> str:
    items = assets(root)
    page = next(p for i, p in items if i == 100).read_text(encoding="utf-8")
    style = "\n".join(p.read_text(encoding="utf-8") for i, p in items if 101 <= i < 200)
    script = "\n".join(p.read_text(encoding="utf-8") for i, p in items if 201 <= i < 300)
    for marker in ("/*STYLE*/", "/*SCRIPT*/"):
        if page.count(marker) != 1:
            raise ValueError(f"index.html must contain exactly one {marker}")
    return page.replace("/*STYLE*/", style).replace("/*SCRIPT*/", script)


class Bridge:
    def __init__(self, exe: Path, cwd: Path):
        self.lock = threading.Lock()
        self.proc = subprocess.Popen([str(exe)], cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, encoding="utf-8", bufsize=1)

    def call(self, line: str) -> str:
        with self.lock:
            assert self.proc.stdin and self.proc.stdout
            self.proc.stdin.write(line.replace("\n", " ") + "\n")
            self.proc.stdin.flush()
            return self.proc.stdout.readline()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8735)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--bridge", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    exe = args.bridge or (root / "build/gui/gui_bridge_stdio.exe")
    # Run a private copy so rebuilding build/gui/ is never blocked by this server.
    private = Path(tempfile.mkdtemp(prefix="rp-gui-dev-")) / exe.name
    shutil.copy2(exe, private)
    bridge = Bridge(private, root)

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, kind: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?")[0] not in ("/", "/index.html"):
                self._send(404, b"not found", "text/plain")
                return
            self._send(200, assemble(root).encode("utf-8"), "text/html; charset=utf-8")

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/rp":
                self._send(404, b"not found", "text/plain")
                return
            size = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(size).decode("utf-8")
            self._send(200, bridge.call(body).encode("utf-8"), "application/json; charset=utf-8")

        def log_message(self, *_: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"GUI preview on http://127.0.0.1:{args.port} (bridge {exe})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
