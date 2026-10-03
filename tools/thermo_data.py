"""Reproduce selected NASA9 data from immutable upstream snapshots."""
import argparse
import csv
import hashlib
import io
import json
import math
import sys

from projectlib import ROOT, atomic_json, atomic_text, digest, read_json

DATASET_ID = 'cea-v3.3.4-neutral-cho-n-v1'
COMMIT = '4c5c612efa2002a94e3a5a1f33b1674d55c65340'
CEA_GAS_CONSTANT = 8314.5100
RAW = '调研/原始来源/20261003_cea_v3.3.4'
SPECIES = ('H2', 'O2', 'N2', 'H2O', 'CO', 'CO2', 'CH4', 'H', 'O', 'OH')
SOURCE_HASHES = {
    'thermo.inp': 'fa7746572952d74e249e818a82a35c113829742fb421a308e167185528884363',
    'LICENSE.txt': 'a60026be9384468d074c19425e552f1bb4a6f507f805e55a96fad586716168ed',
    'NOTICE.txt': '03b64364559d540d97615c31675a69e8eb1965e30de8859a2f8c5c9a38ecb55e',
}


def number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not math.isfinite(value):
        raise ValueError('Non-finite NASA9 field')
    return value


def parse_selected(text):
    lines = text.splitlines()
    records = []
    for name in SPECIES:
        indices = [index for index, line in enumerate(lines) if line[:18].strip() == name]
        if len(indices) != 1:
            raise ValueError(f'Expected one exact record for {name}, found {len(indices)}')
        index = indices[0]
        metadata = lines[index + 1]
        count = int(metadata[:2])
        if count not in (2, 3) or metadata[50:52].strip() != '0':
            raise ValueError(f'{name}: only neutral gas multi-range records are supported')
        mass = number(metadata[52:65])
        formation = number(metadata[65:80])
        if mass <= 0:
            raise ValueError(f'{name}: invalid molar mass')
        elements = {}
        for start in range(10, 50, 8):
            symbol = metadata[start:start + 2].strip()
            amount = number(metadata[start + 2:start + 8])
            if symbol:
                if symbol not in {'C', 'H', 'O', 'N'} or amount <= 0:
                    raise ValueError(f'{name}: unsupported elemental composition')
                elements[symbol] = amount
            elif amount != 0:
                raise ValueError('Element amount without symbol')
        ranges = []
        for interval in range(count):
            cursor = index + 2 + 3 * interval
            bounds = lines[cursor]
            lower, upper = number(bounds[:11]), number(bounds[11:22])
            exponents = [number(bounds[start:start + 5]) for start in range(23, 58, 5)]
            if int(bounds[22:23]) != 7 or exponents != [-2, -1, 0, 1, 2, 3, 4]:
                raise ValueError(f'{name}: unexpected polynomial powers')
            first, second = lines[cursor + 1], lines[cursor + 2]
            coefficients = [number(first[start:start + 16]) for start in range(0, 80, 16)]
            coefficients += [number(second[:16]), number(second[16:32]),
                             number(second[48:64]), number(second[64:80])]
            if second[32:48].strip() and number(second[32:48]) != 0:
                raise ValueError(f'{name}: unsupported eighth heat-capacity term')
            if not 0 < lower < upper or (ranges and ranges[-1]['t_max_k'] != lower):
                raise ValueError(f'{name}: invalid range ordering')
            ranges.append({'t_min_k': lower, 't_max_k': upper, 'coefficients': coefficients})
        records.append({'id': name, 'molar_mass_kg_per_kmol': mass,
                        'elements': elements, 'formation_enthalpy_298_j_mol': formation,
                        'source_line': index + 1, 'source_note': lines[index][18:].strip(),
                        'ranges': ranges})
    return records


def formatted(value):
    return format(value, '.17g')


