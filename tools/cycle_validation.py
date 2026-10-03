"""Recompute cycle report accounting from inputs and public states; not a physical engine validation."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import shutil

from projectlib import ROOT, atomic_json, digest, read_json

MODEL = 'prescribed_thermal_cycle_v1'
BOUNDARY = 'pump_inlets_to_two_nozzle_exits_auxiliary_shaft_and_mechanical_heat'
DATASET = 'cea-v3.3.4-neutral-cho-n-v1'
SPECIES = {'H2', 'O2', 'H2O', 'CO', 'CO2', 'CH4', 'H', 'O', 'OH'}
INPUTS = {
    'total_mass_flow_kg_per_s', 'overall_oxidizer_fuel_ratio', 'chamber_pressure_pa', 'chamber_temperature_k',
    'main_area_ratio', 'generator_oxidizer_fuel_ratio', 'generator_temperature_k', 'turbine_inlet_pressure_pa',
    'turbine_outlet_pressure_pa', 'turbine_efficiency', 'shaft_efficiency', 'auxiliary_power_w',
    'maximum_branch_fraction', 'return_fraction', 'return_pressure_drop_pa', 'branch_area_ratio',
    'branch_axial_projection', 'ambient_pressure_pa',
    *(f'{pump}_pump_{field}' for pump in ('fuel', 'oxidizer') for field in
      ('density_kg_per_m3', 'inlet_pressure_pa', 'outlet_pressure_pa', 'efficiency', 'inlet_h_j_per_kg')),
}


def validate_cycle(report, input_text):
    required = {'schema_version', 'program_version', 'model', 'dataset_id', 'boundary', 'case', 'inputs',
                'flows', 'pumps', 'turbine', 'main_nozzle', 'branch_nozzle', 'performance', 'energy', 'diagnostics', 'limitations'}
    if not isinstance(report, dict) or set(report) != required or type(report['schema_version']) is not int or report['schema_version'] != 1:
        raise ValueError('Invalid prescribed cycle schema')
    if (report['model'], report['dataset_id'], report['boundary']) != (MODEL, DATASET, BOUNDARY):
        raise ValueError('Cycle model, dataset or boundary mismatch')
    if not re.fullmatch(r'\d+\.\d+\.\d+', str(report['program_version'])):
        raise ValueError('Invalid cycle version')
    values = {}
    for line in input_text.lstrip('\ufeff').splitlines():
        line = line.strip()
        if not line or line.startswith('#'): continue
        key, sep, value = line.partition('='); key = key.strip(); value = value.strip()
        if not sep or key in values: raise ValueError('Malformed cycle snapshot')
        values[key] = value
    if set(values) != INPUTS | {'schema_version', 'case_id', 'case_kind', 'source_ref', 'model'} or values['model'] != MODEL or values['schema_version'] != '1':
        raise ValueError('Snapshot schema mismatch')
    if report['case'] != {k: values['case_' + k] if k != 'source_ref' else values[k] for k in ('id', 'kind', 'source_ref')}:
        raise ValueError('Cycle provenance mismatch')
    if report['case']['kind'] not in {'synthetic_benchmark', 'research_scenario'}:
        raise ValueError('Unsupported cycle data role')
    if set(report['inputs']) != INPUTS: raise ValueError('Incomplete cycle inputs')
    for key in INPUTS:
        x = report['inputs'][key]
        if type(x) not in (int, float) or not math.isfinite(x) or x != float(values[key]):
            raise ValueError(f'Cycle input mismatch: {key}')

    def finite_tree(obj):
        if isinstance(obj, dict):
            for item in obj.values(): finite_tree(item)
        elif isinstance(obj, list):
            for item in obj: finite_tree(item)
        elif type(obj) in (int, float):
            if not math.isfinite(obj): raise ValueError('Non-finite cycle output')
        elif not isinstance(obj, str) and obj is not None:
            raise ValueError('Unexpected cycle output type')
    finite_tree(report)
    equations = []
    def same(label, actual, expected, absolute=1e-6, relative=1e-9):
        if type(actual) not in (int, float) or not math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute):
            raise ValueError(f'Cycle equation failed: {label}')
        equations.append(label)
    def nonnegative(label, x):
        if type(x) not in (int, float) or x < 0: raise ValueError(f'Negative cycle quantity: {label}')
    def gas(state):
        if set(state) != {'temperature_k', 'pressure_pa', 'h_j_per_kg', 's_j_per_kg_k', 'cp_frozen_j_per_kg_k', 'mole_fractions'}:
            raise ValueError('Invalid gas state fields')
        if any(type(state[k]) not in (int, float) or state[k] <= 0 for k in ('temperature_k', 'pressure_pa', 'cp_frozen_j_per_kg_k')):
            raise ValueError('Nonpositive cycle gas state')
        y = state['mole_fractions']
        if set(y) != SPECIES or any(type(x) not in (int, float) or not 0 <= x <= 1 for x in y.values()):
            raise ValueError('Invalid cycle composition')
        same('composition sum', sum(y.values()), 1, 1e-12, 0)
    i = report['inputs']; f = report['flows']; e = report['energy']; p = report['performance']; d = report['diagnostics']
    for name, expected in (
        ('flows', {'fuel_mass_flow_kg_per_s','oxidizer_mass_flow_kg_per_s','branch_mass_flow_kg_per_s',
         'branch_fuel_mass_flow_kg_per_s','branch_oxidizer_mass_flow_kg_per_s','main_mass_flow_kg_per_s',
         'main_fuel_mass_flow_kg_per_s','main_oxidizer_mass_flow_kg_per_s','main_oxidizer_fuel_ratio',
         'external_mass_flow_kg_per_s','returned_mass_flow_kg_per_s'}),
        ('energy', {'pump_power_w','turbine_power_w','mechanical_loss_w','generator_required_heat_w',
         'chamber_required_heat_w','inlet_enthalpy_rate_w','exit_total_enthalpy_rate_w'}),
        ('performance', {'main_thrust_n','branch_thrust_n','total_thrust_n','main_throat_area_m2',
         'branch_throat_area_m2','main_effective_velocity_m_per_s','engine_effective_velocity_m_per_s','engine_specific_impulse_s'}),
        ('diagnostics', {'mass_residual_kg_per_s','shaft_residual_w','energy_residual_w','mass_relative_residual',
         'shaft_relative_residual','energy_relative_residual'})):
        if set(report[name]) != expected or any(type(x) not in (int,float) for x in report[name].values()):
            raise ValueError(f'Invalid cycle fields: {name}')
    if i['return_fraction'] != 0 or i['return_pressure_drop_pa'] != 0 or f['returned_mass_flow_kg_per_s'] != 0:
        raise ValueError('Unsupported return branch')
    if i['total_mass_flow_kg_per_s'] <= 0 or i['overall_oxidizer_fuel_ratio'] <= 0 or not 0 < i['shaft_efficiency'] <= 1:
        raise ValueError('Invalid cycle operating inputs')
    for label, x in f.items(): nonnegative(label, x)
    for label, x in p.items(): nonnegative(label, x)
    for key in ('pump_power_w','turbine_power_w','mechanical_loss_w'): nonnegative(key,e[key])
    mf = i['total_mass_flow_kg_per_s'] / (1+i['overall_oxidizer_fuel_ratio']); mo = i['total_mass_flow_kg_per_s'] - mf
    same('fuel flow', f['fuel_mass_flow_kg_per_s'], mf); same('oxidizer flow', f['oxidizer_mass_flow_kg_per_s'], mo)
    if set(report['pumps']) != {'fuel','oxidizer'}: raise ValueError('Invalid pump fields')
    pump = 0.0; hfeed = {}
    for stream, flow in (('fuel', mf), ('oxidizer', mo)):
        prefix = stream + '_pump_'; r = report['pumps'][stream]
        if set(r) != {'specific_work_j_per_kg','shaft_power_w','outlet_h_j_per_kg','energy_residual_w'}: raise ValueError('Invalid pump state')
        if i[prefix+'density_kg_per_m3'] <= 0 or not 0 < i[prefix+'efficiency'] <= 1: raise ValueError('Invalid feed properties')
        work = (i[prefix+'outlet_pressure_pa'] - i[prefix+'inlet_pressure_pa']) / i[prefix+'density_kg_per_m3'] / i[prefix+'efficiency']
        nonnegative('pump work',work)
        same(stream+' pump work',r['specific_work_j_per_kg'],work); same(stream+' pump power',r['shaft_power_w'],flow*work)
        hfeed[stream] = i[prefix+'inlet_h_j_per_kg'] + work
        same(stream+' pump enthalpy',r['outlet_h_j_per_kg'],hfeed[stream])
        same(stream+' pump energy residual',r['energy_residual_w'],0,1e-5,0)
        pump += flow*work
    t = report['turbine']
    if set(t) != {'inlet','isentropic_outlet','outlet','specific_work_j_per_kg','entropy_generation_j_per_kg_k','efficiency_residual_j_per_kg'}: raise ValueError('Invalid turbine fields')
    for state in ('inlet','isentropic_outlet','outlet'): gas(t[state])
    for state in ('isentropic_outlet','outlet'):
        if t[state]['mole_fractions'] != t['inlet']['mole_fractions']: raise ValueError('Turbine composition not frozen')
        same('turbine outlet pressure',t[state]['pressure_pa'],i['turbine_outlet_pressure_pa'])
    same('generator temperature',t['inlet']['temperature_k'],i['generator_temperature_k'])
    same('generator pressure',t['inlet']['pressure_pa'],i['turbine_inlet_pressure_pa'])
    drop = t['inlet']['h_j_per_kg'] - t['outlet']['h_j_per_kg']
    same('turbine work',t['specific_work_j_per_kg'],drop,0.01)
    same('turbine efficiency',drop,i['turbine_efficiency']*(t['inlet']['h_j_per_kg']-t['isentropic_outlet']['h_j_per_kg']),0.01)
    same('isentropic outlet entropy',t['isentropic_outlet']['s_j_per_kg_k'],t['inlet']['s_j_per_kg_k'],1e-7,0)
    same('entropy generation',t['entropy_generation_j_per_kg_k'],t['outlet']['s_j_per_kg_k']-t['inlet']['s_j_per_kg_k'],1e-7,0)
    if t['entropy_generation_j_per_kg_k'] < -1e-7: raise ValueError('Negative turbine entropy generation')
    same('turbine efficiency residual',t['efficiency_residual_j_per_kg'],0,0.01,0)
    branch = f['branch_mass_flow_kg_per_s']; main = f['main_mass_flow_kg_per_s']
    if branch > i['maximum_branch_fraction']*i['total_mass_flow_kg_per_s']: raise ValueError('Excess branch flow')
    same('branch fuel',f['branch_fuel_mass_flow_kg_per_s'],branch/(1+i['generator_oxidizer_fuel_ratio']))
    same('branch oxidizer',f['branch_oxidizer_mass_flow_kg_per_s'],branch-f['branch_fuel_mass_flow_kg_per_s'])
    same('main fuel',f['main_fuel_mass_flow_kg_per_s'],mf-f['branch_fuel_mass_flow_kg_per_s'])
    same('main oxidizer',f['main_oxidizer_mass_flow_kg_per_s'],mo-f['branch_oxidizer_mass_flow_kg_per_s'])
    same('main OF',f['main_oxidizer_fuel_ratio'],f['main_oxidizer_mass_flow_kg_per_s']/f['main_fuel_mass_flow_kg_per_s'])
    same('mass closure',main+branch,i['total_mass_flow_kg_per_s']); same('external flow',f['external_mass_flow_kg_per_s'],branch)
    same('pump sum',e['pump_power_w'],pump)
    same('shaft closure',i['shaft_efficiency']*branch*drop,pump+i['auxiliary_power_w'])
    same('turbine total power',e['turbine_power_w'],branch*drop)
    same('mechanical loss',e['mechanical_loss_w'],(1-i['shaft_efficiency'])*branch*drop)
    if (branch == 0) != (report['branch_nozzle'] is None): raise ValueError('Inactive branch nozzle mismatch')
    exit_energy = 0.0
    for label, flow, projection in (('main',main,1.0),('branch',branch,i['branch_axial_projection'])):
        n = report[label+'_nozzle']
        if n is None:
            same('zero branch thrust',p['branch_thrust_n'],0); same('zero branch area',p['branch_throat_area_m2'],0); continue
        if set(n) != {'chamber','throat','exit','effective_velocity_m_per_s','cstar_m_per_s','continuity_relative_residual','sonic_relative_residual'}: raise ValueError('Invalid nozzle fields')
        gas(n['chamber'])
        for position in ('throat','exit'):
            station = n[position]; gas(station['gas'])
            if set(station) != {'gas','velocity_m_per_s','mass_flux_kg_per_m2_s','mach','energy_residual_j_per_kg','entropy_residual_j_per_kg_k'}: raise ValueError('Invalid flow station')
            if station['gas']['mole_fractions'] != n['chamber']['mole_fractions']: raise ValueError('Nozzle composition not frozen')
            same('nozzle energy',station['gas']['h_j_per_kg']+0.5*station['velocity_m_per_s']**2,n['chamber']['h_j_per_kg'],1e-4,0)
            same('nozzle entropy',station['gas']['s_j_per_kg_k'],n['chamber']['s_j_per_kg_k'],1e-7,0)
            same('nozzle energy residual',station['energy_residual_j_per_kg'],0,1e-4,0)
            same('nozzle entropy residual',station['entropy_residual_j_per_kg_k'],0,1e-7,0)
        ratio=i[label+'_area_ratio']; throat=n['throat']; exit=n['exit']
        if exit['gas']['pressure_pa'] < i['ambient_pressure_pa']: raise ValueError('Unsupported overexpansion')
        same('nozzle continuity',exit['mass_flux_kg_per_m2_s']*ratio,throat['mass_flux_kg_per_m2_s'],1e-6)
        same('sonic throat',throat['mach'],1,1e-8,0)
        same('nozzle continuity residual',n['continuity_relative_residual'],0,1e-8,0)
        same('nozzle sonic residual',n['sonic_relative_residual'],0,1e-8,0)
        velocity = exit['velocity_m_per_s'] + (exit['gas']['pressure_pa']-i['ambient_pressure_pa'])*ratio/throat['mass_flux_kg_per_m2_s']
        same(label+' effective velocity',n['effective_velocity_m_per_s'],velocity)
        same(label+' throat area',p[label+'_throat_area_m2'],flow/throat['mass_flux_kg_per_m2_s'])
        same(label+' thrust',p[label+'_thrust_n'],flow*velocity*projection)
        exit_energy += flow*(exit['gas']['h_j_per_kg']+0.5*exit['velocity_m_per_s']**2)
    chamber = report['main_nozzle']['chamber']
    same('main chamber temperature',chamber['temperature_k'],i['chamber_temperature_k'])
    same('main chamber pressure',chamber['pressure_pa'],i['chamber_pressure_pa'])
    if report['branch_nozzle'] is not None and report['branch_nozzle']['chamber'] != t['outlet']: raise ValueError('Turbine/nozzle state mismatch')
    same('main effective velocity',p['main_effective_velocity_m_per_s'],p['main_thrust_n']/main)
    same('total thrust',p['total_thrust_n'],p['main_thrust_n']+p['branch_thrust_n'])
    same('engine velocity',p['engine_effective_velocity_m_per_s'],p['total_thrust_n']/i['total_mass_flow_kg_per_s'])
    same('engine Isp',p['engine_specific_impulse_s'],p['engine_effective_velocity_m_per_s']/9.80665)
    hin = mf*i['fuel_pump_inlet_h_j_per_kg']+mo*i['oxidizer_pump_inlet_h_j_per_kg']
    qg = branch*t['inlet']['h_j_per_kg']-f['branch_fuel_mass_flow_kg_per_s']*hfeed['fuel']-f['branch_oxidizer_mass_flow_kg_per_s']*hfeed['oxidizer']
    qc = main*chamber['h_j_per_kg']-f['main_fuel_mass_flow_kg_per_s']*hfeed['fuel']-f['main_oxidizer_mass_flow_kg_per_s']*hfeed['oxidizer']
    same('required generator heat',e['generator_required_heat_w'],qg)
    same('required chamber heat',e['chamber_required_heat_w'],qc)
    same('inlet enthalpy rate',e['inlet_enthalpy_rate_w'],hin); same('exit total enthalpy rate',e['exit_total_enthalpy_rate_w'],exit_energy)
    energy_residual = hin+qg+qc-exit_energy-i['auxiliary_power_w']-e['mechanical_loss_w']
    same('global energy accounting',energy_residual,0,0.01,0)
    same('mass residual',d['mass_residual_kg_per_s'],0,1e-10,0)
    same('shaft residual',d['shaft_residual_w'],0,1e-4,0)
    same('energy residual',d['energy_residual_w'],energy_residual,0.01,0)
    for key, limit in (('mass_relative_residual',1e-12),('shaft_relative_residual',1e-8),('energy_relative_residual',1e-10)):
        same(key,d[key],0,limit,0)
    if not isinstance(report['limitations'],list) or len(report['limitations']) < 4 or any(not isinstance(x,str) or not x for x in report['limitations']):
        raise ValueError('Cycle limitations missing')
    return equations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',default='cases/benchmarks/prescribed_cycle.ini')
    parser.add_argument('--archive-id', help='New immutable directory under results/validation')
    args=parser.parse_args()
    if args.archive_id and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',args.archive_id): raise ValueError('Unsafe archive ID')
    import pipeline
    folder=pipeline.run_case(ROOT,args.case,model='prescribed-cycle',no_build=True)
    report=read_json(folder/'result.json'); equations=validate_cycle(report,(folder/'input.ini').read_text(encoding='utf-8-sig'))
    if args.archive_id:
        archive=ROOT/'results/validation'/args.archive_id; archive.mkdir(parents=True,exist_ok=False)
        records=[]
        for filename in ('input.ini','result.json','stdout.txt','stderr.txt','run-manifest.json','build-manifest.json','test-report.json'):
            shutil.copy2(folder/filename,archive/filename)
            records.append({'path':filename,'sha256':digest(archive/filename)})
        atomic_json(archive/'manifest.json',{'schema_version':1,'kind':'cycle-accounting-validation','model':MODEL,
            'equations':equations,'files':records,'scope':'Synthetic bookkeeping and component checks, not independent engine/combustion validation'})
        print(f'Archived: {archive}')
    print(f'Cycle accounting: {len(equations)} equations PASS')


def check_archive(folder):
    folder = Path(folder)
    record = read_json(folder/'manifest.json')
    expected = {'input.ini','result.json','stdout.txt','stderr.txt','run-manifest.json','build-manifest.json','test-report.json'}
    files=record.get('files',[])
    if record.get('kind') != 'cycle-accounting-validation' or record.get('model') != MODEL or len(files) != len(expected) or {f['path'] for f in files} != expected:
        raise ValueError('Incomplete cycle archive')
    for item in files:
        if digest(folder/item['path']) != item['sha256']: raise ValueError('Cycle archive hash mismatch')
    run=read_json(folder/'run-manifest.json'); build=read_json(folder/'build-manifest.json'); tests=read_json(folder/'test-report.json')
    if run.get('status') != 'SUCCESS' or build.get('status') != 'PASS' or tests.get('status') != 'PASS' or run.get('command',[None])[1:3] != ['cycle','prescribed']:
        raise ValueError('Cycle archive has no successful tested run')
    for field, filename in [('input_sha256','input.ini'),('output_sha256','result.json'),('build_manifest_sha256','build-manifest.json'),('test_report_sha256','test-report.json')]:
        if run[field] != digest(folder/filename): raise ValueError('Cycle run snapshot mismatch')
    if tests['build_manifest_sha256'] != digest(folder/'build-manifest.json') or run['executable_sha256'] != build['application']['sha256']:
        raise ValueError('Cycle tested binary identity mismatch')
    if digest(folder/'stdout.txt') != digest(folder/'result.json') or (folder/'stderr.txt').stat().st_size != 0:
        raise ValueError('Cycle stdout/stderr protocol mismatch')
    equations=validate_cycle(read_json(folder/'result.json'),(folder/'input.ini').read_text(encoding='utf-8-sig'))
    if record['equations'] != equations or run['accounting_checks'] != len(equations): raise ValueError('Cycle archive equation evidence mismatch')
    return equations


if __name__=='__main__': main()
