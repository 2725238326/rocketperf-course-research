"""Archive source identities and reproduce feed-property candidates, not a fluid solver."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from projectlib import ROOT, atomic_json, digest, local_path, read_json
from thermo_data import COMMIT, RAW, SOURCE_HASHES, number


OUTPUT = "data/parameters/feed_property_candidates.json"
SOURCE_MANIFEST = "调研/feed_sources.json"
SOURCE_INDEX = "调研/原始来源/来源文件索引.json"
ANCHORS = ("CH4(L)", "O2(L)", "RP-1")
EOS_SOURCES = {
    "Methane": "F02_coolprop_methane_7_1_0",
    "Oxygen": "F03_coolprop_oxygen_7_1_0",
}
PAPER_HASHES = {
    "20261005_feed/nist_surrogate_900238.pdf": "a986704a9184ce32c4499c94f818a520dff859da19554318c3cfa06469eeef4e",
    "20261005_feed/nist_ir6646.pdf": "9475a1e69c8e0703ab6dab640eff32ce3cbc276331b19b3133e7d96e64b2ba5f",
}
# Transcribed from Huber et al. 2009, Table 2, printed p.3086 / PDF p.4.
# These are mole fractions of fitted surrogates, not measured fuel composition.
SURROGATES = {
    "RP-1": {"alpha-methyldecalin": 0.354, "5-methylnonane": 0.150,
             "n-dodecane": 0.183, "heptylcyclohexane": 0.313},
    "RP-2": {"alpha-methyldecalin": 0.354, "5-methylnonane": 0.084,
             "2,4-dimethylnonane": 0.071, "n-dodecane": 0.158, "heptylcyclohexane": 0.333},
}


def register_sources(root=ROOT, manifest=SOURCE_MANIFEST):
    """Append downloaded source metadata without dropping older, nested archives."""
    index = read_json(root / SOURCE_INDEX)
    sources = read_json(local_path(root, manifest))
    if not isinstance(index, list) or not isinstance(sources, list) or not sources:
        raise ValueError("Source index and manifest must be nonempty arrays")
    ids = [entry["id"] for entry in index]
    new_ids = [entry["id"] for entry in sources]
    if len(set(ids)) != len(ids) or len(set(new_ids)) != len(new_ids):
        raise ValueError("Duplicate source identity")
    by_id = {entry["id"]: entry for entry in index}
    for source in sources:
        name = source["id"]
        if not isinstance(name, str) or not name or any(c not in
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in name):
            raise ValueError("Unsafe source identity")
        if not isinstance(source["url"], str) or not source["url"].startswith("https://"):
            raise ValueError("Expected HTTPS source URL")
        relative = source.get("file", f"{name}.txt")
        path = local_path(root, "调研/原始来源/" + relative)
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Source has not been downloaded: {name}")
        record = {
            "id": name, "url": source["url"], "available": True,
            "file": path.relative_to(root / "调研/原始来源").as_posix(), "bytes": path.stat().st_size,
            "saved_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            "sha256": digest(path),
        }
        if name in by_id:
            old = by_id[name]
            if any(old.get(key) != record[key] for key in ("url", "file", "bytes")) or \
                    old.get("sha256", "").lower() != record["sha256"]:
                raise ValueError(f"Existing source differs; archive a new ID: {name}")
        else:
            index.append(record)
    atomic_json(root / SOURCE_INDEX, index)
    return len(sources)


def parse_anchors(text):
    """CEA Appendix A: count=0 means one assigned enthalpy, not NASA9 fits."""
    lines = text.splitlines()
    records = []
    for name in ANCHORS:
        matches = [i for i, line in enumerate(lines) if line[:18].strip() == name]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one anchor: {name}")
        cursor = matches[0]
        meta, temperature = lines[cursor + 1:cursor + 3]
        if int(meta[:2]) != 0 or meta[50:52].strip() != "1":
            raise ValueError(f"{name}: expected condensed, reactant-only record")
        mass, enthalpy, t_ref = number(meta[52:65]), number(meta[65:80]), number(temperature[:11])
        if mass <= 0 or t_ref <= 0:
            raise ValueError(f"{name}: nonpositive mass or temperature")
        elements = {}
        for start in range(10, 50, 8):
            symbol, amount = meta[start:start + 2].strip(), number(meta[start + 2:start + 8])
            if symbol:
                if symbol not in {"C", "H", "O"} or symbol in elements or amount <= 0:
                    raise ValueError(f"{name}: unsupported elemental inventory")
                elements[symbol] = amount
            elif amount:
                raise ValueError(f"{name}: element amount without symbol")
        if not elements:
            raise ValueError(f"{name}: empty inventory")
        records.append({
            "name": name, "elements": elements, "molar_mass_kg_per_kmol": mass,
            "assigned_temperature_k": t_ref, "assigned_enthalpy_j_per_mol": enthalpy,
            "source_line": cursor + 1, "source_note": lines[cursor][18:].strip(),
        })
    return records


def base_record(identity, object_name, variant, parameter, value, unit, role, refs, notes):
    return {
        "id": identity, "object": object_name, "variant": variant, "stage": "not_applicable",
        "parameter": parameter, "value": value, "unit": unit, "data_role": role,
        "operating_boundary": "Property-method candidate only; not a flight-engine input",
        "source_refs": refs, "model_use": "Research and future C17 contract; not enabled in production",
        "notes": notes,
    }


def generate(root=ROOT):
    for name, expected in SOURCE_HASHES.items():
        if digest(root / RAW / name) != expected:
            raise ValueError(f"Immutable CEA source differs: {name}")
    for name, expected in PAPER_HASHES.items():
        if digest(root / "调研/原始来源" / name) != expected:
            raise ValueError(f"Fixed property paper differs: {name}")
    source_index = read_json(root / SOURCE_INDEX)
    indexed = {entry["id"]: entry for entry in source_index if entry.get("available") is True}
    sources = read_json(root / SOURCE_MANIFEST)
    identities = []
    for source in sources:
        entry = indexed.get(source["id"])
        if not entry or entry.get("url") != source["url"]:
            raise ValueError(f"Source not registered: {source['id']}")
        path = local_path(root, "调研/原始来源/" + entry["file"])
        if digest(path) != entry["sha256"].lower():
            raise ValueError(f"Source hash differs: {source['id']}")
        identities.append({"id": entry["id"], "url": entry["url"],
                           "path": path.relative_to(root).as_posix(),
                           "sha256": entry["sha256"].lower()})
    records = []
    for anchor in parse_anchors((root / RAW / "thermo.inp").read_text(encoding="ascii")):
        label = anchor["name"]
        identity = {"CH4(L)": "FP-CH4-L-ANCHOR", "O2(L)": "FP-O2-L-ANCHOR", "RP-1": "FP-RP1-ANCHOR"}[label]
        record = base_record(
            identity, label, "CEA v3.3.4 fixed reactant record", "assigned_enthalpy",
            anchor["assigned_enthalpy_j_per_mol"], "J/mol", "fact",
            [f"{RAW}/thermo.inp", "调研/文献/L02_CEA_Manual_1996.txt"],
            "Single-temperature assigned enthalpy. Not a temperature interval, EOS, density, "
            "pressure correction or experimental identification of Chinese kerosene.",
        )
        record.update({
            "phase": "condensed", "source_phase_code": 1, "temperature_interval_count": 0,
            "anchor": anchor,
            "enthalpy_basis": "CEA assigned chemical enthalpy; includes formation contribution",
            "pressure_pa": None, "density_kg_per_m3": None,
            "derived": {"data_role": "derived", "enthalpy_j_per_kg":
                        anchor["assigned_enthalpy_j_per_mol"] * 1000.0 / anchor["molar_mass_kg_per_kmol"],
                        "equation": "h_mass = 1000 * h_molar / M_kg_per_kmol"},
            "supported_state": "Exact assigned temperature only; pressure dependence not supplied",
        })
        records.append(record)
    for name, composition in SURROGATES.items():
        record = base_record(
            "FP-" + name.replace("-", "") + "-SURROGATE-2009", name,
            "Huber et al. 2009 fitted sample surrogate", "surrogate_mole_fractions",
            dict(composition), "mol/mol", "fact",
            ["F11_nist_surrogate_pdf_20261005", "F08_nist_rp_surrogate_20261005"],
            "Published model composition, not measured batch composition. Table 2/abstract "
            "and following paragraph agree; one preceding sentence reverses the component counts.",
        )
        record.update({
            "locator": "Printed p.3086, Table 2; PDF p.4, visually verified",
            "property_scope": "Sample-specific fitted thermophysical properties; no imported formation enthalpies",
            "component_count": len(composition),
            "production_dependency": False,
            "chemical_enthalpy_basis": None,
            "density_table": None,
            "license_scope": "NIST-hosted author paper retained as evidence; MIT license applies only to CoolProp",
        })
        records.append(record)
    for name, source_id in EOS_SOURCES.items():
        fluid = read_json(root / "调研/原始来源" / f"{source_id}.txt")
        eos = fluid["EOS"][0]
        state = eos["STATES"]["sat_min_liquid"]
        record = base_record(
            f"FP-{name.upper()}-EOS", name, "CoolProp v7.1.0 HEOS", "reference_software_metadata",
            {"eos_citation": eos["BibTeX_EOS"], "t_max_k": eos["T_max"], "p_max_pa": eos["p_max"],
             "molar_mass_kg_per_mol": eos["molar_mass"], "gas_constant_j_per_mol_k": eos["gas_constant"],
             "minimum_saturation_temperature_k": state["T"]},
            "mixed; individual field suffixes define SI units", "fact",
            [source_id, "F04_coolprop_license_7_1_0", "F07_coolprop_bibliography_7_1_0"],
            "Software metadata, not a validated liquid-state table. Global EOS bounds do not "
            "prove single-phase validity. Default reference enthalpy is not the NASA formation basis.",
        )
        record.update({
            "license": "MIT", "production_dependency": False,
            "ideal_helmholtz_terms": [term["type"] for term in eos["alpha0"]],
            "residual_helmholtz_terms": [term["type"] for term in eos["alphar"]],
            "reference_state_policy": "Record offsets; align chemical enthalpy before use",
        })
        records.append(record)
    for identity, object_name, parameter, unit, note in (
        ("FP-CH4-L-DENSITY", "CH4(L)", "engine_inlet_density", "kg/m^3",
         "Engine inlet T/P and verified single-phase table have not been established."),
        ("FP-O2-L-DENSITY", "O2(L)", "engine_inlet_density", "kg/m^3",
         "Engine inlet T/P and verified single-phase table have not been established."),
        ("FP-CN-KEROSENE-COMPOSITION", "Chinese engine kerosene", "batch_composition", "mass fraction",
         "CEA RP-1 and n-dodecane are not evidence of the flown fuel composition."),
        ("FP-CN-KEROSENE-ENTHALPY", "Chinese engine kerosene", "inlet_chemical_enthalpy", "J/kg",
         "Fuel identity, batch, T/P, phase and chemical enthalpy reference are not established."),
    ):
        records.append(base_record(
            identity, object_name, "unidentified engine inlet", parameter, None, unit, "unknown",
            ["调研/专题/RES-006_液态与煤油入口.md"], note,
        ))
    return {
        "schema_version": 1, "dataset_id": "feed-property-candidates-v1",
        "evidence_cutoff": "2026-10-05", "status": "research_candidates_not_production",
        "cea_commit": COMMIT,
        "cea_source_files": [{"path": f"{RAW}/{name}", "sha256": sha}
                             for name, sha in SOURCE_HASHES.items()],
        "source_files": identities,
        "records": records,
        "missing_real_engine_fields": [
            "Propellant batch and purity", "Inlet temperature, pressure and phase",
            "State-dependent liquid density and chemically aligned enthalpy",
            "Pump outlet thermal state and physical phase envelope",
        ],
        "missing_value_policy": "Unknowns remain null; no synthetic or analogous value is promoted to engine fact.",
    }


def check(root=ROOT):
    actual = read_json(root / OUTPUT)
    expected = generate(root)
    # Canonical JSON preserves boolean-vs-number identity, unlike Python dict equality.
    if json.dumps(actual, sort_keys=True, ensure_ascii=False, allow_nan=False) != \
            json.dumps(expected, sort_keys=True, ensure_ascii=False, allow_nan=False):
        raise ValueError("Feed candidates differ from fixed sources or declared research scope")
    return len(expected["records"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("register-sources", "generate", "check"))
    parser.add_argument("--source-manifest", default=SOURCE_MANIFEST,
                        help="Manifest for append-only source registration")
    args = parser.parse_args()
    if args.command == "register-sources":
        print(f"Registered {register_sources(manifest=args.source_manifest)} sources; previous archives preserved")
    elif args.command == "generate":
        atomic_json(ROOT / OUTPUT, generate())
        print(f"Generated {OUTPUT}; no production physics computed")
    else:
        print(f"Feed candidates: {check()} records checked against source identities")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"feed-candidates: {error}", file=sys.stderr)
        sys.exit(1)
