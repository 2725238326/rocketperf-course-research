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
            self.assertEqual(record['schema_version'], 2)
            self.assertEqual(record['next_task'], handoff.select_next_task(
                handoff.read_json(package/'project/tasks.json')))
            self.assertTrue((package / 'VERIFY.txt').is_file())

    def test_next_task_follows_context_and_preserves_pending_status(self):
        report = dict(id='DOC-001', status='READY', priority=2)
        research = dict(id='RES-007', status='READY', priority=1)
        state = dict(tasks=[report, research], context=dict(next_tasks=['RES-007']))
        self.assertIs(handoff.select_next_task(state), research)
        for status in ('PLANNED','BLOCKED','ACTIVE','REVIEW'):
            with self.subTest(status=status):
                research['status'] = status
                self.assertIs(handoff.select_next_task(state), research)
        research['status'] = 'DONE'
        self.assertIs(handoff.select_next_task(state), report)
        report['status'] = 'CANCELLED'
        self.assertIsNone(handoff.select_next_task(state))

    def test_next_task_fallback_is_stable_and_malformed_snapshot_rejected(self):
        later = dict(id='RES-002', status='READY', priority=1)
        first = dict(id='RES-001', status='READY', priority=1)
        report = dict(id='DOC-001', status='READY', priority=2)
        state = dict(tasks=[report, later, first], context=dict(next_tasks=[]))
        self.assertIs(handoff.select_next_task(state), first)
        state['tasks'].reverse()
        self.assertIs(handoff.select_next_task(state), first)
        for bad in (None, dict(tasks=[None], context=dict(next_tasks=[])),
                    dict(tasks=[first, first], context=dict(next_tasks=[])),
                    dict(tasks=[dict(first, priority=True)], context=dict(next_tasks=[])),
                    dict(tasks=[first], context=dict(next_tasks=['UNKNOWN'])),
                    dict(tasks=[first], context=dict(next_tasks=['RES-001','RES-001']))):
            with self.subTest(snapshot=bad), self.assertRaises(ValueError):
                handoff.select_next_task(bad)

    def test_next_task_tampering_and_missing_snapshot_rejected(self):
        with tempfile.TemporaryDirectory(prefix='handoff-', dir=ROOT/'build/test-tmp') as folder:
            package = handoff.create(ROOT, Path(folder)/'package', 'Release', fixture=True)
            original = handoff.read_json(package/'handoff-manifest.json')
            for change in (None, dict(original['next_task'], priority=True)):
                with self.subTest(next_task=change):
                    record = dict(original, next_task=change)
                    handoff.atomic_json(package/'handoff-manifest.json', record)
                    with self.assertRaisesRegex(ValueError, 'next task'):
                        handoff.verify(package)
            record = dict(original)
            record['files'] = [item for item in original['files'] if item['path'] != 'project/tasks.json']
            handoff.atomic_json(package/'handoff-manifest.json', record)
            with self.assertRaisesRegex(ValueError, 'Required handoff files'):
                handoff.verify(package)

    def test_legacy_v1_package_remains_readable(self):
        with tempfile.TemporaryDirectory(prefix='handoff-', dir=ROOT/'build/test-tmp') as folder:
            package = handoff.create(ROOT, Path(folder)/'package', 'Release', fixture=True)
            record = handoff.read_json(package/'handoff-manifest.json')
            record['schema_version'] = 1
            record['files'] = [item for item in record['files'] if item['path'] != 'project/tasks.json']
            (package/'project/tasks.json').unlink()
            handoff.atomic_json(package/'handoff-manifest.json', record)
            self.assertEqual(handoff.verify(package)['schema_version'], 1)

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
