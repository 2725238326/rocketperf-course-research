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
import combustion_reference
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
        for text in ('{"value":1,"value":2}', '{"value":1e999}'):
            with self.assertRaises(ValueError): pipeline.strict_json(text)

    def test_missing_input_and_directory_have_failed_records(self):
        for path in (ROOT/'build'/(uuid.uuid4().hex+'.ini'), ROOT/'cases'):
            run_id='test_missing_'+uuid.uuid4().hex[:12]
            with self.assertRaises(ValueError): pipeline.run_case(ROOT,path,run_id=run_id,no_build=True)
            folder=ROOT/'results/local'/run_id
            self.assertEqual(read_json(folder/'run-manifest.json')['status'],'FAILED')
            self.assertFalse((folder/'result.json').exists())

    def test_positive_mutations_and_false_residual_rejected(self):
        for key in pipeline.RESULT_KEYS:
            candidate=copy.deepcopy(self.report);candidate['results'][key]*=2
            with self.subTest(key=key),self.assertRaises(ValueError): pipeline.validate_result(candidate,self.input)
        candidate=copy.deepcopy(self.report);candidate['diagnostics']['relative_area_residual']=1e-9
        with self.assertRaises(ValueError): pipeline.validate_result(candidate,self.input)
        for text in (self.input+'\nunknown=1',self.input.replace('schema_version=1','schema_version=2')):
            with self.assertRaises(ValueError): pipeline.validate_result(self.report,text)

    def test_false_domain_exclusion_and_duplicate_snapshot_rejected(self):
        run=subprocess.run([str(self.binary),'study','area-ratio-ambient',str(self.case)],cwd=ROOT,capture_output=True,text=True,check=True)
        report=pipeline.strict_json(run.stdout)
        with self.assertRaises(ValueError):
            pipeline.validate_study(report,self.input+'\ngamma=1.4',pipeline.DEFAULT_RATIOS,pipeline.DEFAULT_PRESSURES)
        for index in (0,5):
            candidate=copy.deepcopy(report); point=candidate['points'][index]
            point.pop('results');point.pop('diagnostics');point['status']='out_of_domain'
            point['error']='Overexpanded/back-pressure flow is not supported by this model.'
            with self.subTest(index=index),self.assertRaises(ValueError):
                pipeline.validate_study(candidate,self.input,pipeline.DEFAULT_RATIOS,pipeline.DEFAULT_PRESSURES)

    def test_large_flow_scaling_uses_same_residual_contract(self):
        from cycle_validation import validate_cycle
        text=(ROOT/'cases/benchmarks/prescribed_cycle.ini').read_text(encoding='utf-8')
        for flow in (1e6,1e9):
            with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
                case=Path(folder)/'large.ini'
                scaled=text.replace('total_mass_flow_kg_per_s=100','total_mass_flow_kg_per_s='+str(flow)).replace('auxiliary_power_w=10000','auxiliary_power_w='+str(flow*100))
                case.write_text(scaled,encoding='utf-8')
                run=subprocess.run([str(self.binary),'cycle','prescribed',str(case)],cwd=ROOT,capture_output=True,encoding='utf-8')
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertGreater(len(validate_cycle(pipeline.strict_json(run.stdout),scaled)),100)

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

    def test_study_snapshot_and_reject_bad_points(self):
        folder=pipeline.run_case(ROOT,self.case,run_id='test_study_'+uuid.uuid4().hex[:12],no_build=True,study=True)
        report=read_json(folder/'result.json')
        record=read_json(folder/'run-manifest.json')
        self.assertEqual(record['point_counts'],{'ok':19,'out_of_domain':9})
        self.assertEqual(record['command'][1:3],['study','area-ratio-ambient'])
        for failure in ('coordinate','number','status','count','grid'):
            candidate=copy.deepcopy(report)
            if failure=='coordinate': candidate['points'][0]['area_ratio']=2
            if failure=='number': candidate['points'][0]['results']['thrust_n']=float('nan')
            if failure=='status': candidate['points'][0]={'area_ratio':1,'ambient_pressure_pa':0,'status':'numeric_error','error':'failed'}
            if failure=='count': candidate['points'].pop()
            if failure=='grid': candidate['grid']['area_ratios'][0]=True
            with self.subTest(failure=failure),self.assertRaises(ValueError):
                pipeline.validate_study(candidate,self.input,pipeline.DEFAULT_RATIOS,pipeline.DEFAULT_PRESSURES)

    def test_custom_grid_is_archived_and_invalid_grid_rejected(self):
        folder=pipeline.run_case(ROOT,self.case,run_id='test_custom_'+uuid.uuid4().hex[:12],no_build=True,study=True,area_ratios='1,1.6875',ambient_pressures='0,200000')
        record=read_json(folder/'run-manifest.json')
        self.assertEqual(record['requested_grid'],{'area_ratios':[1,1.6875],'ambient_pressures_pa':[0,200000]})
        for value in ('1,','nan','0x1p0',','.join(['1']*33)):
            with self.subTest(value=value),self.assertRaises(ValueError): pipeline.grid_axis(value)

    def test_python_diagnostics_preserve_unicode(self):
        log=ROOT/'build/test-tmp'/('utf8_'+uuid.uuid4().hex+'.log')
        output=pipeline.execute([sys.executable,'-c',"print('中文日志')"],ROOT,log)
        self.assertEqual(output.strip(),'中文日志')
        self.assertEqual(log.read_text(encoding='utf-8').strip(),'中文日志')

    def test_cycle_snapshot_and_false_accounting_rejected(self):
        case=ROOT/'cases/benchmarks/prescribed_cycle.ini'
        folder=pipeline.run_case(ROOT,case,run_id='test_cycle_'+uuid.uuid4().hex[:12],no_build=True,model='prescribed-cycle')
        record=read_json(folder/'run-manifest.json')
        self.assertEqual(record['status'],'SUCCESS'); self.assertGreater(record['accounting_checks'],80)
        self.assertEqual(record['command'][1:3],['cycle','prescribed'])
        broken=read_json(folder/'result.json'); broken['energy']['pump_power_w']*=2
        run_id='test_cycle_bad_'+uuid.uuid4().hex[:12]
        fake=subprocess.CompletedProcess([],0,json.dumps(broken),'')
        with mock.patch.object(pipeline.subprocess,'run',return_value=fake),self.assertRaises(ValueError):
            pipeline.run_case(ROOT,case,run_id=run_id,no_build=True,model='prescribed-cycle')
        self.assertEqual(read_json(ROOT/'results/local'/run_id/'run-manifest.json')['status'],'FAILED')
        self.assertFalse((ROOT/'results/local'/run_id/'result.json').exists())

    def test_cycle_study_run_and_false_comparison_rejected(self):
        case=ROOT/'cases/benchmarks/prescribed_cycle.ini'
        folder=pipeline.run_case(ROOT,case,run_id='test_cycle_study_'+uuid.uuid4().hex[:12],no_build=True,cycle_field='main_area_ratio',cycle_values='10,20,40')
        self.assertEqual(read_json(folder/'run-manifest.json')['study_validation']['counts']['ok'],3)
        broken=read_json(folder/'result.json');broken['points'][2]['metrics']['thrust_change_n']*=2
        run_id='test_study_bad_'+uuid.uuid4().hex[:12]
        with mock.patch.object(pipeline.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(broken),'')),self.assertRaises(ValueError):
            pipeline.run_case(ROOT,case,run_id=run_id,no_build=True,cycle_field='main_area_ratio',cycle_values='10,20,40')
        self.assertEqual(read_json(ROOT/'results/local'/run_id/'run-manifest.json')['status'],'FAILED')


