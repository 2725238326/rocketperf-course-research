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
import liquid_anchor
import liquid_feed
import liquid_table
import liquid_combustion
import kerosene_reference
import kerosene_validation
import propellant_comparison
from projectlib import read_json, atomic_json, digest


class ThermoDataTests(unittest.TestCase):
    def test_paired_propellant_archive_and_rehashed_errors(self):
        source=ROOT/'results/research/propellant_comparison_v1'
        self.assertEqual(propellant_comparison.verify(source),(57,8))
        for defect in ('inlet','difference','pressure','thrust','scope','recipe','failure'):
            with self.subTest(defect=defect),tempfile.TemporaryDirectory(dir=ROOT/'build') as temp:
                folder=Path(temp)/'archive';shutil.copytree(source,folder)
                record=read_json(folder/'manifest.json'); filename=None
                if defect=='scope': record['scope']='Flight engine ranking'
                elif defect=='recipe': record['recipes'][0]['exit_code']=False
                elif defect=='failure':
                    filename='representative_A40_p100000_pair-stdout.json'
                    (folder/filename).write_text('{}',encoding='utf-8')
                else:
                    filename='representative_A10_p0_pair-stdout.json'; report=read_json(folder/filename)
                    if defect=='inlet': report['inlets']['methane']['fuel_temperature_k']=140
                    elif defect=='difference': report['methane_minus_kerosene']['isp_s']+=1
                    elif defect=='pressure': report['inputs']['pressure_pa']=5e6
                    elif defect=='thrust': report['kerosene']['geometry']['thrust_n']+=1
                    atomic_json(folder/filename,report)
                if filename: record['files'][filename]=digest(folder/filename)
                atomic_json(folder/'manifest.json',record)
                with self.assertRaises(ValueError): propellant_comparison.verify(folder)

    def test_public_rp1_validation_and_rehashed_semantic_errors(self):
        source = ROOT/'results/validation/kerosene_anchor_v1'
        self.assertEqual(kerosene_validation.verify(source), (33, 21))
        for defect in ('model', 'identity', 'temperature', 'inventory', 'mass_flow', 'scope',
                       'failure_output', 'card', 'warning', 'timestamp'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=ROOT/'build') as temp:
                folder = Path(temp)/'archive'
                shutil.copytree(source, folder)
                record = read_json(folder/'manifest.json')
                filename = None
                if defect == 'timestamp': record['finished_at'] = False
                elif defect == 'scope': record['scope'] = 'Real YF-100K flight result'
                elif defect in ('card', 'warning', 'failure_output'):
                    filename = dict(card='of_2_6_hp.inp', warning='of_2_6_hp-cea-stdout.txt',
                                    failure_output='reject_phase-c-stdout.json')[defect]
                    with (folder/filename).open('a', encoding='utf-8') as stream:
                        stream.write('WARNING: invalid\n')
                else:
                    filename = 'of_2_6_A10-c-stdout.json'
                    report = read_json(folder/filename)
                    if defect == 'model': report['model'] = 'ch4l_o2l_hp_frozen_fixed_area_v1'
                    elif defect == 'identity': report['reactant_dataset_id'] = 'other'
                    elif defect == 'temperature': report['chamber']['temperature_k'] += 1
                    elif defect == 'inventory': report['boundary']['element_inventory_kmol_per_kg'][1] *= 2
                    elif defect == 'mass_flow': report['geometry']['mass_flow_kg_per_s'] *= 1.01
                    atomic_json(folder/filename, report)
                if filename:
                    record['files'][filename] = digest(folder/filename)
                atomic_json(folder/'manifest.json', record)
                with self.assertRaises(ValueError):
                    kerosene_validation.verify(folder)

    def test_kerosene_reference_records_product_boundaries_and_c_results(self):
        folder = ROOT/'results/research/kerosene_products_v3_20261006'
        self.assertEqual(kerosene_reference.verify(folder), 15)
        record = read_json(folder/'manifest.json')
        self.assertEqual(record['summaries']['of_0_5_nine-gas']['status'], 'REJECTED')
        self.assertAlmostEqual(record['summaries']['of_1_0_expanded']['mole_fractions']['C(gr)'][0], .058523)
        self.assertEqual(record['summaries']['probe_anchor_temperature']['rows'],
                         record['summaries']['of_2_6_expanded']['rows'])

    def test_kerosene_false_success_and_changed_reference_are_rejected(self):
        source = ROOT/'results/research/kerosene_products_v3_20261006'
        for defect in ('temperature', 'nozzle', 'failed_status', 'recipe', 'warning', 'schema'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(dir=ROOT/'build') as temp:
                folder = Path(temp)/'archive'
                shutil.copytree(source, folder)
                record = read_json(folder/'manifest.json')
                if defect in ('temperature', 'nozzle', 'failed_status'):
                    filename = 'c-stdout.json'
                    report = read_json(folder/filename)
                    if defect == 'temperature': report['points'][1]['temperature_k'] += 1
                    elif defect == 'nozzle': report['points'][3]['nozzles'] = []
                    else: report['points'][0]['status'] = 'out_of_domain'
                    atomic_json(folder/filename, report)
                    record['files'][filename] = digest(folder/filename)
                elif defect == 'recipe': record['recipes'][0]['ratio'] = True
                elif defect == 'schema': record['schema_version'] = True
                else:
                    filename = 'of_2_6_expanded-stdout.txt'
                    with (folder/filename).open('a', encoding='utf-8') as stream:
                        stream.write('WARNING: invalid result\n')
                    record['files'][filename] = digest(folder/filename)
                atomic_json(folder/'manifest.json', record)
                with self.assertRaises(ValueError):
                    kerosene_reference.verify(folder)

    def test_continuous_liquid_archive_and_explicit_enthalpy_cards(self):
        self.assertEqual(len(liquid_combustion.recipes()),47)
        self.assertEqual(len(liquid_combustion.cea_recipes()),18)
        inlet = liquid_combustion.explicit_inlets()
        card = liquid_combustion.case_card("base_hp",liquid_combustion.CONDITIONS[0],"hp",inlet)
        self.assertIn("h,j/mole=",card)
        self.assertIn("fuel=FEED_CH4 C 1 H 4",card)
        self.assertNotIn("CH4(L)",card)
        source = ROOT/"results/validation/liquid_combustion_v1"
        if source.exists():
            self.assertEqual(liquid_combustion.verify(source),(47,18))
            with self.assertRaises(FileExistsError):
                liquid_combustion.archive("results/validation/liquid_combustion_v1")

    def test_continuous_liquid_semantic_tampering(self):
        import copy
        source = ROOT/"results/validation/liquid_combustion_v1"
        if not source.exists():
            return  # First build still exercises the C/CLI and card contracts.
        for defect in ("scope","run_bool","arguments","timestamp","inventory","reference","binary",
                       "enthalpy","mass","element","heat","phase","basis","chamber","geometry",
                       "card","cea_stream","failure_stdout","source","response","duplicate_manifest",
                       "duplicate_output"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(prefix="liquid-hp-",dir=ROOT/"build") as temp:
                folder = Path(temp)/"archive"
                shutil.copytree(source,folder)
                manifest = read_json(folder/"manifest.json")
                filename = None
                if defect == "scope": manifest["scope"] = "Verified engine performance"
                elif defect == "run_bool": manifest["runs"][0]["exit_code"] = False
                elif defect == "arguments": manifest["runs"][0]["arguments"][3] = "arbitrary-zero"
                elif defect == "timestamp": manifest["finished_at"] = False
                elif defect == "inventory": (folder/"extra").mkdir()
                elif defect == "reference": manifest["liquid_reference_sha256"] = "0"*64
                elif defect == "binary": manifest["c_binary_sha256"] = "0"*64
                elif defect == "response": manifest["responses"][0]["specific_impulse_s"] += 1
                elif defect == "duplicate_manifest":
                    path = folder/"manifest.json"
                    path.write_text(path.read_text(encoding="utf-8").replace("{",'{"schema_version":1,',1),encoding="utf-8")
                elif defect in ("card","cea_stream","failure_stdout","source"):
                    filename = dict(card="base_hp.inp",cea_stream="base_hp-cea-stdout.txt",
                                    failure_stdout="reject_basis-stdout.txt",source=next(iter(liquid_combustion.SOURCE_HASHES)))[defect]
                    path = folder/filename
                    if defect == "card":
                        path.write_text(path.read_text(encoding="utf-8").replace("h,j/mole=","h,cal/mole="),encoding="utf-8")
                    else:
                        path.write_text("ERROR fabricated\n",encoding="utf-8")
                else:
                    filename = "base_A10-stdout.txt"
                    report = copy.deepcopy(read_json(folder/filename))
                    if defect == "enthalpy": report["boundary"]["fuel"]["h_j_per_mol"] += 100
                    elif defect == "mass": report["boundary"]["fuel"]["chemical_molar_mass_kg_per_mol"] = 0.0160428
                    elif defect == "element": report["boundary"]["element_inventory_kmol_per_kg"][0] *= 1.01
                    elif defect == "heat": report["boundary"]["heat_transfer_j_per_kg"] = 1
                    elif defect == "phase": report["inputs"]["feed_phase"] = "gas"
                    elif defect == "basis": report["inputs"]["enthalpy_basis"] = "default-HEOS"
                    elif defect == "chamber": report["chamber"]["temperature_k"] += 0.5
                    elif defect == "geometry": report["geometry"]["mass_flow_kg_per_s"] *= 1.01
                    atomic_json(folder/filename,report)
                    if defect == "duplicate_output":
                        path = folder/filename
                        path.write_text(path.read_text(encoding="utf-8").replace("{",'{"schema_version":1,',1),encoding="utf-8")
                if filename:
                    next(f for f in manifest["files"] if f["path"]==filename)["sha256"] = digest(folder/filename)
                if defect != "duplicate_manifest":
                    atomic_json(folder/"manifest.json",manifest)
                with self.assertRaises(ValueError):
                    liquid_combustion.verify(folder)

    def test_continuous_liquid_preparation_failure_is_retained(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix="liquid-hp-fail-",dir=ROOT/"build") as temp:
            root = Path(temp)
            with patch.object(liquid_combustion,"ROOT",root), \
                 patch.object(liquid_combustion,"explicit_inlets",return_value={}), \
                 patch.object(liquid_combustion,"verified_build",side_effect=ValueError("stale test evidence")), \
                 self.assertRaisesRegex(ValueError,"stale test evidence"):
                liquid_combustion.archive("results/validation/new")
            attempts = list((root/"build/liquid-combustion").glob("*/manifest.json"))
            self.assertEqual(len(attempts),1)
            record = read_json(attempts[0])
            self.assertEqual(record["status"],"FAIL")
            self.assertEqual(record["error"],"stale test evidence")
            self.assertFalse((root/"results/validation/new").exists())

    def test_continuous_liquid_final_validation_failure_is_retained(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix="liquid-final-fail-",dir=ROOT/"build") as temp:
            root = Path(temp)
            paths = ("build/fixture/program.exe","build/reference/cea-v3.3.4/data/thermo.inp",
                     "build/reference/cea-build-v3.3.4/source/cea.exe",
                     "build/reference/cea-build-v3.3.4/thermo.lib",
                     "build/reference/cea-build-v3.3.4/trans.lib")
            for name in paths:
                path = root/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b"fixture, not an executable or scientific reference")
            build = root/"build/fixture/build-manifest.json"
            atomic_json(build,dict(application=dict(path=paths[0])))
            atomic_json(build.parent/"test-report.json",{"fixture":True})
            atomic_json(root/"tests/reference/cea/manifest.json",{"fixture":True})
            fixed = dict(executable_sha256=digest(root/paths[2]),
                         compiled_database_hashes={n:digest(root/"build/reference/cea-build-v3.3.4"/n)
                                                   for n in ("thermo.lib","trans.lib")})
            with patch.object(liquid_combustion,"ROOT",root), \
                 patch.object(liquid_combustion,"explicit_inlets",return_value={}), \
                 patch.object(liquid_combustion,"verified_build",return_value=build), \
                 patch.object(liquid_combustion,"check_reference",return_value=fixed), \
                 patch.object(liquid_combustion,"SOURCE_HASHES",{}), \
                 patch.object(liquid_combustion,"THERMO_SHA",digest(root/paths[1])), \
                 patch.object(liquid_combustion,"git",side_effect=lambda path,*args,**kw:
                              SimpleNamespace(stdout="" if args[0]=="status" else liquid_combustion.COMMIT+"\n")), \
                 patch.object(liquid_combustion,"recipes",return_value=[]), \
                 patch.object(liquid_combustion,"cea_recipes",return_value=[]), \
                 patch.object(liquid_combustion,"evaluate",return_value=({},[])), \
                 patch.object(liquid_combustion,"verify",side_effect=ValueError("final semantic rejection")), \
                 self.assertRaisesRegex(ValueError,"final semantic rejection"):
                liquid_combustion.archive("results/validation/new")
            attempts = list((root/"build/liquid-combustion").glob("*/manifest.json"))
            self.assertEqual(len(attempts),1)
            self.assertEqual(read_json(attempts[0])["status"],"FAIL")
            self.assertFalse((root/"results/validation/new").exists())

    def test_liquid_table_data_and_archives(self):
        self.assertEqual(liquid_table.check_generated(),2)
        self.assertEqual(len(liquid_table.recipes()),22)
        source = ROOT/'results/validation/liquid_table_v1'
        if source.exists():
            self.assertEqual(liquid_table.verify(source),22)
            with self.assertRaises(FileExistsError):
                liquid_table.archive('results/validation/liquid_table_v1')

    def test_liquid_table_report_and_archival_tampering(self):
        import copy
        tables,_ = liquid_table.reference()
        expected = liquid_table.expected_report('Methane',121,11e6,tables)
        for field in ('density_kg_per_m3','h_j_per_mol','h_j_per_kg',
                      'eos_molar_mass_kg_per_mol','chemical_molar_mass_kg_per_mol'):
            altered = copy.deepcopy(expected)
            altered['results'][field] *= 1.001
            with self.subTest(field=field), self.assertRaises(ValueError):
                liquid_table.validate_report(altered,'Methane',121,11e6,tables)
        source = ROOT/'results/validation/liquid_table_v1'
        if not source.exists():
            return  # Initial build before publishing the required archive.
        for defect in ('scope','run_bool','run_arguments','timestamp','inventory','reference',
                       'binary','phase','density','enthalpy','mass','basis','failure_stdout',
                       'duplicate_manifest_key','duplicate_build_key','duplicate_test_key'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(prefix='table-',dir=ROOT/'build') as temp:
                folder = Path(temp)/'archive'
                shutil.copytree(source,folder)
                manifest = read_json(folder/'manifest.json')
                filename = None
                if defect == 'scope': manifest['scope'] = 'Flight engine performance'
                elif defect == 'run_bool': manifest['runs'][0]['exit_code'] = False
                elif defect == 'run_arguments': manifest['runs'][0]['arguments'][3] = 'gas'
                elif defect == 'timestamp': manifest['finished_at'] = False
                elif defect == 'inventory': (folder/'unexpected').mkdir()
                elif defect == 'reference': manifest['reference_sha256'] = '0'*64
                elif defect == 'binary': manifest['binary_sha256'] = '0'*64
                elif defect == 'failure_stdout':
                    filename = 'reject_two_phase-stdout.txt'
                    (folder/filename).write_text('{}',encoding='utf-8')
                elif defect.startswith('duplicate_'):
                    filename = {'duplicate_build_key':'build-manifest.json',
                                'duplicate_test_key':'test-report.json'}.get(defect)
                    path = folder/(filename or 'manifest.json')
                    content = path.read_text(encoding='utf-8')
                    path.write_text(content.replace('{','{"schema_version": 1,',1),encoding='utf-8')
                else:
                    filename = 'methane_node-stdout.txt'
                    report = read_json(folder/filename)
                    if defect == 'phase': report['inputs']['phase'] = 'gas'
                    if defect == 'density': report['results']['density_kg_per_m3'] *= 1.01
                    if defect == 'enthalpy': report['results']['h_j_per_mol'] += 100
                    if defect == 'mass': report['results']['chemical_molar_mass_kg_per_mol'] = 0.0160428
                    if defect == 'basis': report['provenance']['enthalpy_basis'] = 'default-HEOS'
                    atomic_json(folder/filename,report)
                if filename:
                    next(f for f in manifest['files'] if f['path']==filename)['sha256'] = digest(folder/filename)
                if defect != 'duplicate_manifest_key':
                    atomic_json(folder/'manifest.json',manifest)
                rejection = (self.assertRaisesRegex(ValueError, 'Duplicate JSON key')
                             if defect.startswith('duplicate_') else self.assertRaises(ValueError))
                with rejection:
                    liquid_table.verify(folder)

    def test_liquid_table_failures_keep_truthful_attempt(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        for stage in ('preparation', 'semantic'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory(prefix='table-fail-',dir=ROOT/'build') as temp:
                root = Path(temp)
                build = root/'build/fixture/build-manifest.json'
                atomic_json(build, {'application': {'path': 'build/fixture/program.exe'}})
                atomic_json(build.parent/'test-report.json', {'fixture': True})
                (build.parent/'program.exe').write_bytes(b'fixture, not executable')
                failure = ValueError(stage+' rejected')
                with patch.object(liquid_table, 'ROOT', root), \
                     patch.object(liquid_table, 'check_generated', return_value=2), \
                     patch.object(liquid_table, 'verified_build', **(
                         {'side_effect': failure} if stage == 'preparation' else {'return_value': build})), \
                     patch.object(liquid_table, 'git', return_value=SimpleNamespace(stdout='a'*40+'\n')), \
                     patch.object(liquid_table, 'recipes', return_value=[('query', ['fixture'], 0)]), \
                     patch.object(liquid_table.subprocess, 'run',
                                  return_value=SimpleNamespace(stdout=b'{}', stderr=b'', returncode=0)), \
                     patch.object(liquid_table, 'verify', side_effect=failure), \
                     self.assertRaisesRegex(ValueError, stage+' rejected'):
                    liquid_table.archive('results/validation/new')
                attempts = list((root/'build/liquid-table').glob('*/manifest.json'))
                self.assertEqual(len(attempts), 1)
                record = read_json(attempts[0])
                self.assertEqual(record['status'], 'FAIL')
                self.assertEqual(record['error'], stage+' rejected')
                self.assertFalse((root/'results/validation/new').exists())
                if stage == 'semantic':
                    self.assertEqual((attempts[0].parent/'query-stdout.txt').read_bytes(), b'{}')

    def test_liquid_feed_archive_recomputes_without_coolprop(self):
        self.assertEqual(liquid_feed.verify(ROOT/'results/research/liquid_feed_reference_v1'),
                         dict(nodes=407,interior=700,saturation=107,ideal=14,queries=24))
        with self.assertRaises(FileExistsError):
            liquid_feed.archive('results/research/liquid_feed_reference_v1')

    def test_liquid_feed_semantic_tampering_with_rehashed_files(self):
        source = ROOT/'results/research/liquid_feed_reference_v1'
        for defect in ('scope','package','run_bool','timestamp','counts_bool','inventory',
                       'density','residual','chemical_zero','saturation','phase','ideal_cp',
                       'finite_pressure_common_mode','coefficient','offgrid','mass','extra',
                       'query','summary','duplicate_key','node_bool','gas_branch'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(prefix='feed-',dir=ROOT/'build') as temp:
                folder = Path(temp)/'archive'
                shutil.copytree(source,folder)
                manifest = read_json(folder/'manifest.json')
                filename = None
                if defect == 'scope': manifest['scope'] = 'Flight engine validated'
                elif defect == 'package': manifest['package']['version'] = 'latest'
                elif defect == 'run_bool': manifest['run']['exit_code'] = False
                elif defect == 'timestamp': manifest['finished_at'] = True
                elif defect == 'counts_bool': manifest['counts']['ideal'] = True
                elif defect == 'inventory': (folder/'extra').mkdir()
                elif defect == 'summary': manifest['summary']['Methane']['max_enthalpy_error_j_per_mol'] = 0
                elif defect in ('chemical_zero','mass','offgrid','query'):
                    filename = 'tables.json'
                    table = read_json(folder/filename)
                    if defect == 'chemical_zero': table['Methane']['nodes'][0]['aligned_h_j_per_mol'] += 100
                    if defect == 'mass': table['Methane']['nodes'][0]['aligned_h_j_per_kg'] *= 1.01
                    if defect == 'offgrid': table['Methane']['interpolation_errors'][0]['density_relative_error'] = 0
                    if defect == 'query': table['Oxygen']['queries'][6]['output'] = {'status':'ok'}
                    atomic_json(folder/filename,table)
                else:
                    filename = 'raw-output.json'
                    raw = read_json(folder/filename)
                    fluid = raw['fluids']['Methane']
                    if defect == 'density': fluid['nodes'][0]['rhomolar'] *= 1.001
                    if defect == 'residual': fluid['nodes'][0]['h_residual_j_per_mol'] = 0
                    if defect == 'saturation': fluid['boundary']['saturation'][0]['pressure_pa'] *= 1.001
                    if defect == 'phase':
                        fluid['nodes'][0]['phase_code'] = 3
                        fluid['nodes'][0]['phase_name'] = 'supercritical_liquid'
                    if defect == 'ideal_cp': fluid['ideals'][0]['cp0_j_per_mol_k'] += 1
                    if defect == 'finite_pressure_common_mode':
                        fluid['ideals'][2]['finite_pressure_h_j_per_mol'] += 10
                        fluid['ideals'][2]['finite_pressure_h_residual_j_per_mol'] += 10
                    if defect == 'coefficient': fluid['exported_json'] = fluid['exported_json'].replace('9.91243972','9.91243973')
                    if defect == 'extra': fluid['nodes'][0]['pump_power_w'] = 1
                    if defect == 'node_bool': fluid['nodes'][0]['phase_code'] = False
                    if defect == 'gas_branch': fluid['nodes'][0]['rhomolar'] = 10
                    atomic_json(folder/filename,raw)
                    if defect == 'duplicate_key':
                        content = (folder/filename).read_text(encoding='utf-8')
                        (folder/filename).write_text(content.replace('"version": "7.1.0"', '"version": "7.1.0", "version": "7.1.0"',1),encoding='utf-8')
                if filename:
                    next(f for f in manifest['files'] if f['path']==filename)['sha256'] = digest(folder/filename)
                atomic_json(folder/'manifest.json',manifest)
                with self.assertRaises(ValueError):
                    liquid_feed.verify(folder)

    def test_liquid_feed_query_and_failure_record(self):
        from unittest import mock
        fluid = read_json(ROOT/'results/research/liquid_feed_reference_v1/tables.json')['Methane']
        nodes = fluid['nodes']
        for t in (float('nan'),float('inf'),True,0):
            with self.subTest(t=t), self.assertRaises(ValueError):
                liquid_feed.interpolation(nodes,'Methane',dict(fluid='Methane',temperature_k=t,pressure_pa=1e6))
        with tempfile.TemporaryDirectory(prefix='feed-fail-',dir=ROOT/'build') as temp:
            root = Path(temp)
            with mock.patch.object(liquid_feed,'ROOT',root), \
                 mock.patch.object(liquid_feed,'sources',side_effect=ValueError('source identity changed')), \
                 self.assertRaisesRegex(ValueError,'source identity changed'):
                liquid_feed.archive('results/research/fixture')
            manifests = list((root/'build/liquid-feed').glob('*/manifest.json'))
            self.assertEqual(len(manifests),1)
            self.assertEqual(read_json(manifests[0])['status'],'FAIL')
            self.assertFalse((root/'results/research/fixture').exists())

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
                elif kind=='liquid-anchor-validation':
                    self.assertEqual(liquid_anchor.verify(manifest.parent),(21,6))
                elif kind=='liquid-table-validation':
                    self.assertEqual(liquid_table.verify(manifest.parent),22)
                elif kind=='liquid-combustion-validation':
                    self.assertEqual(liquid_combustion.verify(manifest.parent),(47,18))
                elif kind=='kerosene-anchor-validation':
                    self.assertEqual(kerosene_validation.verify(manifest.parent),(33,21))
                else: self.fail(f'Unknown validation archive type: {kind}')
        self.assertGreater(combustion_count,0,'Expected actual C/CEA result archive')

    def test_liquid_anchor_archive_and_semantic_tampering(self):
        source = ROOT/'results/validation/liquid_anchor_v1'
        # Before the first archive is created, unit/CLI tests still verify the C
        # contract. Once archived, no numeric evidence may bypass replay checks.
        if not source.exists():
            self.assertEqual(len(liquid_anchor.recipes()), 21)
            return
        self.assertEqual(liquid_anchor.verify(source), (21,6))
        with self.assertRaises(FileExistsError):
            liquid_anchor.archive(source.relative_to(ROOT).as_posix())
        for defect in ('scope','exit_bool','duplicate','anchor','card','trace','enthalpy',
                       'inventory','phase','density','thrust','pressure_correction','comparison_bool',
                       'limits','reference_nul','undeclared','run_object','cea_run_object',
                       'timestamp_type','timestamp_order','run_extra','cea_run_extra'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory(prefix='anchor-',dir=ROOT/'build') as temp:
                folder = Path(temp)/'archive'
                shutil.copytree(source, folder)
                manifest = read_json(folder/'manifest.json')
                filename = None
                if defect == 'scope': manifest['scope'] = 'Real flight engine performance'
                elif defect == 'exit_bool': manifest['runs'][0]['exit_code'] = False
                elif defect == 'duplicate': manifest['runs'][1] = manifest['runs'][0]
                elif defect == 'anchor': manifest['anchors'][0]['assigned_enthalpy_j_per_mol'] += 1
                elif defect == 'comparison_bool': manifest['comparisons']['base_hp'][0]['difference'] = False
                elif defect == 'undeclared': (folder/'undeclared').mkdir()
                elif defect == 'run_object': manifest['runs'][0] = None
                elif defect == 'cea_run_object': manifest['cea_runs'][0] = []
                elif defect == 'timestamp_type': manifest['finished_at'] = True
                elif defect == 'timestamp_order': manifest['finished_at'] = '2020-01-01T00:00:00+00:00'
                elif defect == 'run_extra': manifest['runs'][0]['unexpected'] = 'not part of a run'
                elif defect == 'cea_run_extra': manifest['cea_runs'][0]['unexpected'] = 'not part of a run'
                elif defect == 'card':
                    filename = 'base_rocket.inp'
                    (folder/filename).write_text(liquid_anchor.case_card('base_rocket',3.4,'rocket').replace('nfz=1','nfz=2'),encoding='utf-8')
                elif defect == 'trace':
                    filename = 'base_hp.out'
                    (folder/filename).write_bytes((folder/filename).read_bytes().replace(b'1.000000E-07',b'1.000000E-08'))
                elif defect == 'reference_nul':
                    filename = 'base_hp.out'
                    (folder/filename).write_bytes((folder/filename).read_bytes()+b'\x00')
                else:
                    filename = 'base_A10-stdout.txt'
                    report = read_json(folder/filename)
                    if defect == 'enthalpy': report['boundary']['fuel_h_j_per_kg'] += 100
                    elif defect == 'inventory': report['boundary']['element_inventory_kmol_per_kg'][0] *= 2
                    elif defect == 'phase': report['inputs']['feed_phase'] = 'gas'
                    elif defect == 'density': report['boundary']['density_kg_per_m3'] = 1141
                    elif defect == 'thrust': report['geometry']['thrust_n'] *= 2
                    elif defect == 'pressure_correction': report['boundary']['pressure_correction_applied'] = 0
                    elif defect == 'limits': report['limitations'] = ['Flight engine validated']
                    atomic_json(folder/filename,report)
                if filename:
                    next(item for item in manifest['files'] if item['path']==filename)['sha256'] = digest(folder/filename)
                atomic_json(folder/'manifest.json',manifest)
                with self.assertRaises(ValueError):
                    liquid_anchor.verify(folder)

    def test_liquid_anchor_preparation_failure_is_archived(self):
        from unittest import mock
        with tempfile.TemporaryDirectory(prefix='anchor-failure-',dir=ROOT/'build') as temp:
            root=Path(temp)
            with mock.patch.object(liquid_anchor,'ROOT',root), \
                 mock.patch.object(liquid_anchor,'verified_build',side_effect=ValueError('test evidence stale')), \
                 self.assertRaisesRegex(ValueError,'test evidence stale'):
                liquid_anchor.archive('results/validation/fixture')
            manifests=list((root/'build/liquid-anchor').glob('*/manifest.json'))
            self.assertEqual(len(manifests),1)
            record=read_json(manifests[0])
            self.assertEqual(record['status'],'FAIL')
            self.assertIn('finished_at',record)
            self.assertFalse((root/'results/validation/fixture').exists())

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
