"""Data conversion and evidence guard tests; reference runtime is not required."""
from pathlib import Path
import shutil
import tempfile
import sys
import unittest
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import thermo_data
import pipeline
import cea_reference
import combustion_reference
import cycle_validation
import adiabatic_inlet
import adiabatic_study
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

    def test_adiabatic_study_design_and_type_guards(self):
        placeholder={(s,t):0 for s in ('CH4','O2') for t in adiabatic_study.TEMPERATURES}
        runs=adiabatic_study.recipes(placeholder)
        self.assertEqual(len(runs),51)
        self.assertEqual(sum(code!=0 for _,_,code in runs),5)
        self.assertEqual(len({name for name,_,_ in runs}),51)
        for actual,expected in [(False,0),({'x':True},{'x':1}),([True],[1]),(float('nan'),0)]:
            with self.assertRaises(ValueError):
                adiabatic_study.typed_equal(actual,expected,'fixture')
        self.assertIn('rocket frozen nfz=1',adiabatic_study.case_card('base',298.15,298.15,3.4))
        with self.assertRaises(FileExistsError):
            adiabatic_study.archive('results/research')

    def test_adiabatic_study_archives(self):
        manifests=list((ROOT/'results/research').glob('adiabatic_inlet_response_*/manifest.json'))
        self.assertTrue(manifests,'Expected actual fixed-geometry inlet response archive')
        for manifest in manifests:
            with self.subTest(archive=manifest.parent.name):
                self.assertEqual(adiabatic_study.verify(manifest.parent),(51,12,24))

    def test_adiabatic_response_svg_matches_saved_c_results(self):
        folder=ROOT/'results/research/adiabatic_inlet_response_v1'
        generated=adiabatic_study.response_svg(folder)
        self.assertEqual((ROOT/'docs/adiabatic-inlet-response.svg').read_text(encoding='utf-8'),generated)
        tree=ElementTree.fromstring(generated)
        self.assertEqual(tree.tag,'{http://www.w3.org/2000/svg}svg')
        self.assertEqual(len(tree.findall('{http://www.w3.org/2000/svg}path')),12)
        self.assertIn(digest(folder/'manifest.json')[:16],generated)

    def test_adiabatic_study_rejects_semantic_tampering(self):
        for manifest in (ROOT/'results/research').glob('adiabatic_inlet_response_*/manifest.json'):
            for defect in ('heat','flow','mach','species','condition','card','reference',
                           'failure','command','exit-type','comparison-type','response',
                           'geometry','build','source','timestamp','inventory','hash'):
                with self.subTest(defect=defect),tempfile.TemporaryDirectory(prefix='hp-study-',dir=ROOT/'build') as temp:
                    folder=Path(temp)/'archive'
                    shutil.copytree(manifest.parent,folder)
                    record=read_json(folder/'manifest.json')
                    filename=None
                    if defect in {'heat','flow','mach','species'}:
                        filename='base_A10-stdout.txt';report=read_json(folder/filename)
                        if defect=='heat': report['boundary']['heat_transfer_j_per_kg']=1
                        if defect=='flow': report['geometry']['mass_flow_kg_per_s']*=1.01
                        if defect=='mach': report['nozzle']['exit']['mach']+=0.01
                        if defect=='species': report['chamber']['mole_fractions']['O2']*=1.1
                        atomic_json(folder/filename,report)
                    if defect=='condition': record['conditions'][0]['oxidizer_fuel_mass_ratio']=3.5
                    if defect=='card':
                        filename='base.inp'
                        (folder/filename).write_text(adiabatic_study.case_card('base',298.15,298.15,3.5),encoding='utf-8')
                    if defect=='reference':
                        filename='base.out'
                        (folder/filename).write_text((folder/filename).read_text(encoding='ascii').replace('FROZEN','EQUILIBRIUM'),encoding='ascii')
                    if defect=='failure':
                        filename='reject_h-stdout.txt';(folder/filename).write_text('{}',encoding='utf-8')
                    if defect=='command': record['runs'][10]['arguments'][0]='thermo'
                    if defect=='exit-type': record['runs'][0]['exit_code']=False
                    if defect=='comparison-type':
                        next(c for c in record['comparisons']['base_hp'] if c['reference']==0)['reference']=False
                    if defect=='response': record['responses'][0]['thrust_n']+=100
                    if defect=='geometry': record['design']['throat_area_m2']=0.02
                    if defect=='build': record['c_binary_sha256']='0'*64
                    if defect=='source': record['rocket_source_hashes']['rocket.f90']='0'*64
                    if defect=='timestamp': record['finished_at']=True
                    if defect=='inventory': (folder/'extra').mkdir()
                    if defect=='hash': (folder/'base.inp').write_bytes(b'bad')
                    if filename is not None:
                        next(f for f in record['files'] if f['path']==filename)['sha256']=digest(folder/filename)
                    atomic_json(folder/'manifest.json',record)
                    with self.assertRaises(ValueError): adiabatic_study.verify(folder)


if __name__ == '__main__':
    unittest.main(verbosity=2)
