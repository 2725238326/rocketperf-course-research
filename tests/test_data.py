import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_data


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
        for name in ("baseline.json", "assumptions.json"):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
