"""Failure truthfulness, schema/provenance and immutable execution records."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import pipeline
from projectlib import atomic_json, digest, read_json


class ResultContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build=pipeline.verified_build(ROOT,'Release',require_tests=True)
        manifest=read_json(cls.build)
        cls.binary=ROOT/manifest['application']['path']
        cls.case=ROOT/'cases/benchmarks/air_mach2_vacuum.ini'
        cls.input=cls.case.read_text(encoding='utf-8')
        result=subprocess.run([str(cls.binary),'run',str(cls.case)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        cls.report=pipeline.strict_json(result.stdout)

    def test_valid_and_invalid_report_shapes(self):
        pipeline.validate_result(self.report,self.input)
        for payload in ({},[],{'status':'ok'}):
            with self.subTest(payload=payload),self.assertRaises(ValueError): pipeline.validate_result(payload,self.input)

    def test_numeric_provenance_and_missing_limits(self):
        for field,value in [('input',123),('case','wrong'),('result',float('nan')),('limits',[])]:
            candidate=copy.deepcopy(self.report)
            if field=='input': candidate['inputs']['gamma']=value
            if field=='case': candidate['case']['id']=value
            if field=='result': candidate['results']['thrust_n']=value
            if field=='limits': candidate['limitations']=value
            with self.subTest(field=field),self.assertRaises(ValueError): pipeline.validate_result(candidate,self.input)
        with self.assertRaises(ValueError): pipeline.strict_json('{"value":NaN}')

    def test_success_snapshot_and_duplicate_reservation(self):
        run_id='test_success_'+uuid.uuid4().hex[:12]
        folder=pipeline.run_case(ROOT,self.case,run_id=run_id,no_build=True)
        record=read_json(folder/'run-manifest.json')
        self.assertEqual(record['status'],'SUCCESS')
        self.assertEqual(record['input_sha256'],digest(folder/'input.ini'))
        self.assertEqual(record['output_sha256'],digest(folder/'result.json'))
        with self.assertRaises(FileExistsError): pipeline.run_case(ROOT,self.case,run_id=run_id,no_build=True)

    def test_domain_failure_is_archived(self):
        run_id='test_domain_'+uuid.uuid4().hex[:12]
        with self.assertRaises(ValueError): pipeline.run_case(ROOT,ROOT/'tests/fixtures/overexpanded.ini',run_id=run_id,no_build=True)
        folder=ROOT/'results/local'/run_id
        self.assertEqual(read_json(folder/'run-manifest.json')['status'],'FAILED')
        self.assertFalse((folder/'result.json').exists())

    def test_fake_success_json_is_not_a_successful_run(self):
        run_id='test_schema_'+uuid.uuid4().hex[:12]
        fake=subprocess.CompletedProcess([],0,'{"ok":true}','')
        with mock.patch.object(pipeline.subprocess,'run',return_value=fake),self.assertRaises(ValueError):
            pipeline.run_case(ROOT,self.case,run_id=run_id,no_build=True)
        folder=ROOT/'results/local'/run_id
        self.assertEqual(read_json(folder/'run-manifest.json')['status'],'FAILED')
        self.assertFalse((folder/'result.json').exists())

    def test_timeout_and_start_failure_always_recorded(self):
        for error in [subprocess.TimeoutExpired(['fake'],1),OSError('simulated process start failure')]:
            run_id='test_failure_'+uuid.uuid4().hex[:12]
            with self.subTest(error=type(error).__name__),mock.patch.object(pipeline.subprocess,'run',side_effect=error),self.assertRaises(ValueError):
                pipeline.run_case(ROOT,self.case,run_id=run_id,no_build=True)
            record=read_json(ROOT/'results/local'/run_id/'run-manifest.json')
            self.assertEqual(record['status'],'FAILED')
            self.assertEqual(record['timed_out'],isinstance(error,subprocess.TimeoutExpired))

    def test_snapshot_copy_failure_recorded(self):
        run_id='test_copy_'+uuid.uuid4().hex[:12]
        with mock.patch.object(pipeline.shutil,'copy2',side_effect=OSError('simulated copy failure')),self.assertRaises(ValueError):
            pipeline.run_case(ROOT,self.case,run_id=run_id,no_build=True)
        self.assertEqual(read_json(ROOT/'results/local'/run_id/'run-manifest.json')['status'],'FAILED')

    def test_stale_build_not_reused(self):
        run_id='test_stale_'+uuid.uuid4().hex[:12]
        with mock.patch.object(pipeline,'source_records',return_value=[]),self.assertRaises(ValueError):
            pipeline.run_case(ROOT,self.case,run_id=run_id,no_build=True)
        self.assertEqual(read_json(ROOT/'results/local'/run_id/'run-manifest.json')['status'],'FAILED')

    def test_python_diagnostics_preserve_unicode(self):
        log=ROOT/'build/test-tmp'/('utf8_'+uuid.uuid4().hex+'.log')
        output=pipeline.execute([sys.executable,'-c',"print('中文日志')"],ROOT,log)
        self.assertEqual(output.strip(),'中文日志')
        self.assertEqual(log.read_text(encoding='utf-8').strip(),'中文日志')


class LifecycleTests(unittest.TestCase):
    def test_test_failure_replaces_old_pass_report(self):
        (ROOT/'build/test-tmp').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='lifecycle-',dir=ROOT/'build/test-tmp') as folder:
            root=Path(folder); path=root/'build/artifacts/fake/build-manifest.json'
            atomic_json(path,{'core_test':{'path':'fake.exe'},'application':{'path':'fake.exe'}})
            atomic_json(root/'build/debug/test-report.json',{'status':'PASS'})
            with mock.patch.object(pipeline,'build',return_value=path),mock.patch.object(pipeline,'execute',side_effect=ValueError('test failed')),self.assertRaises(ValueError):
                pipeline.test(root)
            self.assertEqual(read_json(root/'build/debug/test-report.json')['status'],'FAIL')


if __name__=='__main__': unittest.main(verbosity=2)