def generated_files(root=ROOT):
    for name, expected in SOURCE_HASHES.items():
        if digest(root / RAW / name) != expected:
            raise ValueError(f'Immutable NASA source hash differs: {name}')
    records = parse_selected((root / RAW / 'thermo.inp').read_text(encoding='ascii'))
    table = io.StringIO(newline='')
    writer = csv.writer(table, delimiter='\t', lineterminator='\n')
    writer.writerow(['id', 'molar_mass_kg_per_kmol', 't_min_k', 't_max_k',
                     *[f'a{index}' for index in range(9)], 'h_offset_j_per_kg', 's_offset_j_per_kg_k'])
    header = ['#ifndef ROCKETPERF_DATABASE_GENERATED_H', '#define ROCKETPERF_DATABASE_GENERATED_H',
              f'#define RP_THERMO_DATASET_ID "{DATASET_ID}"', '']
    for record in records:
        header.append(f'static const RpNasa9Range rp_ranges_{record["id"]}[] = {{')
        for interval in record['ranges']:
            fields = [record['molar_mass_kg_per_kmol'], interval['t_min_k'], interval['t_max_k'],
                      *interval['coefficients'], 0, 0]
            writer.writerow([record['id'], *map(formatted, fields)])
            coefficients = ', '.join(map(formatted, interval['coefficients']))
            header.append('    {' + f'{formatted(interval["t_min_k"])}, {formatted(interval["t_max_k"])}, '
                          + '{' + coefficients + '}, 0.0, 0.0},')
        header += ['};', '']
    header.append('static const RpNasa9Species rp_database_species[] = {')
    for record in records:
        header.append('    {' + f'"{record["id"]}", {formatted(record["molar_mass_kg_per_kmol"])}, '
                      + f'{len(record["ranges"])}U, rp_ranges_{record["id"]}' + '},')
    header += ['};', '', '#endif', '']
    outputs = {'data/thermo/cea_nasa9.tsv': table.getvalue(),
               'src/thermo/database_generated.h': '\n'.join(header)}
    manifest = {
        'schema_version': 1, 'dataset_id': DATASET_ID, 'role': 'real_species_thermodynamic_fits',
        'source': {'repository': 'https://github.com/nasa/cea', 'release': 'v3.3.4', 'commit': COMMIT,
                   'files': [{'path': f'{RAW}/{name}', 'sha256': sha} for name, sha in SOURCE_HASHES.items()]},
        'license_review': {'distribution_license': 'Apache-2.0', 'basis': f'{RAW}/NOTICE.txt',
                           'scope': 'NOTICE explicitly lists data/thermo.inp and NASA TP-2002-211556; '
                                    'retain LICENSE, NOTICE, species citations and modification record.'},
        'modification_record': 'Selected 10 neutral gas records; converted fixed-width input to TSV/C constants. '
                               'Coefficients, molar masses and temperature bounds unchanged; offsets are zero.',
        'reference_pressure_pa': 100000, 'reference_temperature_k': 298.15,
        'gas_constant_j_kmol_k': CEA_GAS_CONSTANT,
        'enthalpy_basis': 'Formation enthalpy included in b1; do not add the header Hf a second time.',
        'mass_basis': 'CEA source molar masses, not modern Cantera atomic-weight defaults',
        'boundary_rule': '[Tmin,Tmax), final Tmax included; no extrapolation',
        'generated': [{'path': path, 'sha256': hashlib.sha256(text.encode()).hexdigest()}
                      for path, text in outputs.items()],
        'species': records,
        'limitations': ['Neutral ideal-gas single-species reference properties only.',
                        'No equilibrium, liquid properties, ions, condensed carbon or engine calibration.',
                        'H2O/CH4 end at 6000 K; do not extend them to other species upper limits.'],
    }
    outputs['data/thermo/manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    return outputs


def check_generated(root=ROOT):
    outputs = generated_files(root)
    for path, expected in outputs.items():
        if not (root / path).is_file() or (root / path).read_text(encoding='utf-8') != expected:
            raise ValueError(f'Generated NASA9 data drift: {path}')
    reference = read_json(root / 'tests/reference/nasa9_cantera.json')
    if reference['dataset_manifest_sha256'] != digest(root / 'data/thermo/manifest.json'):
        raise ValueError('NASA9 reference uses a different dataset')
    if reference['reference_header_sha256'] != digest(root / 'tests/reference/nasa9_cantera.h'):
        raise ValueError('NASA9 reference header changed')
    if reference['air_source_sha256'] != digest(root / '调研/原始来源/20261003_cantera_v3.1.0_airNASA9.yaml'):
        raise ValueError('NASA9 separate air source changed')
    if reference['version'] != '3.1.0' or reference['gas_constant_j_kmol_k'] != CEA_GAS_CONSTANT:
        raise ValueError('NASA9 reference implementation or gas constant differs')
    return len(outputs)


def make_reference(root=ROOT):
    sys.path.insert(0, str(root / 'build/reference_tooling'))
    import cantera as ct
    if ct.__version__ != '3.1.0':
        raise ValueError('Expected pinned Cantera 3.1.0')
    manifest = read_json(root / 'data/thermo/manifest.json')
    states = []
    for record in manifest['species']:
        coefficients = [len(record['ranges'])]
        temperatures = {298.15, 300.0, 500.0, 1500.0, 3000.0, 5000.0}
        for interval in record['ranges']:
            coefficients += [interval['t_min_k'], interval['t_max_k'], *interval['coefficients']]
            temperatures.update([interval['t_min_k'], interval['t_max_k']])
            if interval['t_min_k'] > record['ranges'][0]['t_min_k']:
                temperatures.update([interval['t_min_k'] - 1e-6, interval['t_min_k'] + 1e-6])
        model = ct.Nasa9PolyMultiTempRegion(record['ranges'][0]['t_min_k'],
                 record['ranges'][-1]['t_max_k'], manifest['reference_pressure_pa'], coefficients)
        mass = record['molar_mass_kg_per_kmol']
        scale = CEA_GAS_CONSTANT / ct.gas_constant
        for temperature in sorted(temperatures):
            states.append({'id': record['id'], 'temperature_k': temperature,
                           'cp_j_per_kg_k': model.cp(temperature) * scale / mass,
                           'h_j_per_kg': model.h(temperature) * scale / mass,
                           's_j_per_kg_k': model.s(temperature) * scale / mass})
    air = ct.Species.list_from_yaml((root / '调研/原始来源/20261003_cantera_v3.1.0_airNASA9.yaml').read_text(encoding='utf-8'), section='species')
    comparison = []
    for record in manifest['species']:
        other = next((species for species in air if species.name == record['id']), None)
        if other is None:
            continue
        flattened = [len(record['ranges'])]
        for interval in record['ranges']:
            flattened += [interval['t_min_k'], interval['t_max_k'], *interval['coefficients']]
        match = len(flattened) == len(other.thermo.coeffs) and all(
                left == right for left, right in zip(flattened, other.thermo.coeffs))
        if not match:
            raise ValueError(f'Air NASA9 source disagreement for {record["id"]}')
        comparison.append(record['id'])
    header = ['#ifndef ROCKETPERF_NASA9_REFERENCE_H', '#define ROCKETPERF_NASA9_REFERENCE_H',
              'typedef struct { const char *id; double temperature_k; double cp; double h; double s; } RpThermoReference;',
              'static const RpThermoReference rp_thermo_references[] = {']
    for state in states:
        header.append('    {' + f'"{state["id"]}", ' + ', '.join(formatted(state[key]) for key in
                      ('temperature_k', 'cp_j_per_kg_k', 'h_j_per_kg', 's_j_per_kg_k')) + '},')
    header += ['};', '#endif', '']
    atomic_text(root / 'tests/reference/nasa9_cantera.h', '\n'.join(header))
    atomic_json(root / 'tests/reference/nasa9_cantera.json', {
        'schema_version': 1, 'implementation': 'Cantera Nasa9PolyMultiTempRegion', 'version': ct.__version__,
                           'platform': sys.platform, 'gas_constant_j_kmol_k': CEA_GAS_CONSTANT,
        'dataset_manifest_sha256': digest(root / 'data/thermo/manifest.json'),
        'reference_header_sha256': digest(root / 'tests/reference/nasa9_cantera.h'),
        'air_source_sha256': digest(root / '调研/原始来源/20261003_cantera_v3.1.0_airNASA9.yaml'),
        'independent_air_coefficients_matched': comparison, 'states': states,
        'cantera_gas_constant_j_kmol_k': ct.gas_constant,
        'scope': 'Independent software evaluation of same coefficients, scaled to CEA gas constant; not independent experimental data.',
    })
    print(f'Cantera reference: {len(states)} states; separate air file matches {comparison}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--reference', action='store_true')
    arguments = parser.parse_args()
    if arguments.check:
        print(f'NASA9 data: {check_generated()} generated artifacts checked')
    elif arguments.reference:
        make_reference()
    else:
        for path, content in generated_files().items():
            atomic_text(ROOT / path, content)
        print(f'NASA9 generated: {len(SPECIES)} real neutral species')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        print(f'thermo-data: {error}', file=sys.stderr)
        sys.exit(1)
