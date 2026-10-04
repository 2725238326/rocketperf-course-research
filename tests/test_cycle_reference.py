"""Immutable synthetic cycle archive integrity; no engine-validation claim."""
import json
import copy
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from cycle_validation import check_archive, validate_cycle
from gas_checks import database, mixture
from cycle_study import verify as verify_study
from projectlib import atomic_json, digest, read_json
from thermal_boundary import verify as verify_thermal


class CycleArchiveTests(unittest.TestCase):
    def thermal_copy(self, temporary):
        folder = Path(temporary) / "thermal"
        shutil.copytree(ROOT / "results/research/thermal_boundary_v1", folder)
        return folder

    def rehash_thermal(self, folder):
        """Simulate a changed archive whose file hashes were recomputed too."""
        manifest = read_json(folder / "manifest.json")
        for item in manifest["files"]:
            item["sha256"] = digest(folder / item["path"])
        atomic_json(folder / "manifest.json", manifest)

    def test_thermal_seven_c_experiments_and_analytical_response(self):
        self.assertEqual(verify_thermal(ROOT / "results/research/thermal_boundary_v1"), 7)

    def test_thermal_scope_types_and_inventory_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build/test-tmp") as temporary:
            folder = self.thermal_copy(temporary)
            original = read_json(folder / "manifest.json")
            for key, value in (("schema_version", True), ("source_dirty", 1),
                               ("scope", "Flight engine validation"), ("started_at", 1)):
                candidate = copy.deepcopy(original)
                candidate[key] = value
                atomic_json(folder / "manifest.json", candidate)
                with self.subTest(key=key), self.assertRaises(ValueError):
                    verify_thermal(folder)
            atomic_json(folder / "manifest.json", original)
            (folder / "undeclared").mkdir()
            with self.assertRaisesRegex(ValueError, "inventory"):
                verify_thermal(folder)

    def test_thermal_rehashed_bad_protocol_and_timestamp_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build/test-tmp") as temporary:
            folder = self.thermal_copy(temporary)
            path = folder / "fuel_h_plus/run-manifest.json"
            original = read_json(path)
            for key, value in (
                ("exit_code", False), ("accounting_checks", True),
                ("command", ["rocketperf.exe", "run", "input.ini"]),
                ("finished_at", "2020-01-01T00:00:00+00:00"),
                ("extra", "undeclared"),
            ):
                candidate = copy.deepcopy(original)
                candidate[key] = value
                atomic_json(path, candidate)
                self.rehash_thermal(folder)
                with self.subTest(key=key), self.assertRaises(ValueError):
                    verify_thermal(folder)

    def test_thermal_wrong_result_rehashed_and_matching_stdout_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build/test-tmp") as temporary:
            folder = self.thermal_copy(temporary)
            result = folder / "fuel_h_plus/result.json"
            candidate = read_json(result)
            candidate["energy"]["chamber_required_heat_w"] += 100000
            atomic_json(result, candidate)
            shutil.copy2(result, folder / "fuel_h_plus/stdout.txt")
            run = read_json(folder / "fuel_h_plus/run-manifest.json")
            run["output_sha256"] = digest(result)
            atomic_json(folder / "fuel_h_plus/run-manifest.json", run)
            self.rehash_thermal(folder)
            with self.assertRaises(ValueError):
                verify_thermal(folder)

    def test_thermal_rehashed_changed_recipe_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build/test-tmp") as temporary:
            folder = self.thermal_copy(temporary)
            input_path = folder / "fuel_h_plus/input.ini"
            input_path.write_text(
                input_path.read_text(encoding="utf-8").replace("-4550000", "-4500000"),
                encoding="utf-8",
            )
            run = read_json(folder / "fuel_h_plus/run-manifest.json")
            run["input_sha256"] = digest(input_path)
            atomic_json(folder / "fuel_h_plus/run-manifest.json", run)
            self.rehash_thermal(folder)
            with self.assertRaisesRegex(ValueError, "input changed"):
                verify_thermal(folder)

    def test_research_grid_states_comparisons_and_provenance(self):
        self.assertEqual(verify_study(ROOT/'results/research/prescribed_cycle_scan_v1_20261004'),10)

    def test_research_mutation_and_duplicate_inventory_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as temporary:
            folder=Path(temporary)/'research'
            shutil.copytree(ROOT/'results/research/prescribed_cycle_scan_v1_20261004',folder)
            manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            manifest['files'].append(manifest['files'][0])
            (folder/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaises(ValueError): verify_study(folder)
    def setUp(self):
        self.archive=ROOT/'results/validation/prescribed_cycle_v1_20261004'
        self.report=json.loads((self.archive/'result.json').read_text(encoding='utf-8'))
        self.input=(self.archive/'input.ini').read_text(encoding='utf-8-sig')

    def test_fixed_archive_and_equations(self):
        self.assertEqual(len(check_archive(ROOT/'results/validation/prescribed_cycle_v1_20261004')),86)

    def test_modified_result_and_missing_file_rejected(self):
        (ROOT/'build/test-tmp').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cycle-archive-',dir=ROOT/'build/test-tmp') as temporary:
            folder=Path(temporary)/'archive'
            shutil.copytree(ROOT/'results/validation/prescribed_cycle_v1_20261004',folder)
            result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
            result['energy']['pump_power_w']*=2
            (folder/'result.json').write_text(json.dumps(result),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'hash mismatch'): check_archive(folder)
            (folder/'result.json').unlink()
            with self.assertRaises(OSError): check_archive(folder)

    def test_public_state_mutations_rejected(self):
        for path,value in (
            (('main_nozzle','cstar_m_per_s'),-123), (('main_nozzle','cstar_m_per_s'),'bad'),
            (('main_nozzle','exit','mach'),-100), (('main_nozzle','exit','mach'),1),
            (('main_nozzle','chamber','cp_frozen_j_per_kg_k'),1),
            (('main_nozzle','exit','mass_flux_kg_per_m2_s'),0),
            (('main_nozzle','throat','velocity_m_per_s'),True),
            (('turbine','inlet','h_j_per_kg'),'bad'),
        ):
            candidate=copy.deepcopy(self.report); cursor=candidate
            for key in path[:-1]: cursor=cursor[key]
            cursor[path[-1]]=value
            with self.subTest(path=path,value=value),self.assertRaises(ValueError): validate_cycle(candidate,self.input)

    def test_frozen_but_wrong_element_inventory_rejected(self):
        candidate=copy.deepcopy(self.report)
        for state in (candidate['main_nozzle']['chamber'],candidate['main_nozzle']['throat']['gas'],candidate['main_nozzle']['exit']['gas']):
            state['mole_fractions']={s:float(s=='H') for s in state['mole_fractions']}
        with self.assertRaises(ValueError): validate_cycle(candidate,self.input)

    def test_recomputed_states_preserve_historical_archive(self):
        self.assertEqual(len(validate_cycle(self.report,self.input)),132)
        self.assertEqual(len(check_archive(self.archive)),86)

    def test_report_checker_matches_pinned_scalar_reference(self):
        fits=database()
        reference=json.loads((ROOT/'tests/reference/nasa9_cantera.json').read_text(encoding='utf-8'))
        for state in reference['states']:
            result=mixture({state['id']:1.0},state['temperature_k'],fits['reference_pressure_pa'],fits)
            for source,target in (('cp_j_per_kg_k','cp_frozen_j_per_kg_k'),('h_j_per_kg','h_j_per_kg'),('s_j_per_kg_k','s_j_per_kg_k')):
                with self.subTest(species=state['id'],temperature=state['temperature_k'],field=target):
                    self.assertTrue(math.isclose(result[target],state[source],rel_tol=2e-11,abs_tol=1e-6))


if __name__=='__main__': unittest.main(verbosity=2)
