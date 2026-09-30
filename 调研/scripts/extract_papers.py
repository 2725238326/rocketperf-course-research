from pathlib import Path
from pypdf import PdfReader
import json
import logging
import sys

sys.stdout.reconfigure(encoding="utf-8")
logging.getLogger("pypdf").setLevel(logging.ERROR)

root = Path(__file__).resolve().parent.parent / "文献"
for source in sorted(root.glob("*.pdf")):
    target = source.with_suffix(".txt")
    reader = PdfReader(source)
    pages = [page.extract_text() or "" for page in reader.pages]
    if not target.exists():
        target.write_text("\n\n".join(f"[PDF PAGE {i + 1}]\n{page}" for i, page in enumerate(pages)), encoding="utf-8")
    print(json.dumps({"file": source.name, "pages": len(pages), "first_page": pages[0][:5000]}, ensure_ascii=False))
