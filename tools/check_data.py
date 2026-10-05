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


def validate_assignment_map(dataset: dict, known_sources: set[str], root: Path) -> list[str]:
    """Check associations, not whether external prose supports a scientific claim."""
    problems: list[str] = []
    objects = {
        "zq3_y1_stage1": ("ZQ-3", "遥一", "一级"),
        "zq3_y1_stage2": ("ZQ-3", "遥一", "二级"),
        "cz10b_first_stage1": ("CZ-10B", "首飞", "一级"),
        "cz10b_first_stage2": ("CZ-10B", "首飞", "二级"),
    }
    models = {
        "continuous_liquid_hp": "ch4_o2_continuous_liquid_hp_frozen_fixed_area_v1",
        "synthetic_cycle_trade": "prescribed_thermal_cycle_v1",
        "ideal_formula": "ideal_constant_gamma_v1",
    }
    if dataset.get("dataset_id") != "assignment-case-map-v1":
        problems.append("assignment map requires the pinned dataset_id")
    if dataset.get("status") != "evidence_and_method_map_not_engine_solver_inputs":
        problems.append("assignment map must not be engine solver inputs")
    try:
        baselines = {r["id"]: r for r in load(root / "data/parameters/baseline.json")["records"]}
        assumptions = {r["id"]: r for r in load(root / "data/parameters/assumptions.json")["records"]}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return [f"cannot resolve assignment parameter references: {exc}"]

    def string_array(value, prefix, nonempty=True):
        valid = (isinstance(value, list) and (bool(value) or not nonempty)
                 and all(isinstance(x, str) and x.strip() for x in value))
        if not valid:
            problems.append(f"{prefix}: requires a string array")
            return []
        if len(value) != len(set(value)):
            problems.append(f"{prefix}: duplicate references or fields")
        return value

    cases = dataset.get("research_cases")
    if not isinstance(cases, list):
        problems.append("research_cases must be an array")
        cases = []
    case_ids = []
    for index, case in enumerate(cases):
        prefix = f"research_cases[{index}]"
        if not isinstance(case, dict):
            problems.append(f"{prefix}: must be an object")
            continue
        cid = case.get("id")
        if not isinstance(cid, str) or cid not in models:
            problems.append(f"{prefix}: unknown method case")
        else:
            case_ids.append(cid)
            if case.get("model_id") != models[cid]:
                problems.append(f"{prefix}: model_id differs from pinned method")
        if case.get("use_scope") != "method_not_vehicle_prediction":
            problems.append(f"{prefix}: cannot claim vehicle prediction")
        expected_role = "synthetic_benchmark" if cid == "ideal_formula" else "research_assumption"
        if case.get("input_role") != expected_role:
            problems.append(f"{prefix}: invalid method input_role")
        if not isinstance(case.get("limitations"), str) or not case["limitations"].strip():
            problems.append(f"{prefix}: missing limitations")
        reqs = string_array(case.get("requirements"), prefix + ".requirements")
        if any(x not in {f"REQ-{i:02}" for i in range(1, 12)} for x in reqs):
            problems.append(f"{prefix}: unknown requirement")
        artifacts = string_array(case.get("artifact_refs"), prefix + ".artifact_refs")
        for ref in artifacts:
            try:
                if not local_path(root, ref).is_file():
                    problems.append(f"{prefix}: missing artifact {ref}")
            except ValueError as exc:
                problems.append(f"{prefix}: {exc}")
        if isinstance(cid, str) and cid in {"continuous_liquid_hp", "synthetic_cycle_trade"}:
            sample = case.get("sample_report_ref")
            if not isinstance(sample, str) or sample not in artifacts:
                problems.append(f"{prefix}: sample_report_ref must be a declared artifact")
            else:
                try:
                    report = load(local_path(root, sample))
                    if not isinstance(report, dict) or report.get("model") != case.get("model_id"):
                        problems.append(f"{prefix}: sample model does not match")
                except (OSError, ValueError) as exc:
                    problems.append(f"{prefix}: cannot read sample report: {exc}")
    if len(case_ids) != len(models) or set(case_ids) != set(models):
        problems.append("assignment map requires exactly three unique method cases")
    record_ids = []
    for index, record in enumerate(dataset.get("records", [])):
        if not isinstance(record, dict):
            continue
        prefix = f"records[{index}]"
        rid = record.get("id")
        if not isinstance(rid, str) or rid not in objects:
            problems.append(f"{prefix}: unknown assignment object")
        else:
            record_ids.append(rid)
            if tuple(record.get(k) for k in ("object", "variant", "stage")) != objects[rid]:
                problems.append(f"{prefix}: object/variant/stage mismatch")
        if record.get("data_role") != "fact":
            problems.append(f"{prefix}: configuration must retain fact role; assumptions are separate")
        for key in ("unknown_fields", "can_calculate", "cannot_calculate", "case_refs"):
            values = string_array(record.get(key), f"{prefix}.{key}")
            if key == "case_refs" and any(x not in case_ids for x in values):
                problems.append(f"{prefix}: unknown method case reference")
        for ref in string_array(record.get("source_refs"), prefix + ".source_refs"):
            if ref not in known_sources:
                problems.append(f"{prefix}: assignment sources require full available source IDs")
        for ref in string_array(record.get("excluded_version_refs"), prefix + ".excluded_version_refs", False):
            if ref not in known_sources:
                problems.append(f"{prefix}: unknown excluded source")
        for key, table, role in (("baseline_record_refs", baselines, "fact"),
                                 ("derived_record_refs", baselines, "derived"),
                                 ("assumption_record_refs", assumptions, "assumption")):
            for ref in string_array(record.get(key), prefix + "." + key, key == "baseline_record_refs"):
                parameter = table.get(ref)
                if parameter is None or parameter.get("data_role") != role:
                    problems.append(f"{prefix}: missing or wrong-role {key} {ref}")
                    continue
                # A product-scale conversion is context for the first-stage
                # TQ-12A only. It must never become a flight-batch input.
                product_context = (
                    rid == "zq3_y1_stage1" and key == "derived_record_refs"
                    and ref == "zq3_tq12a_sea_level_thrust"
                    and (parameter.get("object"), parameter.get("variant"), parameter.get("stage"))
                    == ("TQ-12A", "product_description", "发动机")
                    and parameter.get("model_use") == "reference_scale_only"
                )
                if product_context:
                    continue
                if parameter.get("object") != record.get("object"):
                    problems.append(f"{prefix}: cross-vehicle parameter {ref}")
                if key == "assumption_record_refs":
                    expected_variant = f"{record.get('variant')}-compatible research scenario"
                    if parameter.get("variant") != expected_variant:
                        problems.append(f"{prefix}: cross-version assumption {ref}")
                elif parameter.get("variant") != record.get("variant"):
                    problems.append(f"{prefix}: cross-version parameter {ref}")
                # Whole-vehicle values are context only, never per-engine data.
                if parameter.get("stage") != record.get("stage"):
                    whole_vehicle_context = (
                        key == "baseline_record_refs" and parameter.get("stage") == "整箭"
                        and parameter.get("model_use") == "system_context_only"
                    )
                    if not whole_vehicle_context:
                        problems.append(f"{prefix}: cross-stage parameter {ref}")
        if rid == "cz10b_first_stage1" and isinstance(record.get("case_refs"), list):
            if "continuous_liquid_hp" in record["case_refs"]:
                problems.append(f"{prefix}: methane HP cannot calculate kerosene")
    if len(record_ids) != len(objects) or set(record_ids) != set(objects):
        problems.append("assignment map requires exactly four unique stage objects")
    return problems


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
    if (path.name == "assignment_case_map.json"
            or dataset.get("dataset_id") == "assignment-case-map-v1"
            or "research_cases" in dataset):
        # Pass a normalized record shape so malformed input remains a diagnostic.
        candidate = dict(dataset, records=records)
        problems.extend(validate_assignment_map(candidate, known_sources, root))
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
