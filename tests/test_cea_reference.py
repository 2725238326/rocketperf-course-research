"""Archived CEA evidence and raw-output defect guards, without external runtime."""
from pathlib import Path
import copy
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import cea_reference
from combustion_reference import check_archive, compare_report


class CeaReferenceTests(unittest.TestCase):
    def test_current_method_archive_under_extended_checks(self):
        check_archive(ROOT/'results/validation/ana002_method_reference_20261004')

    def test_negative_properties_bool_schema_and_fake_station_rejected(self):
        reference=next(r for r in cea_reference.check_reference()['cases'] if r['id']=='ch4_o2_rocket_frozen_chamber')
        report=json.loads((ROOT/'results/validation/ana002_method_reference_20261004/frozen10-stdout.json').read_text(encoding='utf-8'))
        for defect in ('cp','R','schema','flux','mach','residual','limits','booliteration'):
            candidate=copy.deepcopy(report)
            if defect=='cp': candidate['chamber']['cp_frozen_j_per_kg_k']=-1
            if defect=='R': candidate['chamber']['gas_constant_j_per_kg_k']=-1
            if defect=='schema': candidate['schema_version']=True
            if defect=='flux': candidate['nozzle']['exit']['mass_flux_kg_per_m2_s']*=2
            if defect=='mach': candidate['nozzle']['exit']['mach']=-1
            if defect=='residual': candidate['diagnostics']['enthalpy_residual_j_per_kg']=0.009
            if defect=='limits': candidate['limitations']='claimed'
            if defect=='booliteration': candidate['diagnostics']['hp_iterations']=True
            with self.subTest(defect=defect),self.assertRaises(ValueError): compare_report(candidate,reference,'frozen',10)
    def test_fixed_archive(self):
        manifest = cea_reference.check_reference()
        self.assertEqual(len(manifest['cases']), 4)
        cases = {case['id']: case['summary'] for case in manifest['cases']}
        self.assertEqual(cases['ch4_o2_hp']['rows']['temperature_k'], [3673.61])
        self.assertEqual(cases['ch4_o2_rocket_equilibrium']['rows']['temperature_k'][0], 3673.61)
        self.assertEqual(cases['ch4_o2_rocket_frozen_chamber']['rows']['temperature_k'][0], 3673.61)

    def test_initial_invalid_bytes_not_silently_cleaned(self):
        raw = ROOT / 'tests/reference/cea/raw/ch4_o2_hp.out'
        with self.assertRaises((UnicodeDecodeError, ValueError)):
            cea_reference.parse_output(raw.read_bytes())

    def test_bad_output_and_wrong_chemistry_fail(self):
        with self.assertRaises(ValueError):
            cea_reference.parse_output(b'T, K 3000\n')
        path = ROOT / 'tests/reference/cea/raw/trace1e8/ch4_o2_rocket_equilibrium.out'
        with self.assertRaises(ValueError):
            cea_reference.parse_output(path.read_bytes(), rocket=True, frozen=True)
        with self.assertRaises(ValueError):
            cea_reference.parse_output(path.read_bytes().replace(b'1.5294', b'NaN'), rocket=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