class LifecycleTests(unittest.TestCase):
    def test_nonobject_parameter_dataset_is_controlled_failure(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
            root=Path(folder);atomic_json(root/'data/parameters/bad.json',[])
            with self.assertRaisesRegex(ValueError,'must be an object'): pipeline.test_records(root)
    def test_archive_text_is_part_of_test_identity(self):
        (ROOT/'build/test-tmp').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
            root=Path(folder); path=root/'results/validation/fixture/stdout.txt'
            path.parent.mkdir(parents=True); path.write_text('original',encoding='utf-8')
            for name in ('thermo_data.py','cea_reference.py','combustion_reference.py','cycle_validation.py','gas_checks.py','check_data.py','handoff.py','cycle_study.py','research_tp_reference.py','research_frozen_reference.py','thermal_boundary.py','adiabatic_inlet.py','adiabatic_study.py','feed_candidates.py'):
                atomic_json(root/'tools'/name,{'fixture':True})
            atomic_json(root/'调研/feed_sources.json',[])
            atomic_json(root/'docs/adiabatic-inlet-response.svg',{'fixture':True})
            atomic_json(root/'调研/原始来源/来源文件索引.json',[])
            before=pipeline.test_records(root)
            path.write_text('damaged',encoding='utf-8')
            self.assertNotEqual(before,pipeline.test_records(root))
            self.assertIn(path.relative_to(root).as_posix(),{r['path'] for r in before})
            before_svg=pipeline.test_records(root)
            atomic_json(root/'docs/adiabatic-inlet-response.svg',{'fixture':'changed'})
            self.assertNotEqual(before_svg,pipeline.test_records(root))
            (root/'docs/adiabatic-inlet-response.svg').unlink()
            with self.assertRaises(OSError): pipeline.test_records(root)

    def test_research_navigation_readme_is_not_numeric_test_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
            root=Path(folder)
            for name in ('thermo_data.py','cea_reference.py','combustion_reference.py','cycle_validation.py','gas_checks.py','check_data.py','handoff.py','cycle_study.py','research_tp_reference.py','research_frozen_reference.py','thermal_boundary.py','adiabatic_inlet.py','adiabatic_study.py','feed_candidates.py'):
                atomic_json(root/'tools'/name,{'fixture':True})
            atomic_json(root/'调研/feed_sources.json',[])
            atomic_json(root/'docs/adiabatic-inlet-response.svg',{'fixture':True})
            atomic_json(root/'调研/原始来源/来源文件索引.json',[])
            navigation=root/'results/research/example/README.md'
            navigation.parent.mkdir(parents=True);navigation.write_text('navigation only',encoding='utf-8')
            before=pipeline.test_records(root)
            navigation.write_text('updated navigation',encoding='utf-8')
            self.assertEqual(before,pipeline.test_records(root))
            numeric=navigation.parent/'result.json';numeric.write_text('{"value":1}',encoding='utf-8')
            self.assertNotEqual(before,pipeline.test_records(root))

    def test_parameter_source_index_and_local_refs_are_tracked(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build/test-tmp') as folder:
            root=Path(folder)
            for name in ('thermo_data.py','cea_reference.py','combustion_reference.py','cycle_validation.py','gas_checks.py','check_data.py','handoff.py','cycle_study.py','research_tp_reference.py','research_frozen_reference.py','thermal_boundary.py','adiabatic_inlet.py','adiabatic_study.py','feed_candidates.py'):
                atomic_json(root/'tools'/name,{'fixture':True})
            atomic_json(root/'调研/feed_sources.json',[])
            atomic_json(root/'docs/adiabatic-inlet-response.svg',{'fixture':True})
            index=root/'调研/原始来源/来源文件索引.json'
            atomic_json(index,[])
            atomic_json(root/'data/parameters/fixture.json',{'records':[{'source_refs':['docs/source.md']}]})
            atomic_json(root/'docs/source.md',{'fixture':True})
            before=pipeline.test_records(root)
            atomic_json(index,[{'id':'S01','available':False}])
            after=pipeline.test_records(root)
            self.assertNotEqual(before,after)
            (root/'docs/source.md').unlink()
            with self.assertRaises(OSError): pipeline.test_records(root)

    def test_incomplete_test_report_is_rejected(self):
        with self.assertRaises(ValueError):
            pipeline.verify_test_report({'status':'PASS','checks':[]},{'application':{'sha256':'x'}},'x')

    def test_feed_sources_and_generator_are_in_test_identity(self):
        files = {entry['path'] for entry in pipeline.test_records(ROOT)}
        self.assertIn('tools/feed_candidates.py', files)
        self.assertIn('调研/feed_sources.json', files)
        dataset = read_json(ROOT/'data/parameters/feed_property_candidates.json')
        for identity in dataset['source_files'] + dataset['cea_source_files']:
            self.assertIn(identity['path'], files)

    def test_combustion_reference_preparation_failure_is_recorded(self):
        (ROOT/'build/test-tmp').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='combustion-lifecycle-',dir=ROOT/'build/test-tmp') as folder:
            run=Path(folder)/'run'
            with mock.patch.object(combustion_reference,'check_reference',side_effect=ValueError('invalid CEA reference')),self.assertRaisesRegex(ValueError,'invalid CEA reference'):
                combustion_reference.run_reference(Path(folder)/'missing.exe',run)
            report=read_json(run/'manifest.json')
            self.assertEqual(report['status'],'FAIL')
            self.assertEqual(report['cases'],[])
            with self.assertRaises(FileExistsError): combustion_reference.run_reference(Path(folder)/'missing.exe',run)

    def test_test_failure_replaces_old_pass_report(self):
        (ROOT/'build/test-tmp').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='lifecycle-',dir=ROOT/'build/test-tmp') as folder:
            root=Path(folder); path=root/'build/artifacts/fake/build-manifest.json'
            atomic_json(path,{'core_test':{'path':'fake.exe'},'application':{'path':'fake.exe'}})
            atomic_json(root/'build/debug/test-report.json',{'status':'PASS'})
            atomic_json(root/'tools/thermo_data.py',{'fixture':True})
            atomic_json(root/'tools/cea_reference.py',{'fixture':True})
            atomic_json(root/'tools/combustion_reference.py',{'fixture':True})
            atomic_json(root/'tools/cycle_validation.py',{'fixture':True})
            for name in ('gas_checks.py','check_data.py','handoff.py','cycle_study.py','research_tp_reference.py','research_frozen_reference.py','thermal_boundary.py','adiabatic_inlet.py','adiabatic_study.py','feed_candidates.py'):
                atomic_json(root/'tools'/name,{'fixture':True})
            atomic_json(root/'调研/feed_sources.json',[])
            atomic_json(root/'docs/adiabatic-inlet-response.svg',{'fixture':True})
            atomic_json(root/'调研/原始来源/来源文件索引.json',[])
            with mock.patch.object(pipeline,'build',return_value=path),mock.patch.object(pipeline,'execute',side_effect=ValueError('test failed')),self.assertRaisesRegex(ValueError,'test failed'):
                pipeline.test(root)
            self.assertEqual(read_json(root/'build/debug/test-report.json')['status'],'FAIL')

    def test_preparation_failure_replaces_old_pass_report(self):
        (ROOT/'build/test-tmp').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='lifecycle-',dir=ROOT/'build/test-tmp') as folder:
            root=Path(folder); path=root/'build/artifacts/fake/build-manifest.json'
            atomic_json(path,{'core_test':{'path':'fake.exe'},'application':{'path':'fake.exe'}})
            atomic_json(root/'build/debug/test-report.json',{'status':'PASS'})
            with mock.patch.object(pipeline,'build',return_value=path),mock.patch.object(pipeline,'test_records',side_effect=OSError('missing validation input')),self.assertRaises(OSError):
                pipeline.test(root)
            self.assertEqual(read_json(root/'build/debug/test-report.json')['status'],'FAIL')


if __name__=='__main__': unittest.main(verbosity=2)
