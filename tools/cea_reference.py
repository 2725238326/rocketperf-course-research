"""Capture/replay fixed CEA cards; never use the reference solver in the C core."""
import argparse
import math
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from projectlib import ROOT, atomic_json, atomic_text, digest, now, read_json, subprocess_env

COMMIT = '4c5c612efa2002a94e3a5a1f33b1674d55c65340'
THERMO_SHA = 'fa7746572952d74e249e818a82a35c113829742fb421a308e167185528884363'
CARDS = ('ch4_o2_tp', 'ch4_o2_hp', 'ch4_o2_rocket_equilibrium', 'ch4_o2_rocket_frozen_chamber')
SPECIES = ('H2', 'O2', 'H2O', 'CO', 'CO2', 'CH4', 'H', 'O', 'OH')
REFERENCE = ROOT / 'tests/reference/cea'
ROWS = {'P, bar': 'pressure_bar', 'T, K': 'temperature_k', 'H, kJ/kg': 'enthalpy_kj_kg',
        'S, kJ/kg-K': 'entropy_kj_kg_k', 'M, (1/n)': 'molar_mass_kg_kmol',
        'Mach': 'mach', 'Ae/At': 'area_ratio', 'C*, m/s': 'cstar_m_s',
        'Cf': 'cf', 'Ivac, m/s': 'ivac_m_s', 'Isp, m/s': 'isp_velocity_m_s'}


def parse_output(data, rocket=False, frozen=False):
    text = data.decode('ascii', errors='strict')
    if '\x00' in text or 'ERROR' in text or 'WARNING' in text:
        raise ValueError('CEA output contains invalid bytes or diagnostics')
    rows = {}; fractions = {}; in_species = False
    for line in text.splitlines():
        stripped = line.strip()
        for prefix, key in ROWS.items():
            if stripped.startswith(prefix + ' '):
                values = [float(x) for x in stripped[len(prefix):].split()]
                if not values or any(not math.isfinite(x) for x in values):
                    raise ValueError('Invalid CEA numeric row')
                if key in rows:
                    raise ValueError('Repeated numeric row or multiple result tables')
                rows[key] = values
        if stripped == 'MOLE FRACTIONS':
            in_species = True
        elif stripped.startswith('PRODUCTS WHICH'):
            in_species = False
        elif in_species and stripped:
            tokens = stripped.split()
            if tokens[0] not in SPECIES:
                raise ValueError('Unexpected species in restricted CEA result')
            fractions[tokens[0]] = [float(x) for x in tokens[1:]]
    columns = 4 if rocket else 1
    for key in ('pressure_bar', 'temperature_k', 'enthalpy_kj_kg', 'entropy_kj_kg_k', 'molar_mass_kg_kmol'):
        if len(rows.get(key, [])) != columns:
            raise ValueError('CEA thermodynamic table is incomplete')
    if rocket:
        for key in ('area_ratio', 'cstar_m_s', 'cf', 'ivac_m_s', 'isp_velocity_m_s'):
            if len(rows.get(key, [])) != 3:
                raise ValueError('CEA rocket performance table is incomplete')
        if ('FROZEN' if frozen else 'EQUILIBRIUM') not in text:
            raise ValueError('CEA chemistry mode differs from input contract')
        if abs(rows['area_ratio'][1] - 10) > 0.001 or abs(rows['area_ratio'][2] - 40) > 0.001:
            raise ValueError('CEA area ratios differ from requested grid')
    for values in fractions.values():
        if len(values) != (1 if frozen else columns) or any(not math.isfinite(x) or x < 0 for x in values):
            raise ValueError('Invalid CEA mole-fraction table')
    if not fractions or set(SPECIES) - set(fractions) - {'CH4'}:
        raise ValueError('Missing non-trace species')
    for index in range(1 if frozen else columns):
        if abs(sum(values[index] for values in fractions.values()) - 1) > 2e-5:
            raise ValueError('Printed mole fractions do not sum to one')
    return {'rows': rows, 'mole_fractions': fractions, 'output_trace_threshold': 1e-8,
            'omitted_species': sorted(set(SPECIES) - set(fractions)),
            'thermo_columns': ['chamber', 'throat', 'exit_A10', 'exit_A40'] if rocket else ['state'],
            'performance_columns': ['throat', 'exit_A10', 'exit_A40'] if rocket else []}


def check_reference():
    manifest = read_json(REFERENCE / 'manifest.json')
    if manifest['commit'] != COMMIT or manifest['thermo_source']['sha256'].lower() != THERMO_SHA:
        raise ValueError('Reference version/database differs')
    for case in manifest['cases']:
        for field in ('input', 'output'):
            path = ROOT / case[field]
            if digest(path) != case[field + '_sha256']:
                raise ValueError('Reference bytes changed: ' + case['id'])
        summary = parse_output((ROOT / case['output']).read_bytes(), 'rocket' in case['id'], 'frozen' in case['id'])
        if summary != case['summary']:
            raise ValueError('Reference parsed summary changed')
    if len(manifest['cases']) != 4:
        raise ValueError('Expected all four fixed CEA cases')
    if {case['id'] for case in manifest['cases']} != set(CARDS):
        raise ValueError('Reference case identities differ')
    return manifest


