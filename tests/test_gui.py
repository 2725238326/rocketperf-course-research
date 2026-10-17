"""GUI bridge contract: same C numbers as the tested CLI, same rejections, strict requests.

    python tools/gui_build.py --bridge-only
    python tests/test_gui.py [--bridge build/gui/gui_bridge_stdio.exe] [--cli build/release/rocketperf.exe]
"""
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "build/gui/gui_bridge_stdio.exe"
CLI = ROOT / "build/release/rocketperf.exe"
CH4 = ["coolprop710-cea334-liquid-molar-v1", "heos710-cea334-ideal-zero-298.15-v1", "liquid"]
RP1 = ["cea-v3.3.4-rp1-o2l-assigned-v1", "liquid", "RP-1", "O2(L)", "10000000"]
CASES = ["zq3_y1_stage1", "zq3_y1_stage2", "cz10b_first_stage1", "cz10b_first_stage2", "cz10b_first_stage2_orsc"]
REL = 2e-12  # both frontends preserve double precision with %.17g


def bridge(*requests):
    lines = "\n".join(json.dumps(r) for r in requests) + "\n"
    done = subprocess.run([str(BRIDGE)], input=lines, capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=120)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return [json.loads(line) for line in done.stdout.splitlines()]


def cli(*args):
    done = subprocess.run([str(CLI), *map(str, args)], capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=120)
    return done.returncode, json.loads(done.stdout) if done.returncode == 0 else None, done.stderr


