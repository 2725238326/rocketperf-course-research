import tempfile
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import handoff


class HandoffTests(unittest.TestCase):
    def setUp(self): (ROOT/'build/test-tmp').mkdir(parents=True,exist_ok=True)

    def test_handoff_manifest_is_verifiable(self):
        with tempfile.TemporaryDirectory(prefix='handoff-', dir=ROOT / 'build/test-tmp') as folder:
            package = handoff.create(ROOT, Path(folder) / 'package', 'Release', fixture=True)
            record = handoff.verify(package)
            self.assertEqual(record['status'], 'PASS')
            self.assertTrue((package / 'VERIFY.txt').is_file())

    def test_modified_binary_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='handoff-', dir=ROOT / 'build/test-tmp') as folder:
            package = handoff.create(ROOT, Path(folder) / 'package', 'Release', fixture=True)
            binary = package / handoff.read_json(package / 'handoff-manifest.json')['binary']['path']
            binary.write_bytes(binary.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                handoff.verify(package)

    def test_missing_declared_file_and_path_escape_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='handoff-',dir=ROOT/'build/test-tmp') as folder:
            package=handoff.create(ROOT,Path(folder)/'package','Release',fixture=True)
            record=handoff.read_json(package/'handoff-manifest.json')
            (package/'START-HERE.md').unlink()
            with self.assertRaises(ValueError): handoff.verify(package)
            record['files'][0]['path']='../outside'
            handoff.atomic_json(package/'handoff-manifest.json',record)
            with self.assertRaises(ValueError): handoff.verify(package)

    def test_receiver_runs_success_and_rejection(self):
        with tempfile.TemporaryDirectory(prefix='handoff-',dir=ROOT/'build/test-tmp') as folder:
            package=handoff.create(ROOT,Path(folder)/'package','Release',fixture=True)
            receipt=handoff.receive(package,'test receiver','maintenance',Path(folder)/'receipt.json')
            self.assertEqual(receipt['status'],'PASS')
            self.assertEqual([r['exit_code'] for r in receipt['checks']],[0,4])
            with self.assertRaises(FileExistsError): handoff.receive(package,'receiver','maintenance',Path(folder)/'receipt.json')

    def test_dirty_workspace_cannot_create_delivery(self):
        with mock.patch.object(handoff,'git',return_value=mock.Mock(stdout=' M example.py')):
            with self.assertRaisesRegex(ValueError,'Commit reviewed'): handoff.create(ROOT)

    def test_malformed_identity_and_smoke_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='handoff-',dir=ROOT/'build/test-tmp') as folder:
            package=handoff.create(ROOT,Path(folder)/'package','Release',fixture=True)
            record=handoff.read_json(package/'handoff-manifest.json')
            for field,value in (('binary',None),('project_head',True),('smoke_tests',[None,None])):
                with self.subTest(field=field):
                    changed=dict(record);changed[field]=value
                    handoff.atomic_json(package/'handoff-manifest.json',changed)
                    with self.assertRaises(ValueError): handoff.verify(package)


if __name__ == '__main__': unittest.main(verbosity=2)
