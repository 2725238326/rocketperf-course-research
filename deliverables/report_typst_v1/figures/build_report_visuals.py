"""Capture report illustrations without altering the original GUI screenshots.

Default: recapture the architecture and verify the saved, reviewed GUI images.
To refresh the GUI, supply --gui-root and --bridge for its actual C preview.
The browser uses reduced motion and waits for all C replies before capture.
"""
from __future__ import annotations

import argparse
import hashlib
import http.server
import importlib.util
import json
import re
import subprocess
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
QA = ROOT / "build" / "report-qa" / "live-panel"
GUI_SCREENS = (
    ("fig09_gui_combustion.png", "chamber", "氧燃比:0.9"),
    ("fig10_gui_propellant.png", "propellant", "报告口径"),
    ("fig11_gui_nozzle.png", "nozzle", "海平面 ε40"),
    ("fig12_gui_cycle-orsc.png", "cycle", "长十乙一级"),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_architecture(refresh: bool = False) -> dict[str, object]:
    QA.mkdir(parents=True, exist_ok=True)
    source = ROOT / "docs" / "architecture" / "rocketperf-live-panel.html"
    selected = OUT / "fig08_dynamic_architecture.png"
    # Use explicit Windows fonts in a derived copy: the upstream Linux font
    # fallback was too wide, truncating the independent-branch annotations.
    # Two six-line boxes also need room for their last row. Source HTML and
    # scientific content stay unchanged; this derived copy is for the PDF only.
    derived = OUT / "architecture-report.html"
    if derived.exists() and not refresh:
        old = json.loads((OUT / "report-visuals-manifest.json").read_text(encoding="utf-8"))["architecture"]
        if sha256(derived) != old["report_animation_sha256"]:
            raise ValueError("Saved report animation changed; use --refresh-architecture to explicitly refresh from source")
        source_hash = old["source_sha256"]
    else:
        html = source.read_text(encoding="utf-8")
        match = re.search(r'(<script id="live-config" type="application/json">)(.*?)(</script>)', html, re.S)
        if match is None:
            raise ValueError("architecture config not found")
        config = json.loads(match[2])
        config["theme"].update({
            "font": '"Consolas","Microsoft YaHei",monospace',
            "titleFont": '"Microsoft YaHei",sans-serif',
            "fontSize": 20,
        })
        config["theme"]["colors"].update({"dim": "#aab1c0"})
        for element in config["elements"]:
            if element["type"] == "box" and element.get("y") in (433, 751) and len(element.get("lines", [])) == 6:
                element["h"] = 205
            if element["type"] == "rule" and element.get("y") == 112:
                element["y"] = 138
        notice = "<!-- Report adaptation of live-panel-skill; Copyright (c) 2026 live-panel contributors. MIT License: architecture-LICENSE-MIT.txt. -->\n"
        derived.write_text(notice + html[:match.start(2)] + json.dumps(config, ensure_ascii=False) + html[match.end(2):], encoding="utf-8")
        source_hash = sha256(source)
    capture_seconds = (4, 14, 24)
    qa_frames: dict[str, str] = {}
    layout_checks: dict[str, object] = {}
    animation_issues: dict[str, object] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 1500}, device_scale_factor=2)
        page.goto(derived.resolve().as_uri() + "?manual", wait_until="load")
        page.wait_for_function("window.__ready === true", timeout=15000)
        page.evaluate("document.fonts.ready")
        for tick in range(121):
            seconds = tick / 4
            issues = page.evaluate("t => { window.seek(t); return window.__check(); }", seconds)
            if issues:
                animation_issues[str(seconds)] = issues
        if animation_issues:
            raise ValueError(f"Animation layout issues: {animation_issues}")
        for seconds in capture_seconds:
            page.evaluate("t => window.seek(t)", seconds)
            page.wait_for_timeout(120)
            frame = QA / f"architecture-t{seconds:02d}.png"
            page.screenshot(path=str(frame), full_page=True, animations="disabled")
            qa_frames[str(seconds)] = frame.relative_to(ROOT).as_posix()
            layout_checks[str(seconds)] = page.evaluate("window.__check()")
        # At 24 s the typewriter annotations have finished and the GG dashboard
        # shows its complete saved result, without partially typed words.
        page.evaluate("t => window.seek(t)", 24)
        page.wait_for_timeout(120)
        page.screenshot(path=str(selected), full_page=True, animations="disabled")
        browser.close()
    return {
        "file": selected.name,
        "source": source.relative_to(ROOT).as_posix(),
        "capture_seconds": list(capture_seconds),
        "selected_frame_seconds": 24,
        "animation_period_seconds": 30,
        "source_sha256": source_hash,
        "report_animation_file": derived.name,
        "report_animation_sha256": sha256(derived),
        "typography_adaptation": "Explicit Consolas/Microsoft YaHei fonts, 20px base, brighter secondary labels, two six-line boxes expanded to 205px, header rule below subtitle/legend; source content and animation timing retained.",
        "layout_checks": layout_checks,
        "animation_layout_samples": 121,
        "animation_layout_issues": animation_issues,
        "qa_frames": qa_frames,
        "sha256": sha256(selected),
    }


