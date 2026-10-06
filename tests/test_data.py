import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_data
import feed_candidates


class DataContractTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'build/test-tmp').mkdir(parents=True, exist_ok=True)

    def check_candidate(self, candidate):
        with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
            path=Path(folder)/'candidate.json'
            path.write_text(json.dumps(candidate,ensure_ascii=False),encoding='utf-8')
            return check_data.validate_dataset(path,ROOT/'调研/原始来源/来源文件索引.json')

    def test_project_datasets_pass(self):
        source_index = ROOT / "调研/原始来源/来源文件索引.json"
        for name in ("baseline.json", "assumptions.json", "feed_property_candidates.json", "assignment_case_map.json", "kerosene_method_contract.json", "classmate_product_evidence.json"):
            with self.subTest(name=name):
                self.assertEqual(check_data.validate_dataset(ROOT / "data/parameters" / name, source_index), [])

    def test_duplicate_id_and_unknown_source_fail(self):
        dataset = json.loads((ROOT / "data/parameters/assumptions.json").read_text(encoding="utf-8"))
        dataset["records"].append(copy.deepcopy(dataset["records"][0]))
        dataset["records"][-1]["source_refs"] = ["NOT-A-SOURCE"]
        with tempfile.TemporaryDirectory(dir=ROOT / "build/test-tmp") as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
            problems = check_data.validate_dataset(path, ROOT / "调研/原始来源/来源文件索引.json")
        self.assertTrue(any("duplicate id" in item for item in problems))
        self.assertTrue(any("unknown source_refs" in item for item in problems))

    def test_assumption_without_range_or_model_fails(self):
        dataset = json.loads((ROOT / "data/parameters/assumptions.json").read_text(encoding="utf-8"))
        del dataset["records"][0]["range"]
        del dataset["records"][0]["model_id"]
        with tempfile.TemporaryDirectory(dir=ROOT / "build/test-tmp") as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
            problems = check_data.validate_dataset(path, ROOT / "调研/原始来源/来源文件索引.json")
        self.assertTrue(any("requires model_id" in item for item in problems))
        self.assertTrue(any("requires finite range" in item for item in problems))

    def test_invalid_values_and_unbounded_assumptions_fail(self):
        for value in (float('nan'),float('inf'),True,None,1000.0,[],{'gamma':float('nan')}):
            dataset=json.loads((ROOT/'data/parameters/assumptions.json').read_text(encoding='utf-8'))
            dataset['records'][2]['value']=value
            with self.subTest(value=value): self.assertTrue(self.check_candidate(dataset))

    def test_nested_fields_require_matching_ranges(self):
        for changes in ({'area_ratio':19.0},{'stagnation_pressure_pa':-1.0}):
            dataset=json.loads((ROOT/'data/parameters/assumptions.json').read_text(encoding='utf-8'))
            dataset['records'][0]['value'].update(changes)
            self.assertTrue(self.check_candidate(dataset))

    def test_invented_or_escaping_local_reference_fails(self):
        for ref in ('docs/no-such-source.md','docs/../../outside.md','RES-999'):
            dataset=json.loads((ROOT/'data/parameters/assumptions.json').read_text(encoding='utf-8'))
            dataset['records'][2]['source_refs']=[ref]
            with self.subTest(ref=ref): self.assertTrue(self.check_candidate(dataset))

    def test_duplicate_json_and_overflow_are_not_valid_data(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
            path=Path(folder)/'candidate.json'
            for text in ('{"schema_version":1,"schema_version":2}', '{"value":1e999}'):
                path.write_text(text,encoding='utf-8')
                self.assertTrue(check_data.validate_dataset(path,ROOT/'调研/原始来源/来源文件索引.json'))

    def test_malformed_role_is_reported_without_type_error(self):
        dataset=json.loads((ROOT/'data/parameters/assumptions.json').read_text(encoding='utf-8'))
        dataset['records'][0]['data_role']=[]
        self.assertTrue(self.check_candidate(dataset))

    def test_duplicate_source_index_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
            index_path = Path(folder)/'index.json'
            entry = {"id": "repeated", "available": True}
            index_path.write_text(json.dumps([entry, entry]), encoding='utf-8')
            problems = check_data.validate_dataset(ROOT/'data/parameters/baseline.json', index_path)
            self.assertIn("source index contains duplicate ids", problems)

    def test_feed_candidates_match_fixed_sources(self):
        self.assertEqual(feed_candidates.check(), 11)
        self.assertEqual((ROOT / feed_candidates.HEADER).read_text(encoding="utf-8"),
                         feed_candidates.anchor_header())

    def test_feed_anchors_are_single_temperature_assigned_enthalpies(self):
        dataset = feed_candidates.generate()
        anchors = dataset["records"][:3]
        self.assertEqual([r["anchor"]["assigned_temperature_k"] for r in anchors], [111.643, 90.170, 298.15])
        self.assertEqual([r["value"] for r in anchors], [-89233.0, -12979.0, -24717.7])
        for record in anchors:
            self.assertEqual(record["temperature_interval_count"], 0)
            self.assertIsNone(record["pressure_pa"])
            self.assertIsNone(record["density_kg_per_m3"])
            self.assertAlmostEqual(record["derived"]["enthalpy_j_per_kg"],
                record["value"] * 1000.0 / record["anchor"]["molar_mass_kg_per_kmol"])

    def test_feed_numeric_and_scope_tampering_fail_even_if_json_is_valid(self):
        dataset = feed_candidates.generate()
        changes = (
            lambda d: d["records"][0].update(value=-89232),
            lambda d: d["records"][0]["anchor"].update(assigned_temperature_k=298.15),
            lambda d: d["records"][0].update(temperature_interval_count=False),
            lambda d: d["records"][1].update(density_kg_per_m3=1141),
            lambda d: d["records"][2]["anchor"].update(elements={"C": 1, "H": 26}),
            lambda d: d["records"][3].update(production_dependency=True),
            lambda d: d["records"][3]["value"].update({"n-dodecane": 0.184}),
            lambda d: d["records"][-1].update(value=0, data_role="fact"),
        )
        for mutate in changes:
            with self.subTest(mutation=mutate.__code__.co_firstlineno):
                candidate = copy.deepcopy(dataset)
                mutate(candidate)
                with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
                    root = Path(folder)
                    (root/'data/parameters').mkdir(parents=True)
                    (root/feed_candidates.OUTPUT).write_text(json.dumps(candidate), encoding='utf-8')
                    from unittest.mock import patch
                    with patch.object(feed_candidates, "generate", return_value=dataset):
                        with self.assertRaisesRegex(ValueError, "differ"):
                            feed_candidates.check(root)

    def test_feed_source_registration_preserves_nested_archives_and_is_idempotent(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
            root = Path(folder)
            (root/'调研/原始来源').mkdir(parents=True)
            old = {"id": "old_nested", "available": True, "file": "nested/archive.txt"}
            (root/feed_candidates.SOURCE_INDEX).write_text(json.dumps([old]), encoding='utf-8')
            source = {"id": "NEW_SOURCE", "url": "https://example.org/source.txt"}
            (root/feed_candidates.SOURCE_MANIFEST).write_text(json.dumps([source]), encoding='utf-8')
            (root/'调研/原始来源/NEW_SOURCE.txt').write_text("fixed raw source", encoding='utf-8')
            self.assertEqual(feed_candidates.register_sources(root), 1)
            first = (root/feed_candidates.SOURCE_INDEX).read_bytes()
            self.assertEqual(feed_candidates.register_sources(root), 1)
            self.assertEqual(first, (root/feed_candidates.SOURCE_INDEX).read_bytes())
            index = json.loads(first)
            self.assertEqual(index[0], old)
            self.assertEqual(index[1]["id"], "NEW_SOURCE")
            (root/'调研/原始来源/NEW_SOURCE.txt').write_text("changed", encoding='utf-8')
            with self.assertRaisesRegex(ValueError, "differs"):
                feed_candidates.register_sources(root)
            self.assertEqual(first, (root/feed_candidates.SOURCE_INDEX).read_bytes())

    def test_feed_surrogates_use_mole_fractions_not_actual_batch_claims(self):
        records = feed_candidates.generate()["records"]
        for name, count in (("RP-1", 4), ("RP-2", 5)):
            record = next(r for r in records if r["object"] == name and
                          r["parameter"] == "surrogate_mole_fractions")
            self.assertEqual(record["unit"], "mol/mol")
            self.assertEqual(record["component_count"], count)
            self.assertAlmostEqual(sum(record["value"].values()), 1.0)
            self.assertIsNone(record["chemical_enthalpy_basis"])
            self.assertFalse(record["production_dependency"])

    def test_assignment_associations_reject_missing_or_misleading_data(self):
        dataset = json.loads((ROOT / "data/parameters/assignment_case_map.json").read_text(encoding="utf-8"))
        mutations = (
            lambda d: d["records"].pop(),
            lambda d: d["records"].append(copy.deepcopy(d["records"][0])),
            lambda d: d["records"][0].update(variant="遥二"),
            lambda d: d["records"][0].update(source_refs=["V09"]),
            lambda d: d["records"][0].update(cannot_calculate=[]),
            lambda d: d["records"][0].update(unknown_fields=[None]),
            lambda d: d["records"][0].update(baseline_record_refs=["synthetic_mach2"]),
            lambda d: d["records"][0].update(baseline_record_refs=["zq3_y1_stage2_configuration"]),
            lambda d: d["records"][0].update(baseline_record_refs=["zq3_product_current_configuration"]),
            lambda d: d["records"][1].update(derived_record_refs=["zq3_tq12a_sea_level_thrust"]),
            lambda d: d["records"][1].update(assumption_record_refs=["zq3_stage1_pressure_area_scenario"]),
            lambda d: d["records"][0].update(assumption_record_refs=["cz10b_stage1_pressure_area_scenario"]),
            lambda d: d["records"][2]["case_refs"].append("continuous_liquid_hp"),
            lambda d: d["research_cases"][0].update(use_scope="vehicle_prediction"),
            lambda d: d["research_cases"][0].update(model_id="invented-model"),
            lambda d: d["research_cases"][0].update(id=[]),
            lambda d: d["research_cases"][0].update(id={}),
            lambda d: d["research_cases"][0].update(artifact_refs=["docs/no-such-artifact.md"]),
            lambda d: d["research_cases"][0].update(sample_report_ref="../../outside.json"),
            lambda d: d["research_cases"][0].update(requirements=["REQ-99"]),
            lambda d: d["research_cases"].append(copy.deepcopy(d["research_cases"][0])),
            lambda d: d.update(research_cases=[None]),
            lambda d: d.update(records=False),
            lambda d: d.update(status="real_engine_inputs"),
            lambda d: d.update(dataset_id="invented-map"),
            lambda d: d.pop("dataset_id"),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate.__code__.co_firstlineno):
                candidate = copy.deepcopy(dataset)
                mutate(candidate)
                self.assertTrue(self.check_candidate(candidate))

    def test_assignment_identity_cannot_disable_checks_at_canonical_filename(self):
        dataset = json.loads((ROOT / "data/parameters/assignment_case_map.json").read_text(encoding="utf-8"))
        dataset.pop("dataset_id")
        dataset.pop("research_cases")
        with tempfile.TemporaryDirectory(dir=ROOT / "build/test-tmp") as folder:
            candidate = Path(folder) / "assignment_case_map.json"
            candidate.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
            problems = check_data.validate_dataset(candidate, ROOT / "调研/原始来源/来源文件索引.json")
        self.assertTrue(any("pinned dataset_id" in item for item in problems))
        self.assertTrue(any("research_cases" in item for item in problems))

    def test_assignment_artifacts_are_part_of_test_identity(self):
        import pipeline
        tracked = {entry["path"] for entry in pipeline.test_records(ROOT)}
        dataset = json.loads((ROOT / "data/parameters/assignment_case_map.json").read_text(encoding="utf-8"))
        for case in dataset["research_cases"]:
            self.assertTrue(set(case["artifact_refs"]).issubset(tracked))


if __name__ == "__main__":
    unittest.main(verbosity=2)