class GuiBridgeTests(unittest.TestCase):
    def close(self, a, b, what):
        self.assertAlmostEqual(a, b, delta=REL * max(1.0, abs(b)), msg=what)

    def test_ch4_nozzle_matches_cli(self):
        for of, ar, pa in [(2.6, 40, 0), (3.2, 10, 50000), (1.0, 4, 0)]:
            with self.subTest(of=of, ar=ar, pa=pa):
                env, = bridge({"cmd": "nozzle", "args": {"fuel": "ch4", "of": of, "ar": ar, "pa": pa, "at": 0.01}})
                self.assertTrue(env["ok"], env)
                code, ref, err = cli("combustion", "frozen-liquid-state", *CH4, 120, 1e7, 100, 1e7, 1e7, of, ar, pa, 0.01)
                self.assertEqual(code, 0, err)
                r = env["result"]
                self.close(r["chamber"]["gas"]["t"], ref["chamber"]["temperature_k"], "Tc")
                self.close(r["chamber"]["graphite_activity"], ref["diagnostics"]["graphite_activity"], "a_C")
                self.close(r["ideal"]["cstar"], ref["nozzle"]["cstar_m_per_s"], "c*")
                self.close(r["attached"]["isp"], ref["geometry"]["specific_impulse_s"], "Isp")
                self.close(r["attached"]["thrust"], ref["geometry"]["thrust_n"], "F")
                self.close(r["attached"]["mdot"], ref["geometry"]["mass_flow_kg_per_s"], "mdot")
                self.close(r["attached"]["cf"], ref["nozzle"]["thrust_coefficient"], "CF")
                for i, x in enumerate(ref["chamber"]["mole_fractions"].values()):
                    self.close(r["chamber"]["gas"]["x"][i], x, f"x{i}")

    def test_overexpanded_regime_matches_cli_and_rejects_attached(self):
        env, = bridge({"cmd": "nozzle", "args": {"fuel": "ch4", "of": 2.6, "ar": 40, "pa": 101325, "at": 0.01}})
        code, ref, err = cli("combustion", "regime-liquid-state", *CH4, 120, 1e7, 100, 1e7, 1e7, 2.6, 40, 101325, 0.01)
        self.assertEqual(code, 0, err)
        r, g = env["result"], ref["regime"]
        self.assertEqual(r["regime"]["name"], g["class"])
        self.close(r["regime"]["matched_ar"], g["matched_area_ratio"]["area_ratio"], "matched")
        self.close(r["regime"]["separation_ar"], g["separation_area_ratio"]["area_ratio"], "separation")
        self.close(r["ideal"]["isp"], g["ideal_attached"]["specific_impulse_s"], "ideal Isp")
        self.assertFalse(r["attached"]["ok"])
        self.assertEqual(r["attached"]["status"], "out_of_domain")
        code, _, err = cli("combustion", "frozen-liquid-state", *CH4, 120, 1e7, 100, 1e7, 1e7, 2.6, 40, 101325, 0.01)
        self.assertNotEqual(code, 0)
        self.assertIn(r["attached"]["message"], err)

    def test_rp1_and_comparison_match_cli(self):
        env, = bridge({"cmd": "nozzle", "args": {"fuel": "rp1", "of": 3.0, "ar": 10, "pa": 0, "at": 0.01}})
        code, ref, err = cli("combustion", "frozen-rp1", *RP1, 3.0, 298.15, 90.170, 10, 0, 0.01)
        self.assertEqual(code, 0, err)
        self.close(env["result"]["attached"]["isp"], ref["geometry"]["specific_impulse_s"], "RP-1 Isp")
        env, = bridge({"cmd": "compare", "args": {"ch4_of": 2.6, "rp1_of": 2.6, "ar": 10, "pa": 0}})
        code, ref, err = cli("study", "propellants", 2.6, 2.6, 10, 0)
        self.assertEqual(code, 0, err)
        d, e = env["result"]["delta"], ref["methane_minus_kerosene"]
        for a, b in [("thrust", "thrust_n"), ("isp", "isp_s"), ("mdot", "mass_flow_kg_per_s"), ("cstar", "cstar_m_per_s")]:
            self.close(d[a], e[b], a)

    def test_cycles_match_cli(self):
        envs = bridge(*({"cmd": "cycle", "args": {"case": f"cases/vehicles/{c}.ini"}} for c in CASES))
        for case, env in zip(CASES, envs):
            with self.subTest(case=case):
                self.assertTrue(env["ok"], env)
                code, ref, err = cli("cycle", "adiabatic", f"cases/vehicles/{case}.ini")
                self.assertEqual(code, 0, err)
                b, rb = env["result"]["balance"], ref["balance"]
                self.close(b["isp"], rb["engine_specific_impulse_s"], "Isp")
                self.close(b["total_thrust"], rb["total_thrust_n"], "F")
                self.close(b["branch_flow"], rb["branch_mass_flow_kg_per_s"], "branch")
                self.close(env["result"]["turbine"]["out_p"], ref["turbine"]["outlet"]["pressure_pa"], "turbine out")

    def test_override_equals_edited_case_file(self):
        text = (ROOT / "cases/vehicles/zq3_y1_stage1.ini").read_text(encoding="utf-8").replace("preburner_oxidizer_fuel_ratio=1.0", "preburner_oxidizer_fuel_ratio=1.2")
        tmp = ROOT / "build/gui/test_override.ini"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        env, = bridge({"cmd": "cycle", "args": {"case": "cases/vehicles/zq3_y1_stage1.ini", "preburner_oxidizer_fuel_ratio": 1.2}})
        code, ref, err = cli("cycle", "adiabatic", tmp)
        tmp.unlink()
        self.assertEqual(code, 0, err)
        self.close(env["result"]["balance"]["isp"], ref["balance"]["engine_specific_impulse_s"], "edited Isp")

    def test_exported_cycle_ini_reproduces_overrides(self):
        env, = bridge({"cmd": "cycle", "args": {
            "case": "cases/vehicles/cz10b_first_stage1.ini",
            "preburner_oxidizer_fuel_ratio": 31.0,
            "chamber_pressure_pa": 9.5e6,
        }})
        self.assertTrue(env["ok"], env)
        exported = env["result"].get("ini")
        self.assertIsInstance(exported, str)
        self.assertIn("preburner_oxidizer_fuel_ratio=31", exported)
        with tempfile.NamedTemporaryFile("w", suffix=".ini", dir=ROOT / "build/gui", delete=False, encoding="utf-8") as handle:
            path = Path(handle.name)
            handle.write(exported)
        try:
            code, ref, err = cli("cycle", "adiabatic", path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(code, 0, err)
        b = env["result"]["balance"]
        rb = ref["balance"]
        self.close(b["isp"], rb["engine_specific_impulse_s"], "exported Isp")
        self.close(b["total_thrust"], rb["total_thrust_n"], "exported thrust")
        self.close(b["branch_flow"], rb["branch_mass_flow_kg_per_s"], "exported branch flow")

    def test_rejections_keep_c_status(self):
        carbon, rp1_pc, sweep = bridge({"cmd": "chamber", "args": {"fuel": "ch4", "of": 0.8}},
                                       {"cmd": "chamber", "args": {"fuel": "rp1", "pc": 5e6, "of": 2.6}},
                                       {"cmd": "chamber_sweep", "args": {"fuel": "ch4", "of_min": 0.5, "of_max": 4.0, "n": 36}})
        self.assertEqual((carbon["ok"], carbon["status"], carbon["stage"]), (False, "out_of_domain", "chamber"))
        self.assertIn("graphite activity", carbon["message"])
        self.assertEqual(rp1_pc["status"], "out_of_domain")
        st = sweep["result"]["status"]
        self.assertEqual(st[0], "out_of_domain")
        self.assertEqual(st[-1], "ok")
        self.assertIsNone(sweep["result"]["t"][0])

    def test_sweep_points_equal_single_solves(self):
        sweep, single = bridge({"cmd": "nozzle_sweep", "args": {"fuel": "ch4", "of": 2.6, "ars": [10, 40], "pas": [0, 101325]}},
                               {"cmd": "nozzle", "args": {"fuel": "ch4", "of": 2.6, "ar": 10, "pa": 101325}})
        r = sweep["result"]
        self.close(r["isp"][1][0], single["result"]["attached"]["isp"], "sweep vs single")
        self.assertEqual(r["regime"][1], [0, 2])
        self.close(r["matched_ar"][1], single["result"]["regime"]["matched_ar"], "matched")

    def test_request_hygiene(self):
        bad = bridge({"cmd": "chamber", "args": {"pcc": 1}}, {"cmd": "nope", "args": {}},
                     {"cmd": "cycle", "args": {"case": "../secret.ini"}},
                     {"cmd": "cycle", "args": {"case": "cases/vehicles/zq3_y1_stage1.ini", "fuel_pump_inlet_pressure_pa": 2e6}},
                     {"cmd": "chamber", "args": {"of": "2.6"}})
        self.assertTrue(all(not e["ok"] and e["status"] == "invalid_argument" for e in bad), bad)
        raw = subprocess.run([str(BRIDGE)], input='{"cmd":"chamber","args":{"of":1e999}}\n{"cmd":"chamber","args":{"of":2.6,"of":3}}\nnot json\n',
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        for line in raw.stdout.splitlines():
            self.assertEqual(json.loads(line)["status"], "parse_error")
        strict_lines = [
            '{"cmd":"chamber","args":{"of":1.e1}}',
            '{"cmd":"chamber","args":{"of":01}}',
            '{"cmd":"chamber","args":{"of":1.}}',
            '{"cmd":"chamber","args":{"of":1e}}',
            '{"cmd":"chamber","args":{"of":2.6},"args":{}}',
            '{"cmd":"info",}',
            '{"cmd":"info","cmd":"info"}',
            '{"cmd":"chamber","args":{"of":1e+}}',
            '{"cmd":"chamber","args":{"of":-01}}',
            r'{"cmd":"chamber","args":{"fuel":"\u1',
        ]
        malformed_run = subprocess.run([str(BRIDGE)], input="\n".join(strict_lines) + "\n",
                                       capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        malformed = [json.loads(line) for line in malformed_run.stdout.splitlines()]
        self.assertEqual(malformed_run.returncode, 0, malformed_run.stderr)
        self.assertEqual(len(malformed), len(strict_lines))
        self.assertTrue(all(e["status"] == "parse_error" for e in malformed), malformed)
        fractional, = bridge({"cmd": "chamber_sweep", "args": {
            "fuel": "ch4", "of_min": 0.5, "of_max": 4.0, "n": 12.5,
        }})
        self.assertEqual(fractional["status"], "invalid_argument")
        fractional_compare, = bridge({"cmd": "compare", "args": {"n": 19.5}})
        self.assertEqual(fractional_compare["status"], "invalid_argument")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge", type=Path)
    parser.add_argument("--cli", type=Path)
    args, rest = parser.parse_known_args()
    BRIDGE = (args.bridge or BRIDGE).resolve()
    CLI = (args.cli or CLI).resolve()
    unittest.main(argv=[sys.argv[0], *rest], verbosity=2)