def capture_gui(gui_root: Path, bridge_exe: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Read the GUI worktree; all generated evidence stays in this repository."""
    spec = importlib.util.spec_from_file_location("report_gui_preview", gui_root / "tools/gui_dev.py")
    if spec is None or spec.loader is None:
        raise ValueError("GUI preview module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assembled = module.assemble(gui_root)
    (QA / "gui-source.html").write_text(assembled, encoding="utf-8")
    bridge = module.Bridge(bridge_exe, gui_root)
    replies: list[dict[str, object]] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = assembled.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            request = self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
            response = bridge.call(request)
            replies.append({"request": json.loads(request), "response": json.loads(response)})
            body = response.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    records: list[dict[str, object]] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2, reduced_motion="reduce")
            for filename, tab, preset in GUI_SCREENS:
                page = context.new_page()
                page.goto(url + "#" + tab, wait_until="networkidle")
                page.wait_for_function("document.querySelector('.view:not([hidden]) .kpi .v, .view:not([hidden]) .refused') !== null")
                page.evaluate("value => applyPreset(value)", preset)
                page.wait_for_timeout(500)
                page.wait_for_load_state("networkidle")
                page.wait_for_function("!document.querySelector('#calc.busy, #calc.fail')")
                page.evaluate("document.fonts.ready")
                page.mouse.move(1900, 1060)
                target = OUT / filename
                page.screenshot(path=str(target), animations="disabled")
                visible = page.locator(".view:not([hidden])")
                kpis = visible.locator(".kpi").all_inner_texts()
                if tab == "cycle":
                    # Check display against the C response, not against another
                    # label that might contain the same stale presentation bug.
                    response = next(r["response"] for r in reversed(replies)
                                    if r["request"]["cmd"] == "cycle" and r["request"]["args"]["case"].endswith("cz10b_first_stage1.ini"))
                    result = response["result"]
                    expected = (result["balance"]["total_thrust"] / 1e3,
                                result["balance"]["isp"],
                                result["balance"]["turbine_power"] / 1e6,
                                result["turbine"]["out_p"] / 1e6)
                    for value, decimals, text in zip(expected, (2, 2, 3, 2), kpis):
                        if f"{value:.{decimals}f}" not in text.replace(",", ""):
                            raise ValueError(f"GUI KPI not settled: {text!r}; C expects {value}")
                with Image.open(target) as im:
                    width, height = im.size
                records.append({
                    "file": filename, "source": "GUI browser preview with the actual C bridge",
                    "tab": tab, "preset": preset, "viewport_css_px": [1920, 1080],
                    "device_scale_factor": 2, "reduced_motion": True,
                    "kpi_text": kpis, "width": width, "height": height, "sha256": sha256(target),
                })
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        bridge.proc.terminate()
        bridge.proc.wait(timeout=10)
    (QA / "gui-c-replies.json").write_text(json.dumps(replies, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=gui_root, capture_output=True, text=True, check=True).stdout.strip()
    provenance = {
        "gui_worktree": str(gui_root), "git_head": head,
        "assembled_html_sha256": hashlib.sha256(assembled.encode("utf-8")).hexdigest(),
        "bridge_sha256": sha256(bridge_exe),
        "capture_method": "Identical desktop page resources, localhost C bridge, all replies complete, reduced motion; no numerical labels edited for capture.",
        "raw_replies": (QA / "gui-c-replies.json").relative_to(ROOT).as_posix(),
    }
    return records, provenance


def verify_saved_gui() -> tuple[list[dict[str, object]], dict[str, object]]:
    previous = json.loads((OUT / "report-visuals-manifest.json").read_text(encoding="utf-8"))
    records = previous["gui_screens"]
    for record in records:
        if sha256(OUT / record["file"]) != record["sha256"]:
            raise ValueError(f"GUI image changed since reviewed capture: {record['file']}")
    return records, previous["gui_provenance"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gui-root", type=Path)
    parser.add_argument("--bridge", type=Path)
    parser.add_argument("--refresh-architecture", action="store_true", help="Explicitly rebuild the report animation from docs/architecture source")
    args = parser.parse_args()
    if bool(args.gui_root) != bool(args.bridge):
        parser.error("--gui-root and --bridge must be supplied together")
    architecture = snapshot_architecture(args.refresh_architecture)
    if any(architecture["layout_checks"].values()):
        raise ValueError(f"Architecture layout check failed: {architecture['layout_checks']}")
    gui, provenance = capture_gui(args.gui_root.resolve(), args.bridge.resolve()) if args.gui_root else verify_saved_gui()
    manifest = {
        "schema_version": 2,
        "architecture": architecture,
        "gui_screens": gui,
        "gui_provenance": provenance,
        "notes": [
            "The dynamic HTML is sampled at 4, 14 and 24 seconds; the report uses the 24-second frame with complete typewriter annotations.",
            "The cycle screenshot shows the Changzheng-10B first-stage oxygen-rich staged-combustion research scenario.",
            "Original deliverables/gui-shots images remain unchanged. The report uses fresh, settled captures; screenshots illustrate the interface, not independent scientific validation.",
        ],
    }
    (OUT / "report-visuals-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    action = "recaptured" if args.gui_root else "verified saved"
    print(f"saved architecture frame; {action} {len(gui)} GUI screens")


if __name__ == "__main__":
    main()
