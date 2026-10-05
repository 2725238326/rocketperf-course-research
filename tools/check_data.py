"""Validate parameter and assumption datasets against the project evidence contract."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

from projectlib import local_path, read_json


ROOT = Path(__file__).resolve().parents[1]
ROLES = {"fact", "derived", "assumption", "unknown", "synthetic_benchmark"}
REQUIRED_RECORD_FIELDS = {
    "id", "object", "variant", "stage", "parameter", "value", "unit",
    "data_role", "operating_boundary", "source_refs", "model_use", "notes",
}


def load(path: Path):
    return read_json(path)


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_dataset(path: Path, source_index_path: Path, root=ROOT) -> list[str]:
    problems: list[str] = []
    try:
        dataset = load(path)
    except (OSError, ValueError) as exc:
        return [f"cannot read dataset: {exc}"]
    try:
        source_index = load(source_index_path)
    except (OSError, ValueError) as exc:
        return [f"cannot read source index: {exc}"]
    if not isinstance(dataset, dict):
        return ["dataset must be an object"]
    if type(dataset.get("schema_version")) is not int or dataset["schema_version"] != 1:
        problems.append("schema_version must be 1")
    if not isinstance(source_index, list):
        return ["source index must be an array"]
    if any(not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id'].strip()
           or type(item.get('available')) is not bool for item in source_index):
        return ["source index entries require nonempty id and boolean available"]
    source_ids = [item["id"] for item in source_index]
    if len(source_ids) != len(set(source_ids)):
        return ["source index contains duplicate ids"]
    records = dataset.get("records")
    if not isinstance(records, list) or not records:
        problems.append("records must be a non-empty array")
        records = []
    known_sources = {item.get("id") for item in source_index if isinstance(item, dict) and item.get("available")}
    short_sources = {source.split("_")[0] for source in known_sources if isinstance(source, str)}
    tasks = {t['id'] for t in read_json(root / 'project/tasks.json')['tasks']} if (root / 'project/tasks.json').is_file() else set()
    def reference_exists(ref):
        if ref in known_sources or ref in short_sources or ref in tasks:
            return True
        if ref.startswith(('docs/', '调研/')):
            try:
                return local_path(root, ref.split('#', 1)[0]).is_file()
            except ValueError:
                return False
        return False
    def valid_value(value):
        if type(value) in (int, float): return finite(value)
        if isinstance(value, str): return bool(value.strip())
        if isinstance(value, dict): return bool(value) and all(valid_value(x) for x in value.values())
        if isinstance(value, list): return bool(value) and all(valid_value(x) for x in value)
        return False
    def bounded(value, bounds):
        return (finite(value) and isinstance(bounds, dict) and set(bounds) == {'min','max'}
                and finite(bounds['min']) and finite(bounds['max'])
                and bounds['min'] <= value <= bounds['max'])
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
        if not isinstance(role,str) or role not in ROLES:
            problems.append(f"{prefix}: invalid data_role {role!r}")
        refs = record.get("source_refs")
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            problems.append(f"{prefix}: source_refs must be a non-empty string array")
        elif any(not reference_exists(ref) for ref in refs):
            bad = [ref for ref in refs if not reference_exists(ref)]
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
        value = record.get('value')
        if role == 'unknown':
            if value is not None: problems.append(f'{prefix}: unknown value must be null')
        elif not valid_value(value):
            problems.append(f'{prefix}: value must contain finite numbers or nonempty descriptive text; no boolean/null')
        if role == "assumption":
            model_id = record.get("model_id")
            value_range = record.get("range")
            if not isinstance(model_id, str) or not model_id.strip():
                problems.append(f"{prefix}: assumption requires model_id")
            if isinstance(value, dict):
                valid = (isinstance(value_range,dict) and set(value_range)==set(value)
                         and all(bounded(x,value_range[key]) for key,x in value.items()))
            else:
                valid = bounded(value,value_range)
            if not valid:
                problems.append(f"{prefix}: assumption requires finite range.min/range.max and value within each field range")
            if not isinstance(record.get("rationale"), str) or not record["rationale"].strip():
                problems.append(f"{prefix}: assumption requires rationale")
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
