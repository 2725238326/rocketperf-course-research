"""Archived CEA evidence and raw-output defect guards, without external runtime."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import cea_reference


class CeaReferenceTests(unittest.TestCase):
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
