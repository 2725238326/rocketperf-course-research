"""Black-box CLI contract tests; standard library only, no engine data."""
import argparse
import copy
import json
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from combustion_reference import compare_report
from cycle_validation import validate_cycle
from cycle_study import validate_study as validate_cycle_study
import liquid_anchor
import liquid_table
import liquid_combustion

ROOT = Path(__file__).resolve().parents[1]
BINARY = None


class CliTests(unittest.TestCase):
    def test_rp1_success_and_input_rejection(self):
        data = ['cea-v3.3.4-rp1-o2l-assigned-v1', 'liquid', 'RP-1', 'O2(L)',
                '10000000', '2.6', '298.15', '90.170']
        run = self.run_app('combustion', 'hp-rp1', *data)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report['model'], 'rp1_o2l_hp_assigned_v1')
        self.assertAlmostEqual(report['chamber']['temperature_k'], 3724.01, delta=.02)
        run = self.run_app('combustion', 'frozen-rp1', *data, '10', '0', '.01')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertAlmostEqual(json.loads(run.stdout)['geometry']['specific_impulse_s'], 310.5717305, places=5)
        for index, value, code in ((0,'other',4),(1,'gas',4),(2,'CH4(L)',4),(3,'O2',4),
                                  (4,'9999999',4),(5,'1',4),(6,'350',4),(7,'nan',2)):
            changed = list(data); changed[index] = value
            run = self.run_app('combustion', 'hp-rp1', *changed)
            self.assertEqual(run.returncode, code, run.stderr)
            self.assertFalse(run.stdout)

    @classmethod
    def setUpClass(cls):
        if BINARY is None:
            raise unittest.SkipTest("CLI tests require --binary <path>; use tools/pipeline.py test")
        cls.base = (ROOT / "cases/benchmarks/air_mach2_vacuum.ini").read_text(encoding="utf-8")
        cls.reference = json.loads((ROOT / "tests/reference/air_mach2.json").read_text(encoding="utf-8"))
        cls.cycle = (ROOT / 'cases/benchmarks/prescribed_cycle.ini').read_text(encoding='utf-8')
        (ROOT / "build/test-tmp").mkdir(parents=True, exist_ok=True)

    def setUp(self):
        # Owned, unique directory under build; no existing user files are removed.
        self.temp = tempfile.TemporaryDirectory(prefix="cli 空格 ", dir=ROOT / "build/test-tmp")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def run_app(self, *args):
        return subprocess.run([str(BINARY), *map(str, args)], cwd=ROOT, capture_output=True,
                              text=True, encoding="utf-8", timeout=15, check=False)

    def case(self, text):
        path = self.folder / "算例 file.ini"
        path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        return path

    def assert_failed(self, text, exit_code=3):
        result = self.run_app("run", self.case(text))
        self.assertEqual(result.returncode, exit_code, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.strip())

    def test_liquid_table_success_and_rejections(self):
        tables,_ = liquid_table.reference()
        for name,args,code in liquid_table.recipes():
            with self.subTest(name=name):
                run = self.run_app(*args)
                self.assertEqual(run.returncode,code,run.stderr)
                if code == 0:
                    self.assertEqual(run.stderr,"")
                    liquid_table.validate_report(json.loads(run.stdout),args[2],float(args[4]),float(args[5]),tables)
                    self.assertEqual(self.run_app(*args).stdout,run.stdout)
                else:
                    self.assertEqual(run.stdout,"")
                    self.assertTrue(run.stderr.startswith("Usage" if code == 2 else
                                                         "invalid_argument:" if name in ("reject_negative","reject_zero")
                                                         else "out_of_domain:"))

    def test_continuous_liquid_hp_nozzle_and_rejections(self):
        for name,args,code in liquid_combustion.recipes():
            with self.subTest(name=name):
                run = self.run_app(*args)
                self.assertEqual(run.returncode,code,run.stderr)
                if code == 0:
                    self.assertEqual(run.stderr,"")
                    report = json.loads(run.stdout)
                    fields = ["fuel_temperature_k","fuel_pressure_pa","oxidizer_temperature_k",
                              "oxidizer_pressure_pa","pressure_pa","oxidizer_fuel_mass_ratio"]
                    if args[1] == "frozen-liquid-state":
                        fields += ["area_ratio","ambient_pressure_pa","throat_area_m2"]
                    declared = dict(feed_phase=args[4],enthalpy_basis=args[3],
                                    **dict(zip(fields,map(float,args[5:]))))
                    liquid_combustion.check_report(report,declared,args[1],declared.get("area_ratio"))
                    self.assertEqual(self.run_app(*args).stdout,run.stdout)
                else:
                    self.assertEqual(run.stdout,"")
                    self.assertTrue(run.stderr.startswith("Usage" if code == 2 else
                        "invalid_argument:" if name in ("reject_zero","reject_throat") else "out_of_domain:"))

    def test_analytic_reference_and_unicode_path(self):
        result = self.run_app("run", self.case(self.base))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["case"]["kind"], "synthetic_benchmark")
        self.assertEqual(report["model"], "ideal_constant_gamma_v1")
        for key, expected in self.reference["expected"].items():
            with self.subTest(key=key):
                self.assertTrue(math.isclose(report["results"][key], expected,
                                             rel_tol=self.reference["relative_tolerance"], abs_tol=1e-12))
        self.assertLess(report["diagnostics"]["relative_area_residual"], 1e-8)
        self.assertIn("no chemistry", " ".join(report["limitations"]))

    def test_ambient_pressure_difference(self):
        first = json.loads(self.run_app("run", self.case(self.base)).stdout)
        second = json.loads(self.run_app("run", self.case(self.base.replace("ambient_pressure_pa=0", "ambient_pressure_pa=100000"))).stdout)
        self.assertAlmostEqual(first["results"]["thrust_n"] - second["results"]["thrust_n"], 168.75, places=8)

    def test_deterministic_output(self):
        path = self.case(self.base)
        first = self.run_app("run", path)
        second = self.run_app("run", path)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_bom_crlf_and_whitespace(self):
        payload = b"\xef\xbb\xbf" + self.base.replace("gamma=1.4", "  gamma = 1.4  ").replace("\n", "\r\n").encode("utf-8")
        result = self.run_app("run", self.case(payload))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_required_fields_duplicates_unknown_and_model(self):
        variants = [
            self.base.replace("gamma=1.4\n", ""),
            self.base + "gamma=1.4\n",
            self.base + "pressure_mpa=1\n",
            self.base.replace("schema_version=1", "schema_version=2"),
            self.base.replace("ideal_constant_gamma_v1", "unimplemented_equilibrium"),
            self.base.replace("synthetic_benchmark", "verified_engine"),
            self.base.replace("source_ref=docs/benchmarks.md#mach2", "source_ref="),
            self.base.replace("case_id=air_mach2_vacuum", "case_id=Bad Name"),
        ]
        for index, text in enumerate(variants):
            with self.subTest(index=index): self.assert_failed(text)

    def test_invalid_numbers(self):
        for number in ["nan", "inf", "1e999", "1e-999", "0x1.4p0", "1.4abc", "1.4 # comment", "1,4", "", "1e+"]:
            with self.subTest(number=number):
                self.assert_failed(self.base.replace("gamma=1.4", "gamma=" + number))

    def test_physical_domain(self):
        for old, new in [("gamma=1.4", "gamma=1"), ("area_ratio=1.6875", "area_ratio=0.5"),
                         ("throat_area_m2=0.001", "throat_area_m2=-1"),
                         ("ambient_pressure_pa=0", "ambient_pressure_pa=200000")]:
            with self.subTest(new=new): self.assert_failed(self.base.replace(old, new), 4)

    def test_embedded_nul_long_lines_and_file_limits(self):
        self.assert_failed(self.base.replace("gamma=1.4", "gamma=1.4\x00hidden"))
        self.assert_failed("#" + "x" * 600 + "\n" + self.base)
        self.assert_failed("# comment\n" * 130 + self.base)
        self.assert_failed("", 3)

    def test_metadata_json_escaping(self):
        source = 'note\\path"quoted'
        result = self.run_app("run", self.case(self.base.replace("docs/benchmarks.md#mach2", source)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["case"]["source_ref"], source)

    def test_help_version_usage_and_missing_file(self):
        self.assertEqual(self.run_app("--help").returncode, 0)
        self.assertIn("0.1.0", self.run_app("--version").stdout)
        self.assertEqual(self.run_app().returncode, 2)
        self.assertEqual(self.run_app("run").returncode, 2)
        missing = self.run_app("run", self.folder / "missing.ini")
        self.assertEqual(missing.returncode, 3)
        self.assertEqual(missing.stdout, "")

    def test_fixed_liquid_anchor_success_and_geometry(self):
        baseline = None
        for name, args, code in liquid_anchor.recipes():
            if code:
                continue
            run = self.run_app(*args)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stderr, "")
            report = json.loads(run.stdout)
            if name == "old_gas":
                self.assertGreater(report["chamber"]["temperature_k"], baseline["chamber"]["temperature_k"])
                continue
            self.assertEqual(report["reactant_dataset_id"], liquid_anchor.ANCHOR_DATASET)
            self.assertIs(report["boundary"]["pressure_correction_applied"], False)
            of = report["inputs"]["oxidizer_fuel_mass_ratio"]
            expected_h = (-89233000/16.04246 - of*12979000/31.9988)/(1+of)
            self.assertAlmostEqual(report["boundary"]["inlet_mixture_h_j_per_kg"], expected_h, places=7)
            self.assertLessEqual(abs(report["diagnostics"]["enthalpy_residual_j_per_kg"]), 0.01)
            self.assertAlmostEqual(report["chamber"]["h_j_per_kg"], expected_h, delta=0.01)
            self.assertNotIn("density_kg_per_m3", report["boundary"])
            if name == "base_hp":
                baseline = report
            if "geometry" in report:
                geometry = report["geometry"]
                self.assertAlmostEqual(geometry["mass_flow_kg_per_s"],
                                       1e7*geometry["throat_area_m2"]/report["nozzle"]["cstar_m_per_s"], places=8)
                self.assertAlmostEqual(geometry["thrust_n"], geometry["mass_flow_kg_per_s"]*
                                       report["nozzle"]["effective_velocity_m_per_s"], places=7)
                if name.startswith("base_"):
                    self.assertEqual(report["chamber"], baseline["chamber"])

    def test_fixed_liquid_anchor_failure_protocol_and_strict_syntax(self):
        for name, args, code in liquid_anchor.recipes():
            if not code:
                continue
            with self.subTest(name=name):
                run = self.run_app(*args)
                self.assertEqual(run.returncode, code, run.stderr)
                self.assertEqual(run.stdout, "")
                self.assertTrue(run.stderr.startswith("Usage" if code == 2 else "out_of_domain:"))
        for numeric in ("inf", "NaN", "1e999", "0x1p0", "111.643x"):
            args = liquid_anchor.arguments(liquid_anchor.inputs(), "hp-liquid")
            args[-2] = numeric
            self.assertEqual(self.run_app(*args).returncode, 2)

    def test_area_ambient_study_scan_reports_domain_points(self):
        result = self.run_app("study", "area-ratio-ambient", self.case(self.base),
                              "--area-ratios", "1,1.6875",
                              "--ambient-pressures", "0,100000,200000")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(set(report), {"schema_version", "program_version", "study", "base_inputs",
                                       "grid", "points", "limitations"})
        self.assertEqual(report["study"]["id"], "S1_area_ratio_ambient")
        self.assertEqual(report["grid"]["area_ratios"], [1.0, 1.6875])
        self.assertEqual(report["grid"]["ambient_pressures_pa"], [0.0, 100000.0, 200000.0])
        self.assertEqual(len(report["points"]), 6)
        self.assertEqual([(p["area_ratio"], p["ambient_pressure_pa"]) for p in report["points"]],
                         [(1.0, 0.0), (1.0, 100000.0), (1.0, 200000.0),
                          (1.6875, 0.0), (1.6875, 100000.0), (1.6875, 200000.0)])
        self.assertEqual(report["points"][0]["status"], "ok")
        self.assertEqual(report["points"][4]["status"], "ok")
        self.assertEqual(report["points"][5]["status"], "out_of_domain")
        self.assertEqual(set(report["points"][0]), {"area_ratio", "ambient_pressure_pa", "status", "results", "diagnostics"})
        self.assertEqual(set(report["points"][5]), {"area_ratio", "ambient_pressure_pa", "status", "error"})
        self.assertGreater(report["points"][3]["results"]["thrust_n"],
                           report["points"][4]["results"]["thrust_n"])
        self.assertIn("research scenario inputs", " ".join(report["limitations"]))

    def test_area_ambient_study_grid_option_validation(self):
        for options in (("--area-ratios", "0.5"), ("--area-ratios", "1,"),
                        ("--area-ratios", "1, "), ("--area-ratios", "1,,2"),
                        ("--area-ratios", ",".join(["1"] * 33)),
                        ("--area-ratios", "1", "--area-ratios", "2"),
                        ("--ambient-pressures", "0", "--ambient-pressures", "1"),
                        ("--area-ratios", "0x1p0"),
                        ("--ambient-pressures", "nan"),
                        ("--unknown", "1")):
            with self.subTest(options=options):
                result = self.run_app("study", "area-ratio-ambient", self.case(self.base), *options)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr.strip())

    def test_numeric_failure_is_not_a_successful_study(self):
        path=self.case(self.base.replace("stagnation_temperature_k=300", "stagnation_temperature_k=1e308"))
        result=self.run_app("study", "area-ratio-ambient", path)
        self.assertEqual(result.returncode,4,result.stderr)
        report=json.loads(result.stdout)
        self.assertTrue(any(p['status']=='numeric_error' for p in report['points']))
        self.assertTrue(result.stderr.strip())

    def test_real_nasa9_species_reference(self):
        reference = json.loads((ROOT / 'tests/reference/nasa9_cantera.json').read_text(encoding='utf-8'))
        for state in reference['states']:
            if state['temperature_k'] != 300.0:
                continue
            with self.subTest(species=state['id']):
                result = self.run_app('thermo', state['id'], '300')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                report = json.loads(result.stdout)
                self.assertEqual(report['model'], 'nasa9_species_v1')
                self.assertEqual(report['dataset_id'], 'cea-v3.3.4-neutral-cho-n-v1')
                self.assertEqual(report['species'], state['id'])
                self.assertEqual(report['reference_pressure_pa'], 100000)
                for key in ('cp_j_per_kg_k', 'h_j_per_kg', 's_j_per_kg_k'):
                    self.assertTrue(math.isclose(report[key], state[key], rel_tol=2e-11, abs_tol=1e-6))

    def test_thermo_invalid_inputs_are_not_success_results(self):
        for species, temperature, code in [('fixture_gas','300',4), ('H2O','6000.1',4),
                                          ('H2O','199',4), ('O2','nan',2), ('O2','0',4),
                                          ('O2','0x1p2',2), ('O2','300,400',2)]:
            with self.subTest(species=species, temperature=temperature):
                result = self.run_app('thermo', species, temperature)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertTrue(result.stderr.strip())

    def test_combustion_matches_pinned_cea(self):
        references = json.loads((ROOT / 'tests/reference/cea/manifest.json').read_text(encoding='utf-8'))
        cases = {case['id']: case for case in references['cases']}
        for mode, area, arguments, ref_id in [
            ('tp', None, ('3000', '10000000', '3.4', '298.15', '298.15'), 'ch4_o2_tp'),
            ('hp', None, ('10000000', '3.4', '298.15', '298.15'), 'ch4_o2_hp'),
            ('frozen', 10, ('10000000', '3.4', '298.15', '298.15', '10', '0'), 'ch4_o2_rocket_frozen_chamber'),
            ('frozen', 40, ('10000000', '3.4', '298.15', '298.15', '40', '0'), 'ch4_o2_rocket_frozen_chamber')]:
            with self.subTest(mode=mode, area=area):
                result = self.run_app('combustion', mode, *arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                report = json.loads(result.stdout)
                self.assertGreaterEqual(len(compare_report(report, cases[ref_id], mode, area)), 20)

    def test_combustion_rejects_invalid_inputs_without_output(self):
        for arguments, code in [
            ((), 2), (('hp',), 2), (('liquid', '10000000', '3.4', '298.15', '298.15'), 2),
            (('hp', 'nan', '3.4', '298.15', '298.15'), 2),
            (('hp', '0x1p2', '3.4', '298.15', '298.15'), 2),
            (('hp', '10000000', '-3.4', '298.15', '298.15'), 4),
            (('hp', '10000000', '3.4', '90', '298.15'), 4),
            (('tp', '999', '10000000', '3.4', '298.15', '298.15'), 4),
            (('frozen', '10000000', '3.4', '298.15', '298.15', '40', '100000'), 4),
            (('frozen', '10000000', '3.4', '298.15', '298.15', '0.5', '0'), 4)]:
            with self.subTest(arguments=arguments):
                result = self.run_app('combustion', *arguments)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertTrue(result.stderr.strip())

    def test_tp_frozen_fixed_geometry_scaling_and_backpressure(self):
        arguments=('3300','5000000','3.436135057526204','298.15','298.15','10')
        reports=[]
        for ambient, throat in [('0','0.03388974483'),('0','0.06777948966'),('5000','0.03388974483')]:
            run=self.run_app('combustion','frozen-tp',*arguments,ambient,throat)
            self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(run.stderr,'')
            report=json.loads(run.stdout);reports.append(report)
            self.assertEqual(report['model'],'ch4_o2_tp_frozen_fixed_area_v1')
            self.assertEqual(report['chamber']['temperature_k'],3300)
            self.assertEqual(report['diagnostics']['hp_iterations'],0)
            geometry=report['geometry'];nozzle=report['nozzle']
            self.assertTrue(math.isclose(geometry['mass_flow_kg_per_s'],float(throat)*nozzle['throat']['mass_flux_kg_per_m2_s'],rel_tol=1e-12))
        base,doubled,ambient=reports
        self.assertTrue(math.isclose(doubled['geometry']['mass_flow_kg_per_s'],2*base['geometry']['mass_flow_kg_per_s'],rel_tol=1e-12))
        self.assertTrue(math.isclose(doubled['geometry']['thrust_n'],2*base['geometry']['thrust_n'],rel_tol=1e-12))
        self.assertEqual(doubled['geometry']['specific_impulse_s'],base['geometry']['specific_impulse_s'])
        self.assertEqual(ambient['geometry']['mass_flow_kg_per_s'],base['geometry']['mass_flow_kg_per_s'])
        self.assertTrue(math.isclose(base['geometry']['thrust_n']-ambient['geometry']['thrust_n'],5000*base['geometry']['exit_area_m2'],abs_tol=1e-7))

    def test_tp_frozen_rejects_invalid_geometry_and_temperature(self):
        base=['3300','5000000','3.4','298.15','298.15','10','0','0.01']
        for index,value,code in [(0,'999',4),(5,'0.5',4),(6,'100000',4),(7,'0',4),(7,'-1',4),(7,'nan',2),(7,'1e308',4)]:
            args=list(base);args[index]=value
            with self.subTest(index=index,value=value):
                run=self.run_app('combustion','frozen-tp',*args)
                self.assertEqual(run.returncode,code,run.stderr);self.assertEqual(run.stdout,'');self.assertTrue(run.stderr.strip())
        self.assertEqual(self.run_app('combustion','frozen-tp',*base[:-1]).returncode,2)

    def enthalpy_arguments(self, fuel_t='298.15', oxidizer_t='298.15'):
        values=[]
        for species,temperature in [('CH4',fuel_t),('O2',oxidizer_t)]:
            run=self.run_app('thermo',species,temperature)
            self.assertEqual(run.returncode,0,run.stderr)
            values.append(json.loads(run.stdout)['h_j_per_kg'])
        return ['nasa9-cea-v3.3.4','gas','10000000','3.4',*map(repr,values)]

    def test_explicit_enthalpy_equivalence_and_fixed_nozzle(self):
        refs=json.loads((ROOT/'tests/reference/cea/manifest.json').read_text(encoding='utf-8'))
        hp_ref=next(c for c in refs['cases'] if c['id']=='ch4_o2_hp')
        nozzle_ref=next(c for c in refs['cases'] if c['id']=='ch4_o2_rocket_frozen_chamber')
        for tf,to in [('298.15','298.15'),('450','900')]:
            args=self.enthalpy_arguments(tf,to)
            run=self.run_app('combustion','hp-h',*args)
            self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(run.stderr,'')
            report=json.loads(run.stdout)
            old=json.loads(self.run_app('combustion','hp','10000000','3.4',tf,to).stdout)
            self.assertEqual(report['chamber'],old['chamber'])
            self.assertEqual(report['diagnostics'],old['diagnostics'])
            self.assertEqual(report['boundary']['heat_transfer_j_per_kg'],0)
            self.assertNotIn('fuel_temperature_k',report['inputs'])
            if tf=='298.15':
                compare_report(report,hp_ref,'hp-h',expected_inputs=report['inputs'])
                points=[]
                for area,pa,at in [(10,0,0.01),(40,0,0.01),(10,0,0.02),(10,5000,0.01)]:
                    run=self.run_app('combustion','frozen-h',*args,str(area),str(pa),str(at))
                    self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(run.stderr,'')
                    point=json.loads(run.stdout);points.append(point)
                    compare_report(point,nozzle_ref,'frozen-h',area,expected_inputs=point['inputs'])
                base,_,double,ambient=points
                self.assertTrue(math.isclose(double['geometry']['thrust_n'],2*base['geometry']['thrust_n'],abs_tol=1e-7))
                self.assertEqual(ambient['geometry']['mass_flow_kg_per_s'],base['geometry']['mass_flow_kg_per_s'])
                self.assertTrue(math.isclose(base['geometry']['thrust_n']-ambient['geometry']['thrust_n'],
                                             5000*base['geometry']['exit_area_m2'],abs_tol=1e-7))

    def test_explicit_enthalpy_rejections_and_protocol(self):
        args=self.enthalpy_arguments()
        for index,value,code in [(0,'arbitrary-zero',4),(1,'liquid',4),(1,'unknown',4),
                                 (2,'99',4),(2,'nan',2),(3,'-1',4),(3,'20.1',4),
                                 (4,'1e308',4),(4,'-1e308',4),(4,'nan',2),
                                 (5,'-1e308',4),(5,'0x1p2',2)]:
            bad=list(args);bad[index]=value
            with self.subTest(index=index,value=value):
                run=self.run_app('combustion','hp-h',*bad)
                self.assertEqual(run.returncode,code,run.stderr);self.assertEqual(run.stdout,'')
                self.assertTrue(run.stderr.strip())
        for tail in [('10','1000000','0.01'),('10','0','0'),('0.5','0','0.01')]:
            run=self.run_app('combustion','frozen-h',*args,*tail)
            self.assertEqual(run.returncode,4);self.assertEqual(run.stdout,'')
        for bad in [args[:-1],args+['extra']]:
            self.assertEqual(self.run_app('combustion','hp-h',*bad).returncode,2)

    def test_explicit_enthalpy_validator_rejects_false_success(self):
        args=self.enthalpy_arguments()
        run=self.run_app('combustion','frozen-h',*args,'10','0','0.01')
        self.assertEqual(run.returncode,0,run.stderr)
        report=json.loads(run.stdout);expected=copy.deepcopy(report['inputs'])
        ref=next(c for c in json.loads((ROOT/'tests/reference/cea/manifest.json').read_text(encoding='utf-8'))['cases']
                 if c['id']=='ch4_o2_rocket_frozen_chamber')
        for defect in ['basis','phase','input-h','boundary-h','heat','bool-heat','temperature','thrust','flow','energy','model']:
            bad=copy.deepcopy(report)
            if defect=='basis': bad['inputs']['enthalpy_basis']='arbitrary'
            if defect=='phase': bad['inputs']['feed_phase']='liquid'
            if defect=='input-h': bad['inputs']['fuel_h_j_per_kg']+=1000
            if defect=='boundary-h': bad['boundary']['inlet_mixture_h_j_per_kg']+=1000
            if defect=='heat': bad['boundary']['heat_transfer_j_per_kg']=1
            if defect=='bool-heat': bad['boundary']['heat_transfer_j_per_kg']=False
            if defect=='temperature': bad['chamber']['temperature_k']+=1
            if defect=='thrust': bad['geometry']['thrust_n']+=10
            if defect=='flow': bad['geometry']['mass_flow_kg_per_s']*=2
            if defect=='energy': bad['nozzle']['exit']['gas']['h_j_per_kg']+=1000
            if defect=='model': bad['model']='prescribed_thermal_cycle_v1'
            with self.subTest(defect=defect),self.assertRaises(ValueError):
                compare_report(bad,ref,'frozen-h',10,expected_inputs=expected)

    def test_combustion_validator_rejects_false_success(self):
        result = self.run_app('combustion', 'frozen', '10000000', '3.4', '298.15', '298.15', '40', '0')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        reference = next(case for case in json.loads((ROOT / 'tests/reference/cea/manifest.json').read_text(encoding='utf-8'))['cases'] if case['id'] == 'ch4_o2_rocket_frozen_chamber')
        for defect in ('model', 'input', 'nonfinite', 'negative', 'energy', 'composition', 'freeze', 'ivac', 'residual'):
            broken = copy.deepcopy(report)
            if defect == 'model': broken['model'] = 'flight-engine'
            if defect == 'input': broken['inputs']['pressure_pa'] = 1e6
            if defect == 'nonfinite': broken['chamber']['temperature_k'] = float('nan')
            if defect == 'negative': broken['chamber']['mole_fractions']['H2'] = -0.1
            if defect == 'energy': broken['nozzle']['exit']['gas']['h_j_per_kg'] += 1000
            if defect == 'composition': broken['nozzle']['exit']['gas']['mole_fractions']['H2'] += 0.01
            if defect == 'freeze': broken['nozzle']['freeze_location'] = 'throat'
            if defect == 'ivac': broken['nozzle']['vacuum_effective_velocity_m_per_s'] = 3435.41 / 9.80665
            if defect == 'residual': broken['diagnostics']['element_relative_residual'][0] = 0.01
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                compare_report(broken, reference, 'frozen', 40)

    def test_cycle_accounting_and_unicode_path(self):
        result = self.run_app('cycle','prescribed',self.case(self.cycle))
        self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(result.stderr,'')
        report=json.loads(result.stdout)
        self.assertGreaterEqual(len(validate_cycle(report,self.cycle)),80)
        self.assertAlmostEqual(report['energy']['pump_power_w'],1137201.607646175,places=6)
        self.assertGreater(report['flows']['branch_mass_flow_kg_per_s'],0)
        self.assertNotEqual(report['energy']['chamber_required_heat_w'],0)
        self.assertIn('not an adiabatic',' '.join(report['limitations']))
        self.assertEqual(result.stdout,self.run_app('cycle','prescribed',self.case(self.cycle)).stdout)
        bom=b'\xef\xbb\xbf'+self.cycle.replace('\n','\r\n').encode('utf-8')
        self.assertEqual(self.run_app('cycle','prescribed',self.case(bom)).returncode,0)

    def test_cycle_schema_and_numeric_rejections(self):
        variants=[self.cycle+'unknown=1\n',self.cycle+'return_fraction=0\n',
                  self.cycle.replace('return_fraction=0\n',''),self.cycle.replace('prescribed_thermal_cycle_v1','flight_engine'),
                  self.cycle.replace('synthetic_benchmark','verified_engine'),self.cycle.replace('schema_version=1','schema_version=2'),
                  self.cycle.replace('main_area_ratio=10','main_area_ratio=10\x00hidden'),
                  '#'+('x'*600)+'\n'+self.cycle,'# comment\n'*130+self.cycle]
        for value in ('nan','inf','1e999','1e-999','0x1p2','1,4','10 # comment'):
            variants.append(self.cycle.replace('main_area_ratio=10','main_area_ratio='+value))
        for text in variants:
            with self.subTest(text=text[-100:]):
                result=self.run_app('cycle','prescribed',self.case(text))
                self.assertEqual(result.returncode,3,result.stderr); self.assertEqual(result.stdout,'')
        for args in ((),('prescribed',),('unknown','case.ini')):
            self.assertEqual(self.run_app('cycle',*args).returncode,2)

    def test_cycle_domain_and_zero_branch(self):
        for old,new in [('return_fraction=0','return_fraction=0.5'),
                        ('fuel_pump_outlet_pressure_pa=7000000','fuel_pump_outlet_pressure_pa=4000000'),
                        ('maximum_branch_fraction=0.25','maximum_branch_fraction=0.000001'),
                        ('ambient_pressure_pa=0','ambient_pressure_pa=1000000'),
                        ('turbine_efficiency=0.7','turbine_efficiency=1.01')]:
            with self.subTest(new=new):
                result=self.run_app('cycle','prescribed',self.case(self.cycle.replace(old,new)))
                self.assertEqual(result.returncode,4,result.stderr); self.assertEqual(result.stdout,'')
        zero=self.cycle.replace('pump_inlet_pressure_pa=200000','pump_inlet_pressure_pa=7000000').replace('auxiliary_power_w=10000','auxiliary_power_w=0')
        result=self.run_app('cycle','prescribed',self.case(zero)); self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout); self.assertIsNone(report['branch_nozzle'])
        self.assertEqual(report['flows']['branch_mass_flow_kg_per_s'],0)
        self.assertGreater(len(validate_cycle(report,zero)),50)

    def test_cycle_study_cost_and_finite_step_response(self):
        result=self.run_app('study','prescribed-cycle',self.case(self.cycle),'main_area_ratio','10,20,40')
        self.assertEqual(result.returncode,0,result.stderr);report=json.loads(result.stdout)
        checked=validate_cycle_study(report,self.cycle,'main_area_ratio',[10,20,40])
        self.assertEqual(checked['counts']['ok'],3)
        self.assertEqual(report['points'][0]['metrics']['thrust_change_n'],0)
        for key in report['points'][2]['metrics']:
            candidate=copy.deepcopy(report)
            candidate['points'][2]['metrics'][key]=False if key=='elasticity_defined' else candidate['points'][2]['metrics'][key]+1
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_cycle_study(candidate,self.cycle,'main_area_ratio',[10,20,40])

    def test_cycle_study_axes_and_domain_exclusions(self):
        for field,values in [('branch_axial_projection',[0,1,2]),('ambient_pressure_pa',[0,101325]),
            ('turbine_efficiency',[0.693,0.7,0.707]),('chamber_temperature_k',[3267,3300,3333]),
            ('overall_oxidizer_fuel_ratio',[3.366,3.4,3.434]),('fuel_pump_efficiency',[0.693,0.7,0.707]),
            ('oxidizer_pump_efficiency',[0.7425,0.75,0.7575])]:
            result=self.run_app('study','prescribed-cycle',self.case(self.cycle),field,','.join(map(str,values)))
            self.assertEqual(result.returncode,0,result.stderr)
            validate_cycle_study(json.loads(result.stdout),self.cycle,field,values)
        result=self.run_app('study','prescribed-cycle',self.case(self.cycle),'ambient_pressure_pa','0,1000')
        report=json.loads(result.stdout);report['points'][1]={'value':1000,'status':'out_of_domain','error':'forged'}
        with self.assertRaises(ValueError): validate_cycle_study(report,self.cycle,'ambient_pressure_pa',[0,1000])

    def test_cycle_study_invalid_cli_and_baseline(self):
        for args in [('bad','1'),('main_area_ratio','nan'),('main_area_ratio','-1'),('main_area_ratio','1,')]:
            result=self.run_app('study','prescribed-cycle',self.case(self.cycle),*args)
            self.assertEqual(result.returncode,2);self.assertFalse(result.stdout)
        result=self.run_app('study','prescribed-cycle',self.case(self.cycle.replace('return_fraction=0','return_fraction=0.1')),'main_area_ratio','10,20')
        self.assertEqual(result.returncode,4);self.assertFalse(result.stdout)

    def test_cycle_validator_detects_wrong_accounting(self):
        result=self.run_app('cycle','prescribed',self.case(self.cycle)); self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        for defect in ('schema','provenance','nonfinite','pump','shaft','branch','thrust','energy','composition','zero','input','negative','entropy','state','residual','heat'):
            broken=copy.deepcopy(report)
            if defect=='schema': broken.pop('energy')
            if defect=='provenance': broken['case']['kind']='verified_engine'
            if defect=='nonfinite': broken['performance']['total_thrust_n']=float('nan')
            if defect=='pump': broken['pumps']['fuel']['shaft_power_w']*=2
            if defect=='shaft': broken['energy']['turbine_power_w']*=2
            if defect=='branch': broken['flows']['branch_mass_flow_kg_per_s']*=2
            if defect=='thrust': broken['performance']['engine_specific_impulse_s']*=9.80665
            if defect=='energy': broken['branch_nozzle']['exit']['gas']['h_j_per_kg']+=1000
            if defect=='composition': broken['turbine']['outlet']['mole_fractions']['H2']+=0.01
            if defect=='zero': broken['branch_nozzle']=None
            if defect=='input': broken['inputs']['turbine_efficiency']=True
            if defect=='negative': broken['performance']['branch_thrust_n']*=-1
            if defect=='entropy': broken['turbine']['entropy_generation_j_per_kg_k']=-1
            if defect=='state': broken['branch_nozzle']['chamber']['temperature_k']+=1
            if defect=='residual': broken['diagnostics']['energy_relative_residual']=0.01
            if defect=='heat': broken['energy']['chamber_required_heat_w']=0
            with self.subTest(defect=defect),self.assertRaises(ValueError): validate_cycle(broken,self.cycle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    options, remaining = parser.parse_known_args()
    BINARY = options.binary.resolve(strict=True)
    unittest.main(argv=[__file__, *remaining], verbosity=2)
