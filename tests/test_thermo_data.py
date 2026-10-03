"""Data conversion and evidence guard tests; reference runtime is not required."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import thermo_data
import pipeline
import cea_reference


class ThermoDataTests(unittest.TestCase):
    def test_generated_database_and_reference(self):
        self.assertEqual(thermo_data.check_generated(), 3)
        self.assertEqual(len(cea_reference.check_reference()['cases']), 4)

    def test_conversion_retains_true_temperature_limits(self):
        records = thermo_data.parse_selected((ROOT / thermo_data.RAW / 'thermo.inp').read_text(encoding='ascii'))
        mapping = {record['id']: record for record in records}
        self.assertEqual(len(mapping), 10)
        self.assertEqual(mapping['H2O']['ranges'][-1]['t_max_k'], 6000)
        self.assertEqual(mapping['O2']['ranges'][-1]['t_max_k'], 20000)
        self.assertEqual(mapping['CH4']['elements'], {'C': 1, 'H': 4})
        self.assertEqual(mapping['H2O']['formation_enthalpy_298_j_mol'], -241826)

    def test_duplicate_record_and_nonfinite_coefficients_fail(self):
        text = (ROOT / thermo_data.RAW / 'thermo.inp').read_text(encoding='ascii')
        with self.assertRaises(ValueError):
            thermo_data.parse_selected(text + '\nH2                duplicate\n')
        with self.assertRaises(ValueError):
            thermo_data.parse_selected(text.replace('4.078323210D+04', '           NaN', 1))
        with self.assertRaises(ValueError):
            thermo_data.number('Infinity')

    def test_cli_skip_and_empty_evidence_are_rejected(self):
        for log in ('Ran 13 tests\nOK (skipped=13)', 'Ran 0 tests\nOK', 'OK', 'Ran 3 tests\nFAILED', 'Ran 3 tests\nNOT OK'):
            with self.subTest(log=log), self.assertRaises(ValueError):
                pipeline.cli_test_count(log)
        self.assertEqual(pipeline.cli_test_count('Ran 13 tests in 0.1s\nOK'), 13)


if __name__ == '__main__':
    unittest.main(verbosity=2)
