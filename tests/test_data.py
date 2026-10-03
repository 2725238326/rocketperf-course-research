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


if __name__ == "__main__":
    unittest.main(verbosity=2)
