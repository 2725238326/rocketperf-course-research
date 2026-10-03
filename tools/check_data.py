"""Validate parameter and assumption datasets against the project evidence contract."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
ROLES = {"fact", "derived", "assumption", "unknown", "synthetic_benchmark"}
REQUIRED_RECORD_FIELDS = {
    "id", "object", "variant", "stage", "parameter", "value", "unit",
    "data_role", "operating_boundary", "source_refs", "model_use", "notes",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_dataset(path: Path, source_index_path: Path) -> list[str]:
    problems: list[str] = []
    try:
        dataset = load(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read dataset: {exc}"]
    try:
        source_index = load(source_index_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read source index: {exc}"]
    if not isinstance(dataset, dict):
        return ["dataset must be an object"]
    if dataset.get("schema_version") != 1:
        problems.append("schema_version must be 1")
    records = dataset.get("records")
    if not isinstance(records, list) or not records:
        problems.append("records must be a non-empty array")
        records = []
    known_sources = {item.get("id") for item in source_index if isinstance(item, dict) and item.get("available")}
    short_sources = {source.split("_")[0] for source in known_sources if isinstance(source, str)}
    ids: set[str] = set()
    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        if not isinstance(record, dict):
            problems.append(f"{prefix}: must be an object")
            continue
        missing = REQUIRED_RECORD_FIELDS - set(record)
        for field in sorted(missing):
            problems.append(f"{prefix}: missing {field}")
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id.strip():
            problems.append(f"{prefix}: id must be non-empty")
        elif record_id in ids:
            problems.append(f"{prefix}: duplicate id {record_id}")
        else:
            ids.add(record_id)
        role = record.get("data_role")
        if role not in ROLES:
            problems.append(f"{prefix}: invalid data_role {role!r}")
        refs = record.get("source_refs")
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            problems.append(f"{prefix}: source_refs must be a non-empty string array")
        elif any(ref not in known_sources and ref not in short_sources and not ref.startswith(("docs/", "调研/", "RES-", "DATA-")) for ref in refs):
            bad = [ref for ref in refs if ref not in known_sources and ref not in short_sources and not ref.startswith(("docs/", "调研/", "RES-", "DATA-"))]
            problems.append(f"{prefix}: unknown source_refs {bad}")
        unit = record.get("unit")
        if not isinstance(unit, str) or not unit.strip():
            problems.append(f"{prefix}: unit must be non-empty")
        boundary = record.get("operating_boundary")
        if not isinstance(boundary, str) or not boundary.strip():
            problems.append(f"{prefix}: operating_boundary must be non-empty")
        if not isinstance(record.get("model_use"), str) or not record["model_use"].strip():
            problems.append(f"{prefix}: model_use must be non-empty")
        if not isinstance(record.get("notes"), str) or not record["notes"].strip():
            problems.append(f"{prefix}: notes must be non-empty")
        if role == "assumption":
            model_id = record.get("model_id")
            value_range = record.get("range")
            if not isinstance(model_id, str) or not model_id.strip():
                problems.append(f"{prefix}: assumption requires model_id")
            if not isinstance(value_range, dict) or not finite(value_range.get("min")) or not finite(value_range.get("max")):
                problems.append(f"{prefix}: assumption requires finite range.min/range.max")
            elif value_range["min"] > value_range["max"]:
                problems.append(f"{prefix}: assumption range.min > range.max")
            if not isinstance(record.get("rationale"), str) or not record["rationale"].strip():
                problems.append(f"{prefix}: assumption requires rationale")
        if role in {"fact", "derived", "synthetic_benchmark"} and isinstance(record.get("value"), (int, float)):
            if not finite(record["value"]):
                problems.append(f"{prefix}: numeric value must be finite")
    if not isinstance(dataset.get("missing_real_engine_fields"), list):
        problems.append("missing_real_engine_fields must be an array")
    if not isinstance(dataset.get("missing_value_policy"), str) or not dataset["missing_value_policy"].strip():
        problems.append("missing_value_policy must be non-empty")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--source-index", type=Path, default=ROOT / "调研/原始来源/来源文件索引.json")
    args = parser.parse_args()
    problems = validate_dataset(args.dataset, args.source_index)
    report = {"dataset": args.dataset.as_posix(), "status": "PASS" if not problems else "FAIL", "problems": problems}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