def run_reference(executable, database, record=False):
    folder = ROOT / 'build/reference-runs' / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    report = {'status': 'RUNNING', 'started_at': now(), 'cases': []}
    atomic_json(folder / 'run-manifest.json', report)
    try:
        report['executable_sha256'] = digest(executable)
        if digest(ROOT / '调研/原始来源/20261003_cea_v3.3.4/thermo.inp') != THERMO_SHA:
            raise ValueError('Archived source database differs')
        source = ROOT / 'build/reference/cea-v3.3.4'
        revision = subprocess.run(['git', '-C', str(source), 'rev-parse', 'HEAD'], capture_output=True,
                                  text=True, check=True, timeout=15).stdout.strip()
        if revision != COMMIT or digest(source / 'data/thermo.inp') != THERMO_SHA:
            raise ValueError('Built CEA source commit/database differs')
        report['source_commit'] = revision
        report['source_thermo_sha256'] = digest(source / 'data/thermo.inp')
        report['source_transport_sha256'] = digest(source / 'data/trans.inp')
        for name in ('thermo.lib', 'trans.lib'):
            shutil.copy2(database / name, folder / name)
        expected = None if record else check_reference()
        if expected is not None and any(digest(folder / n) != expected['compiled_database_hashes'][n]
                                        for n in ('thermo.lib', 'trans.lib')):
            raise ValueError('Compiled databases differ from recorded reference')
        for name in CARDS:
            shutil.copy2(REFERENCE / (name + '.inp'), folder / (name + '.inp'))
            result = subprocess.run([str(executable), '-v', name], cwd=folder, capture_output=True,
                                    encoding='utf-8', errors='replace', timeout=30, env=subprocess_env())
            atomic_text(folder / (name + '.log'), result.stdout + result.stderr)
            if result.returncode or result.stderr or 'CEA Version: 3.3.4' not in result.stdout:
                raise ValueError('CEA execution failed or version differs: ' + name)
            if 'WARNING' in result.stdout or 'ERROR' in result.stdout:
                raise ValueError('CEA diagnostic requires review: ' + name)
            output = folder / (name + '.out')
            summary = parse_output(output.read_bytes(), 'rocket' in name, 'frozen' in name)
            entry = {'id': name, 'input': 'tests/reference/cea/' + name + '.inp',
                     'input_sha256': digest(folder / (name + '.inp')),
                     'output': 'tests/reference/cea/raw/trace1e8/' + name + '.out',
                     'output_sha256': digest(output), 'summary': summary}
            report['cases'].append(entry)
            if expected is not None:
                other = next(x for x in expected['cases'] if x['id'] == name)
                if summary != other['summary']:
                    raise ValueError('Printed numeric reference differs: ' + name)
        report['status'] = 'PASS'
        if record:
            destination = REFERENCE / 'raw/trace1e8'
            if destination.exists():
                raise ValueError('Reference already recorded; use replay, not overwrite')
            destination.mkdir()
            for entry in report['cases']:
                shutil.copy2(folder / (entry['id'] + '.out'), ROOT / entry['output'])
                shutil.copy2(folder / (entry['id'] + '.log'), destination / (entry['id'] + '.log'))
            atomic_json(REFERENCE / 'manifest.json', {
                'schema_version': 2, 'tool': 'NASA CEA', 'version': '3.3.4', 'commit': COMMIT,
                'thermo_source': {'path': '调研/原始来源/20261003_cea_v3.3.4/thermo.inp', 'sha256': THERMO_SHA},
                'platform': sys.platform, 'executable_sha256': report['executable_sha256'],
                'source_transport_sha256': report['source_transport_sha256'],
                'compiled_database_hashes': {n: digest(folder / n) for n in ('thermo.lib', 'trans.lib')},
                'cases': report['cases'], 'scope': 'Restricted nine-species gas-feed method benchmark; not flight engine performance.',
                'known_output_defects': ['Initial trace=1e-12 TP/HP empty trace list contains invalid bytes; raw initial outputs retained.',
                                         'Reactant ENERGY KJ/MOL label prints CH4 -74600; do not use this column as kJ/mol input.']})
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        report['finished_at'] = now()
        atomic_json(folder / 'run-manifest.json', report)
    print('CEA reference PASS: four fixed cards; ' + str(folder))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--executable', type=Path, default=ROOT / 'build/reference/cea-build-v3.3.4/source/cea.exe')
    parser.add_argument('--database-dir', type=Path, default=ROOT / 'build/reference/cea-build-v3.3.4')
    args = parser.parse_args()
    if args.check:
        check_reference(); print('CEA archived inputs/outputs: four cases checked')
    else:
        run_reference(args.executable.resolve(), args.database_dir.resolve(), args.record)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print('cea-reference: ' + str(error), file=sys.stderr); sys.exit(1)
