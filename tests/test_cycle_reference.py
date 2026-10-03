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


class CycleArchiveTests(unittest.TestCase):
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
