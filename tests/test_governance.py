"""State transitions, provenance gates and architectural boundaries."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import project
from render_architecture import expected_architecture
from projectlib import QUALITY_CHECKS, atomic_json, canonical, fingerprint, lock, read_json


class GovernanceTests(unittest.TestCase):
    def test_assignment_diagram_requirements_links_and_generation(self):
        outputs = expected_architecture(ROOT)
        source = outputs["docs/architecture/assignment.svg"]
        svg = ET.fromstring(source)
        self.assertEqual(svg.attrib["viewBox"], "0 0 1920 1080")
        text = "".join(svg.itertext())
        for requirement in ("REQ-01", "REQ-02", "REQ-03", "REQ-04", "REQ-05", "REQ-06", "REQ-07"):
            self.assertIn(requirement, text)
        for required in ("朱雀三号", "长征十号乙", "HP 平衡", "冻结喷管", "CEA 同源对照",
                         "程序源代码", "发布版", "展示 PPT", "研究报告", "未覆盖"):
            self.assertIn(required, text)
        namespace = {"s": "http://www.w3.org/2000/svg"}
        self.assertFalse(svg.findall(".//s:script", namespace))
        self.assertFalse(svg.findall(".//s:image", namespace))
        for element in svg.findall(".//s:a", namespace):
            target = element.attrib["href"]
            self.assertNotIn("://", target)
            self.assertTrue((ROOT / "docs/architecture" / target).resolve().is_file())
        self.assertEqual((ROOT / "docs/architecture/assignment.svg").read_text(encoding="utf-8"), source)
        self.assertIn('data-view="assignment" aria-selected="true"', outputs["docs/architecture/index.html"])

    def test_editable_eol_identity_and_raw_archive_bytes(self):
        code=self.root/'example.py'
        code.write_bytes(b'print(1)\n')
        before=fingerprint(self.root)
        code.write_bytes(b'print(1)\r\n')
        self.assertEqual(before,fingerprint(self.root))
        archive=self.root/'results/validation/fixture/stdout.txt'
        archive.parent.mkdir(parents=True);archive.write_bytes(b'result\n')
        before=fingerprint(self.root)
        archive.write_bytes(b'result\r\n')
        self.assertNotEqual(before,fingerprint(self.root))
    def setUp(self):
        (ROOT/'build/test-tmp').mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='governance-',dir=ROOT/'build/test-tmp')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        atomic_json(self.root/'project/policy.json',{'wip_limit':1})
        (self.root/'base.md').write_text('Historical baseline',encoding='utf-8')
        records=[]
        for tid,status,deps,artifact in [('BASE-001','DONE',[],'base.md'),('WORK-001','READY',['BASE-001'],'result.txt'),('NEXT-001','PLANNED',['WORK-001'],'next.txt'),('SIDE-001','READY',['BASE-001'],'side.txt')]:
            records.append({'id':tid,'title':tid,'status':status,'priority':1,'depends_on':deps,'required_artifacts':[artifact],'acceptance':['Readable validated artifact'],'owner':None,'note':'fixture','verification':{'kind':'historical','reference':'base.md'} if status=='DONE' else None})
        state={'schema_version':1,'revision':1,'context':{'phase':'test','evidence_cutoff':'2026-10-01','next_tasks':['WORK-001'],'facts':['fixture']},'tasks':records,'events':[]}
        for record in records: project.event_for(state,record,None,'fixture','seed')
        atomic_json(self.root/'project/tasks.json',state)
        project.render_views(self.root,state)

    def state(self): return read_json(self.root/'project/tasks.json')
    def task(self,tid): return next(t for t in self.state()['tasks'] if t['id']==tid)
    def change(self,action,tid='WORK-001',actor='root',**kw):
        return project.transition(self.root,tid,action,actor,'test reason',**kw)
    def proof(self):
        (self.root/'result.txt').write_text('real fixture result',encoding='utf-8')
        relative='build/quality/latest.json'
        report={'schema_version':1,'kind':'quality','status':'PASS','input_fingerprint':fingerprint(self.root),'checks':[{'name':name,'status':'PASS'} for name in sorted(QUALITY_CHECKS)]}
        atomic_json(self.root/relative,report)
        return relative

    def test_start_owner_and_wip(self):
        self.change('start')
        self.assertEqual(self.task('WORK-001')['owner'],'root')
        before=self.state()
        with self.assertRaises(ValueError): self.change('start','SIDE-001')
        self.assertEqual(self.state(),before)
        with self.assertRaises(ValueError): self.change('block',actor='other')

    def test_dependency_and_missing_artifact(self):
        with self.assertRaises(ValueError): self.change('start','NEXT-001')
        self.change('start')
        proof=self.proof()
        (self.root/'result.txt').unlink()
        # Missing output also changes fingerprint; neither path permits submission.
        with self.assertRaises(ValueError): self.change('submit',evidence=proof)
        with self.assertRaises(ValueError): self.change('complete')

    def test_verified_completion_unlocks_dependency(self):
        self.change('start'); proof=self.proof()
        self.change('submit',evidence=proof)
        self.assertEqual(self.task('WORK-001')['status'],'REVIEW')
        self.change('complete')
        self.assertEqual(self.task('WORK-001')['status'],'DONE')
        self.assertEqual(self.task('NEXT-001')['status'],'READY')
        self.assertEqual(project.validate_registry(self.root,self.state()),[])
        view=(self.root/'worknow.md').read_text(encoding='utf-8')
        self.assertIn('NEXT-001',view)
        self.assertNotIn('WORK-001',view)  # Completed tasks are not suggested for resumption.

    def test_stale_and_incomplete_quality_rejected(self):
        self.change('start'); proof=self.proof()
        (self.root/'result.txt').write_text('changed after test',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'stale'): self.change('submit',evidence=proof)
        proof=self.proof(); report=read_json(self.root/proof); report['checks']=report['checks'][:1]; atomic_json(self.root/proof,report)
        with self.assertRaises(ValueError): self.change('submit',evidence=proof)

    def test_complete_rechecks_freshness(self):
        self.change('start'); self.change('submit',evidence=self.proof())
        (self.root/'result.txt').write_text('post-review change',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'stale'): self.change('complete')
        self.assertEqual(self.task('WORK-001')['status'],'REVIEW')

    def test_quality_shapes_duplicates_and_version_rejected(self):
        self.change('start'); proof=self.proof(); valid=read_json(self.root/proof)
        for mode in ('list','entry','duplicate','name','version'):
            payload=copy.deepcopy(valid)
            if mode=='list': payload=[]
            if mode=='entry': payload['checks'][0]=1
            if mode=='duplicate': payload['checks'].append(payload['checks'][0])
            if mode=='name': payload['checks'][0]['name']=[]
            if mode=='version': payload['schema_version']=True
            atomic_json(self.root/proof,payload)
            with self.subTest(mode=mode),self.assertRaises(ValueError): self.change('submit',evidence=proof)

    def test_block_handoff_and_resume(self):
        self.change('start'); self.change('block')
        self.change('handoff',new_owner='maintainer')
        with self.assertRaises(ValueError): self.change('unblock')
        self.change('unblock',actor='maintainer')
        self.assertEqual(self.task('WORK-001')['status'],'READY')

    def test_review_reopen_returns_to_active(self):
        self.change('start'); self.change('submit',evidence=self.proof()); self.change('reopen')
        self.assertEqual(self.task('WORK-001')['status'],'ACTIVE')
        self.assertIsNone(self.task('WORK-001')['verification'])

    def test_done_reopen_revokes_unstarted_dependents(self):
        self.change('start');self.change('submit',evidence=self.proof());self.change('complete')
        self.change('reopen')
        self.assertEqual(self.task('WORK-001')['status'],'READY')
        self.assertEqual(self.task('NEXT-001')['status'],'PLANNED')

    def test_cycle_duplicate_and_unsafe_artifact_are_rejected(self):
        before=self.state()
        for tid,deps,artifacts in [('CYCLE-001',['CYCLE-001'],['x.txt']),('WORK-001',[],['x.txt']),('BAD-001',[],['../outside.txt'])]:
            with self.subTest(tid=tid),self.assertRaises(ValueError):
                project.add_task(self.root,tid,'title','root',deps,artifacts,['criterion'],1)
        self.assertEqual(before,self.state())

    def test_event_and_state_tampering_detected(self):
        state=self.state(); state['events'][0]['note']='rewritten'
        self.assertTrue(project.validate_registry(self.root,state))
        state=self.state();state['tasks'][1]['status']='ACTIVE';state['tasks'][1]['owner']='other'
        self.assertTrue(any('history' in x for x in project.validate_registry(self.root,state)))

    def test_amend_preserves_contract_history_and_freezes_review(self):
        project.amend_task(self.root,'WORK-001','root','scope refined',acceptance=['New explicit criterion'])
        self.assertEqual(self.task('WORK-001')['acceptance'],['New explicit criterion'])
        self.assertIn('contract_before',self.state()['events'][-1]['details'])
        self.change('start');self.change('submit',evidence=self.proof())
        with self.assertRaises(ValueError): project.amend_task(self.root,'WORK-001','root','change',title='new')

    def test_context_edit_requires_owner_and_preserves_history(self):
        with self.assertRaises(ValueError): project.amend_context(self.root,'WORK-001','root','update',phase='new')
        self.change('start')
        before=self.state()['context']
        project.amend_context(self.root,'WORK-001','root','data verified',phase='new',next_tasks=['NEXT-001'],evidence_cutoff='2026-10-02')
        self.assertEqual(self.state()['events'][-1]['details']['context_before'],before)
        self.assertEqual(self.state()['context']['next_tasks'],['NEXT-001'])
        self.assertEqual(project.validate_registry(self.root,self.state()),[])
        self.assertIn('NEXT-001',(self.root/'worknow.md').read_text(encoding='utf-8'))
        for changes in ({'next_tasks':['BASE-001']},{'phase':''},{'evidence_cutoff':'yesterday'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError): project.amend_context(self.root,'WORK-001','root','invalid',**changes)
        with self.assertRaises(ValueError): project.amend_context(self.root,'WORK-001','other','update',phase='wrong')

    def test_raw_evidence_change_invalidates_proof(self):
        archive=self.root/'调研/原始来源/a.txt';archive.parent.mkdir(parents=True);archive.write_text('old',encoding='utf-8')
        self.change('start');proof=self.proof()
        archive.write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'stale'): self.change('submit',evidence=proof)

    def test_lock_rejects_concurrent_mutation(self):
        before=self.state()
        with lock(self.root):
            with self.assertRaises(ValueError): self.change('start')
        self.assertEqual(self.state(),before)

    def test_work2_scope_and_generated_views_do_not_invalidate_acceptance(self):
        project.amend_task(self.root,'WORK-001','root','Work2 deliverable',required_artifacts=['Work2/result.txt'])
        target=self.root/'Work2/result.txt';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('scoped result',encoding='utf-8')
        self.change('start');proof=self.proof()
        board=(self.root/'Work2/docs/tasks.md').read_text(encoding='utf-8')
        self.assertIn('WORK-001',board)
        self.assertNotIn('SIDE-001',board)
        self.assertIn('SIDE-001',(self.root/'docs/tasks.md').read_text(encoding='utf-8'))
        before=fingerprint(self.root)
        self.change('submit',evidence=proof);self.change('complete')
        self.assertEqual(before,fingerprint(self.root))
        self.assertNotIn('WORK-001',(self.root/'Work2/worknow.md').read_text(encoding='utf-8'))
        rules=self.root/'Work2/rules.md';rules.write_text('changed rule',encoding='utf-8')
        self.assertNotEqual(before,fingerprint(self.root))

    def test_work2_original_same_size_tamper_and_missing_manifest_rejected(self):
        import work2_sources
        for relative in work2_sources.RAW_PATHS:
            path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'original')
        self.assertTrue(work2_sources.check_sources(self.root)['issues'])
        work2_sources.capture(self.root)
        self.assertEqual(work2_sources.check_sources(self.root)['issues'],[])
        with self.assertRaises(ValueError): work2_sources.capture(self.root)
        (self.root/work2_sources.RAW_PATHS[0]).write_bytes(b'modified')
        report=work2_sources.check_sources(self.root)
        self.assertTrue(any('bytes changed' in issue for issue in report['issues']))
        (self.root/work2_sources.RAW_PATHS[1]).unlink()
        self.assertTrue(any('missing' in issue for issue in work2_sources.check_sources(self.root)['issues']))

    def test_research_provenance_rejects_tamper_missing_source_and_unknown_value(self):
        import work2_research
        raw=self.root/'Work2/research/raw/fixture.txt'
        raw.parent.mkdir(parents=True);raw.write_bytes(b'original')
        record={'id':'W2-T01','available':True,'path':raw.relative_to(self.root).as_posix(),
                'bytes':8,'sha256':hashlib.sha256(b'original').hexdigest(),'read_scope':'read fixture'}
        atomic_json(self.root/work2_research.INDEX,{'sources':[record]})
        self.assertEqual(work2_research.verify(self.root)['issues'],[])
        raw.write_bytes(b'modified')
        self.assertTrue(work2_research.verify(self.root)['issues'])
        raw.write_bytes(b'original')
        atomic_json(self.root/'Work2/research/data/claims.json',{'claims':[{'id':'C1','classification':'verified_fact','source_ids':['absent']}]})
        atomic_json(self.root/'Work2/research/data/parameter-observations.json',{'observations':[{'id':'P1','classification':'unknown','value':42,'source_ids':[]}]})
        issues=work2_research.verify(self.root)['issues']
        self.assertTrue(any('Unknown source' in issue for issue in issues))
        self.assertTrue(any('contains a value' in issue for issue in issues))

    def test_grok_path_normalization_and_trace_gate_without_network(self):
        import subprocess
        pwsh=shutil.which('pwsh')
        self.assertIsNotNone(pwsh,'Project requires PowerShell syntax/entry checks')
        config=self.root/'fixture-config.txt'
        script=ROOT/'调研/scripts/research.ps1'
        for index,base in enumerate(['https://example.invalid','https://example.invalid/v1','https://example.invalid/v1/responses']):
            config.write_text(base+'\n'+'sk-'+'x'*32,encoding='utf-8')
            wrapper="""
