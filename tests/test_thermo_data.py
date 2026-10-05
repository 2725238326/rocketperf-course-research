"""Data conversion and evidence guard tests; reference runtime is not required."""
from pathlib import Path
import shutil
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import thermo_data
import pipeline
import cea_reference
import combustion_reference
import cycle_validation
import adiabatic_inlet
from projectlib import read_json, atomic_json, digest


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

    def test_archived_validation_results_are_consistent(self):
        archives = sorted((ROOT / 'results/validation').glob('*/manifest.json'))
        self.assertTrue(archives, 'Expected actual C/CEA result archive')
        combustion_count = 0
        for manifest in archives:
            with self.subTest(archive=manifest.parent.name):
                kind=read_json(manifest).get('kind')
                if kind=='combustion-reference':
                    self.assertEqual(combustion_reference.check_archive(manifest.parent)['status'], 'PASS')
                    combustion_count += 1
                elif kind=='cycle-accounting-validation':
                    self.assertGreater(len(cycle_validation.check_archive(manifest.parent)),0)
                elif kind=='adiabatic-inlet-validation':
                    self.assertEqual(adiabatic_inlet.verify(manifest.parent),15)
                else: self.fail(f'Unknown validation archive type: {kind}')
        self.assertGreater(combustion_count,0,'Expected actual C/CEA result archive')

    def test_adiabatic_archive_rejects_tampering(self):
        self.assertEqual(len(adiabatic_inlet.recipes(0,0)),15)
        for manifest in (ROOT/'results/validation').glob('*/manifest.json'):
            if read_json(manifest).get('kind')!='adiabatic-inlet-validation':
                continue
            for defect in ('scope','exit-type','command','heat','thrust','reference','build','inventory','comparison-type'):
                with self.subTest(defect=defect),tempfile.TemporaryDirectory(prefix='adiabatic-',dir=ROOT/'build') as temp:
                    folder=Path(temp)/'archive'
                    shutil.copytree(manifest.parent,folder)
                    record=read_json(folder/'manifest.json')
                    if defect=='scope': record['scope']='Real liquid engine validation'
                    if defect=='exit-type': record['runs'][0]['exit_code']=False
                    if defect=='command': record['runs'][5]['arguments'][2]='arbitrary'
                    if defect in {'heat','thrust'}:
                        filename='enthalpy_A10-stdout.txt';report=read_json(folder/filename)
                        if defect=='heat': report['boundary']['heat_transfer_j_per_kg']=1
                        else: report['geometry']['thrust_n']+=10
                        atomic_json(folder/filename,report)
                        next(f for f in record['files'] if f['path']==filename)['sha256']=digest(folder/filename)
                    if defect=='reference':
                        filename='ch4_o2_hp.out'
                        (folder/filename).write_bytes((folder/filename).read_bytes()+b'\n')
                        next(f for f in record['files'] if f['path']==filename)['sha256']=digest(folder/filename)
                    if defect=='build': record['binary_sha256']='0'*64
                    if defect=='inventory': (folder/'extra.txt').write_text('extra',encoding='utf-8')
                    if defect=='comparison-type':
                        row=next(c for c in record['comparisons']['enthalpy_hp'] if c['reference']==0)
                        row['reference']=False
                    atomic_json(folder/'manifest.json',record)
                    with self.assertRaises(ValueError): adiabatic_inlet.verify(folder)


if __name__ == '__main__':
    unittest.main(verbosity=2)
