"""Evidence rejection tests, executed by the existing parameter-data group."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import subprocess
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from projectlib import digest
from work2_baseline import verify as verify_base
from work2_baseline_layers import verify_bundle, verify_independent_record
from work2_frontier_data import OUTPUT, expected


class BaselineEvidenceTests(unittest.TestCase):
    def copy_archive(self):
        # Retained below build/work2 for inspection; no recursive cleanup action.
        target=ROOT/'build/work2/evidence-tests'/uuid.uuid4().hex
        shutil.copytree(ROOT/'Work2/results/baseline_v1',target)
        return target

    def test_selected_bundle_passes(self):
        self.assertEqual(verify_bundle(ROOT/'Work2/results/baseline_v1'),
            dict(cases=84,debug_processes=60,independent_references=54,cea_gas_cases=4,inlet_cases=9,cli_rejections=3))

    def test_raw_byte_change_is_rejected(self):
        folder=self.copy_archive()
        raw=folder/'hp-p1e+07-of3.4-counted.stdout.txt'
        raw.write_text(raw.read_text(encoding='utf-8')+' ',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'bytes changed'): verify_base(folder)

    def test_rehashed_but_unphysical_state_is_rejected(self):
        folder=self.copy_archive();record=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        case=next(c for c in record['cases'] if c['input']['id']=='hp-p1e+07-of3.4')
        case['output']['gas']['mole_fractions'][0]+=.01
        case['output']['gas']['mole_fractions'][2]-=.01
        for suffix in ('counted','plain'):
            raw=folder/('hp-p1e+07-of3.4-'+suffix+'.stdout.txt')
            value=json.loads(raw.read_text(encoding='utf-8'));value['gas']=case['output']['gas']
            raw.write_text(json.dumps(value),encoding='utf-8')
            entry=next(f for f in record['files'] if f['path']==raw.name)
            entry.update(sha256=digest(raw),bytes=raw.stat().st_size)
        (folder/'manifest.json').write_text(json.dumps(record),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'physical checks'): verify_base(folder)

    def test_independent_reference_success_label_is_insufficient(self):
        record=json.loads((ROOT/'Work2/results/baseline_v1/manifest.json').read_text(encoding='utf-8'))
        value=copy.deepcopy(record)
        value['independent_references'][0]['reference']['mole_fractions'][0]+=.01
        with self.assertRaisesRegex(ValueError,'composition comparison'): verify_independent_record(value)

    def test_cumulative_work_cannot_be_replaced_by_final_iteration(self):
        folder=self.copy_archive();record=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        case=next(c for c in record['cases'] if c['input']['id']=='hp-p1e+07-of3.4')
        case['output']['counts']['newton_steps']=case['output']['final_equilibrium_iterations']
        raw=folder/'hp-p1e+07-of3.4-counted.stdout.txt';raw.write_text(json.dumps(case['output']),encoding='utf-8')
        entry=next(f for f in record['files'] if f['path']==raw.name)
        entry.update(sha256=digest(raw),bytes=raw.stat().st_size)
        (folder/'manifest.json').write_text(json.dumps(record),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'counter relationships'): verify_base(folder)

    def test_work2_archive_is_in_test_fingerprint(self):
        from pipeline import test_records
        files={entry['path'] for entry in test_records(ROOT)}
        self.assertIn('Work2/results/baseline_v1/selection-manifest.json',files)
        self.assertIn('Work2/results/baseline_v1/layers/u015-origin/failed-quality-20261024.json',files)
        self.assertIn('.gitattributes',files)

    def test_archive_git_filter_preserves_mixed_newline_bytes(self):
        # hash-object without -w checks Git's real clean filter without storing a blob.
        data=b'first\r\nsecond\n'
        expected_blob=hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()
        for suffix in ('md','py','c','txt','json'):
            path='Work2/results/baseline_v1/__byte_probe__.'+suffix
            with self.subTest(suffix=suffix):
                run=subprocess.run(['git','hash-object','--stdin','--path='+path],input=data,
                    cwd=ROOT,capture_output=True,check=True)
                self.assertEqual(run.stdout.decode('ascii').strip(),expected_blob)

    def test_frontier_data_has_fixed_verified_membership(self):
        index=json.loads((ROOT/'Work2/research/data/source-index.json').read_text(encoding='utf-8'))
        self.assertEqual(expected(index),json.loads((ROOT/OUTPUT).read_text(encoding='utf-8')))


if __name__=='__main__': unittest.main(verbosity=2)