param($ScriptPath,$Config,$Destination,$Trace)
function Invoke-RestMethod {
  param($Uri,$Method,$Headers,$ContentType,$Body,$TimeoutSec)
  if ($Uri -ne 'https://example.invalid/v1/responses') { throw 'Unexpected normalized route' }
  $output = @(@{type='message';content=@(@{type='output_text';text='fixture answer'})})
  if ($Trace -eq 'yes') { $output += @{type='web_search_call';status='completed'} }
  return @{model='fixture';status='completed';output=$output;usage=@{}}
}
& $ScriptPath -Topic fixture -PromptFile $Config -OutputDirectory $Destination -ConfigPath $Config -CutoffDate 2026-10-24 -RequireSearchTrace
"""
            wrapper_path=self.root/'wrapper.ps1';wrapper_path.write_text(wrapper,encoding='utf-8')
            out=self.root/f'output-{index}'
            done=subprocess.run([pwsh,'-NoProfile','-File',str(wrapper_path),str(script),str(config),str(out),'yes'],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(done.returncode,0,done.stderr)
            data=read_json(out/'fixture.json')
            self.assertEqual(data['evidence_class'],'search_trace_and_answer')
        failed=self.root/'no-trace'
        done=subprocess.run([pwsh,'-NoProfile','-File',str(wrapper_path),str(script),str(config),str(failed),'no'],capture_output=True,text=True,encoding='utf-8')
        self.assertNotEqual(done.returncode,0)
        self.assertEqual(read_json(failed/'fixture.json')['evidence_class'],'process_only')

    def test_research_round_membership_does_not_expand_on_append(self):
        from work2_survey_data import FIRST_ROUND_IDS, first_round_sources
        self.assertEqual(len(FIRST_ROUND_IDS),46)
        original=[{'id':sid,'available':True} for sid in sorted(FIRST_ROUND_IDS)]
        expanded=original+[{'id':'W2-V01','available':True},{'id':'W2-V02','available':False}]
        self.assertEqual(first_round_sources({'sources':expanded}),original)

    def test_research_reuse_preserves_date_and_refuses_changed_original(self):
        from work2_research import INDEX, LEGACY_INDEX, reuse
        original=self.root/'调研/原始来源/paper.txt'
        original.parent.mkdir(parents=True,exist_ok=True);original.write_bytes(b'paper')
        atomic_json(self.root/LEGACY_INDEX,[{'id':'OLD','url':'https://example.invalid/paper',
                    'available':True,'file':'paper.txt','bytes':5,
                    'sha256':hashlib.sha256(b'paper').hexdigest(),'saved_at':'2026-09-29T00:00:00Z'}])
        record=reuse('W2-VL01','OLD',self.root)
        self.assertEqual(record['retrieved_at'],'2026-09-29T00:00:00Z')
        self.assertEqual(read_json(self.root/INDEX)['sources'][0]['read_scope'],'downloaded_only')
        original.write_bytes(b'other')
        with self.assertRaisesRegex(ValueError,'identity mismatch'): reuse('W2-VL02','OLD',self.root)
        self.assertEqual(len(read_json(self.root/INDEX)['sources']),1)

    def test_vehicle_evidence_rejects_unknown_values_and_unread_sources(self):
        from work2_research import INDEX
        from work2_vehicle_data import verify
        source=self.root/'original.txt';source.write_text('engine statement',encoding='utf-8')
        atomic_json(self.root/INDEX,{'sources':[{'id':'W2-V01','available':True,'path':'original.txt',
                    'read_scope':'downloaded_only'}]})
        atomic_json(self.root/'Work2/research/data/vehicle-evidence-v1.json',{'observations':[
                    {'id':'U001','classification':'unknown','value':0,'source_ids':['W2-V01'],'short_quote':'engine'}]})
        issues=verify(self.root)
        self.assertTrue(any('Unknown vehicle parameter contains a value' in issue for issue in issues))
        self.assertTrue(any('Unread/unusable vehicle source' in issue for issue in issues))

    def test_missing_proof_snapshot_detected(self):
        self.change('start');self.change('submit',evidence=self.proof())
        proof_path=self.task('WORK-001')['verification']['path']
        (self.root/proof_path).write_text('{}',encoding='utf-8')
        self.assertTrue(any('snapshot' in x for x in project.validate_registry(self.root,self.state())))

    def test_module_dependency_guard(self):
        shutil.copytree(ROOT/'src',self.root/'src')
        shutil.copytree(ROOT/'include',self.root/'include')
        modules=read_json(ROOT/'project/modules.json')
        atomic_json(self.root/'project/modules.json',modules)
        for module in modules['modules']:
            for relative in module['checks']:
                path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture',encoding='utf-8')
        self.assertEqual(project.architecture_checks(self.root),[])
        source=self.root/'src/core/root.c'
        source.write_text('#include "case_file.h"\n'+source.read_text(encoding='utf-8'),encoding='utf-8')
        self.assertTrue(any('Forbidden dependency' in x for x in project.architecture_checks(self.root)))
        thermo=self.root/'src/thermo/mixture.c'
        thermo.write_text(thermo.read_text(encoding='utf-8')+'\nvoid fixture_io(void) { printf("not pure"); }\n',encoding='utf-8')
        self.assertTrue(any('Core purity boundary violated: src/thermo/mixture.c' in x for x in project.architecture_checks(self.root)))
        cycle=self.root/'src/cycle/components.c'
        cycle.write_text(cycle.read_text(encoding='utf-8')+'\nvoid fixture_io(void) { printf("not pure"); }\n',encoding='utf-8')
        self.assertTrue(any('Core purity boundary violated: src/cycle/components.c' in x for x in project.architecture_checks(self.root)))

    def test_secret_detection_does_not_print_secret(self):
        secret='sk-'+'a'*32
        self.assertTrue(project.SECRET.search(secret))
        self.assertFalse(project.SECRET.search('Bearer ' + '<runtime credential>'))
        self.assertFalse(project.SECRET.search('https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence'))
        self.assertTrue(project.SECRET.search('Authorization: Bearer ' + secret))
        self.assertTrue(project.SECRET.search('key="' + secret + '"'))


if __name__=='__main__': unittest.main(verbosity=2)
