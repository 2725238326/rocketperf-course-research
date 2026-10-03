"""Recompute cycle report accounting from inputs and public states; not a physical engine validation."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import shutil
import sys
from functools import partial

from projectlib import ROOT, atomic_json, digest, read_json
from gas_checks import check_elements, database, mixture

MODEL = 'prescribed_thermal_cycle_v1'
BOUNDARY = 'pump_inlets_to_two_nozzle_exits_auxiliary_shaft_and_mechanical_heat'
DATASET = 'cea-v3.3.4-neutral-cho-n-v1'
VALIDATION_VERSION = 2
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


def validate_cycle(report, input_text, root=ROOT):
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
    if not isinstance(report['inputs'],dict) or set(report['inputs']) != INPUTS: raise ValueError('Incomplete cycle inputs')
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
    equations = []; extended_equations = []
    fits = database(root)
    def same(label, actual, expected, absolute=1e-6, relative=1e-9, extended=False):
        if type(actual) not in (int, float) or not math.isfinite(actual) or not math.isfinite(expected) or not math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute):
            raise ValueError(f'Cycle equation failed: {label}')
        (extended_equations if extended else equations).append(label)
    more = partial(same, extended=True)
    def numeric_fields(obj, expected, label):
        if not isinstance(obj,dict) or set(obj) != expected or any(type(x) not in (int,float) for x in obj.values()):
            raise ValueError(f'Invalid numeric fields: {label}')
    def nonnegative(label, x):
        if type(x) not in (int, float) or x < 0: raise ValueError(f'Negative cycle quantity: {label}')
    def gas(state):
        if not isinstance(state,dict) or set(state) != {'temperature_k', 'pressure_pa', 'h_j_per_kg', 's_j_per_kg_k', 'cp_frozen_j_per_kg_k', 'mole_fractions'}:
            raise ValueError('Invalid gas state fields')
        if any(type(v) not in (int,float) for k,v in state.items() if k != 'mole_fractions'):
            raise ValueError('Nonnumeric gas state')
        if any(type(state[k]) not in (int, float) or state[k] <= 0 for k in ('temperature_k', 'pressure_pa', 'cp_frozen_j_per_kg_k')):
            raise ValueError('Nonpositive cycle gas state')
        y = state['mole_fractions']
        if not isinstance(y,dict) or set(y) != SPECIES or any(type(x) not in (int, float) or not 0 <= x <= 1 for x in y.values()):
            raise ValueError('Invalid cycle composition')
        same('composition sum', sum(y.values()), 1, 1e-12, 0)
        evaluated=mixture(y,state['temperature_k'],state['pressure_pa'],fits)
        for key in ('h_j_per_kg','s_j_per_kg_k','cp_frozen_j_per_kg_k'):
            more('NASA9 '+key,state[key],evaluated[key],1e-6,2e-11)
        if state['cp_frozen_j_per_kg_k'] <= evaluated['gas_constant_j_per_kg_k']:
            raise ValueError('Nonpositive frozen cv')
        return evaluated['gas_constant_j_per_kg_k']
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
        numeric_fields(report[name],expected,name)
    if i['return_fraction'] != 0 or i['return_pressure_drop_pa'] != 0 or f['returned_mass_flow_kg_per_s'] != 0:
        raise ValueError('Unsupported return branch')
    if i['total_mass_flow_kg_per_s'] <= 0 or i['overall_oxidizer_fuel_ratio'] <= 0 or not 0 < i['shaft_efficiency'] <= 1:
        raise ValueError('Invalid cycle operating inputs')
    if (not 0.1 <= i['generator_oxidizer_fuel_ratio'] <= 20 or not 0 < i['turbine_efficiency'] <= 1
        or not 0 < i['maximum_branch_fraction'] < 1 or not 0 <= i['branch_axial_projection'] <= 1
        or i['auxiliary_power_w'] < 0 or i['ambient_pressure_pa'] < 0
        or not 0 < i['turbine_outlet_pressure_pa'] <= i['turbine_inlet_pressure_pa']
        or any(not 1 <= i[k] <= 1e4 for k in ('main_area_ratio','branch_area_ratio'))
        or any(not 1000 <= i[k] <= 6000 for k in ('chamber_temperature_k','generator_temperature_k'))
        or any(not 100 <= i[k] <= 1e9 for k in ('chamber_pressure_pa','turbine_inlet_pressure_pa'))):
        raise ValueError('Cycle input outside supported domain')
    for label, x in f.items(): nonnegative(label, x)
    for label, x in p.items(): nonnegative(label, x)
    for key in ('pump_power_w','turbine_power_w','mechanical_loss_w'): nonnegative(key,e[key])
    mf = i['total_mass_flow_kg_per_s'] / (1+i['overall_oxidizer_fuel_ratio']); mo = i['total_mass_flow_kg_per_s'] - mf
    same('fuel flow', f['fuel_mass_flow_kg_per_s'], mf); same('oxidizer flow', f['oxidizer_mass_flow_kg_per_s'], mo)
    if not isinstance(report['pumps'],dict) or set(report['pumps']) != {'fuel','oxidizer'}: raise ValueError('Invalid pump fields')
    pump = 0.0; hfeed = {}
    for stream, flow in (('fuel', mf), ('oxidizer', mo)):
        prefix = stream + '_pump_'; r = report['pumps'][stream]
        numeric_fields(r,{'specific_work_j_per_kg','shaft_power_w','outlet_h_j_per_kg','energy_residual_w'},'pump')
        if i[prefix+'density_kg_per_m3'] <= 0 or not 0 < i[prefix+'efficiency'] <= 1: raise ValueError('Invalid feed properties')
        if not 0 < i[prefix+'inlet_pressure_pa'] <= i[prefix+'outlet_pressure_pa'] or i[prefix+'outlet_pressure_pa'] < i['chamber_pressure_pa']:
            raise ValueError('Invalid pump pressure reachability')
        work = (i[prefix+'outlet_pressure_pa'] - i[prefix+'inlet_pressure_pa']) / i[prefix+'density_kg_per_m3'] / i[prefix+'efficiency']
        nonnegative('pump work',work)
        same(stream+' pump work',r['specific_work_j_per_kg'],work); same(stream+' pump power',r['shaft_power_w'],flow*work)
        hfeed[stream] = i[prefix+'inlet_h_j_per_kg'] + work
        same(stream+' pump enthalpy',r['outlet_h_j_per_kg'],hfeed[stream])
        residual=flow*(r['outlet_h_j_per_kg']-i[prefix+'inlet_h_j_per_kg'])-r['shaft_power_w']
        allowance=1e-8*max(1.0,r['shaft_power_w'])
        same(stream+' pump energy residual',r['energy_residual_w'],0,allowance,0)
        more(stream+' pump residual identity',r['energy_residual_w'],residual,1e-10*max(1.0,r['shaft_power_w']),0)
        pump += flow*work
    t = report['turbine']
    if not isinstance(t,dict) or set(t) != {'inlet','isentropic_outlet','outlet','specific_work_j_per_kg','entropy_generation_j_per_kg_k','efficiency_residual_j_per_kg'}: raise ValueError('Invalid turbine fields')
    for state in ('inlet','isentropic_outlet','outlet'): gas(t[state])
    numeric_fields({k:v for k,v in t.items() if k not in {'inlet','isentropic_outlet','outlet'}},
                   {'specific_work_j_per_kg','entropy_generation_j_per_kg_k','efficiency_residual_j_per_kg'},'turbine')
    check_elements(t['inlet']['mole_fractions'],i['generator_oxidizer_fuel_ratio'],fits)
    extended_equations.append('generator elements')
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
    if main <= 0 or f['main_fuel_mass_flow_kg_per_s'] <= 0 or f['main_oxidizer_mass_flow_kg_per_s'] <= 0 or not 0.1 <= f['main_oxidizer_fuel_ratio'] <= 20:
        raise ValueError('Invalid main feed flow or mixture ratio')
    if branch > 0 and any(i[s+'_pump_outlet_pressure_pa'] < i['turbine_inlet_pressure_pa'] for s in ('fuel','oxidizer')):
        raise ValueError('Pump pressure cannot reach generator')
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
            if label == 'main': raise ValueError('Main nozzle required')
            same('zero branch thrust',p['branch_thrust_n'],0); same('zero branch area',p['branch_throat_area_m2'],0); continue
        if not isinstance(n,dict) or set(n) != {'chamber','throat','exit','effective_velocity_m_per_s','cstar_m_per_s','continuity_relative_residual','sonic_relative_residual'}: raise ValueError('Invalid nozzle fields')
        gas(n['chamber'])
        numeric_fields({k:v for k,v in n.items() if k not in {'chamber','throat','exit'}},
                       {'effective_velocity_m_per_s','cstar_m_per_s','continuity_relative_residual','sonic_relative_residual'},'nozzle')
        if n['effective_velocity_m_per_s'] <= 0 or n['cstar_m_per_s'] <= 0: raise ValueError('Nonpositive nozzle performance')
        for position in ('throat','exit'):
            station = n[position]
            if not isinstance(station,dict) or 'gas' not in station: raise ValueError('Invalid flow station')
            gas_constant=gas(station['gas'])
            if set(station) != {'gas','velocity_m_per_s','mass_flux_kg_per_m2_s','mach','energy_residual_j_per_kg','entropy_residual_j_per_kg_k'}: raise ValueError('Invalid flow station')
            numeric_fields({k:v for k,v in station.items() if k != 'gas'},
                           {'velocity_m_per_s','mass_flux_kg_per_m2_s','mach','energy_residual_j_per_kg','entropy_residual_j_per_kg_k'},'flow station')
            if any(station[k] <= 0 for k in ('velocity_m_per_s','mass_flux_kg_per_m2_s','mach')): raise ValueError('Nonpositive flow station')
            sg=station['gas']; cp=sg['cp_frozen_j_per_kg_k']
            sound=math.sqrt(cp/(cp-gas_constant)*gas_constant*sg['temperature_k'])
            more(label+' '+position+' Mach',station['mach'],station['velocity_m_per_s']/sound,1e-9)
            more(label+' '+position+' mass flux',station['mass_flux_kg_per_m2_s'],sg['pressure_pa']/(gas_constant*sg['temperature_k'])*station['velocity_m_per_s'])
            if station['gas']['mole_fractions'] != n['chamber']['mole_fractions']: raise ValueError('Nozzle composition not frozen')
            same('nozzle energy',station['gas']['h_j_per_kg']+0.5*station['velocity_m_per_s']**2,n['chamber']['h_j_per_kg'],1e-5,0)
            same('nozzle entropy',station['gas']['s_j_per_kg_k'],n['chamber']['s_j_per_kg_k'],1e-7,0)
            same('nozzle energy residual',station['energy_residual_j_per_kg'],0,1e-5,0)
            same('nozzle entropy residual',station['entropy_residual_j_per_kg_k'],0,1e-7,0)
        ratio=i[label+'_area_ratio']; throat=n['throat']; exit=n['exit']
        if exit['mach'] < 1-1e-8 or not exit['gas']['temperature_k'] <= throat['gas']['temperature_k'] < n['chamber']['temperature_k']:
            raise ValueError('Wrong frozen nozzle expansion branch')
        more(label+' cstar',n['cstar_m_per_s'],n['chamber']['pressure_pa']/throat['mass_flux_kg_per_m2_s'])
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
    check_elements(chamber['mole_fractions'],f['main_oxidizer_fuel_ratio'],fits)
    extended_equations.append('main elements')
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
    mass_scale=i['total_mass_flow_kg_per_s']; shaft_scale=max(1.0,pump+i['auxiliary_power_w'])
    energy_scale=max(1.0,abs(hin)+abs(qg)+abs(qc)+abs(exit_energy))
    same('global energy accounting',energy_residual,0,1e-10*energy_scale,0)
    same('mass residual',d['mass_residual_kg_per_s'],0,1e-12*mass_scale,0)
    same('shaft residual',d['shaft_residual_w'],0,1e-8*shaft_scale,0)
    same('energy residual',d['energy_residual_w'],energy_residual,1e-12*energy_scale,0)
    more('mass residual identity',d['mass_residual_kg_per_s'],mass_scale-main-branch,1e-12*mass_scale,0)
    more('shaft residual identity',d['shaft_residual_w'],i['shaft_efficiency']*branch*drop-pump-i['auxiliary_power_w'],1e-10*shaft_scale,0)
    for key,residual,scale in [('mass_relative_residual',d['mass_residual_kg_per_s'],mass_scale),
                               ('shaft_relative_residual',d['shaft_residual_w'],shaft_scale),
                               ('energy_relative_residual',d['energy_residual_w'],energy_scale)]:
        more(key+' identity',d[key],residual/scale,1e-15,0)
    for key, limit in (('mass_relative_residual',1e-12),('shaft_relative_residual',1e-8),('energy_relative_residual',1e-10)):
        same(key,d[key],0,limit,0)
    if not isinstance(report['limitations'],list) or len(report['limitations']) < 4 or any(not isinstance(x,str) or not x for x in report['limitations']):
        raise ValueError('Cycle limitations missing')
    return equations + extended_equations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',default='cases/benchmarks/prescribed_cycle.ini')
    parser.add_argument('--archive-id', help='New immutable directory under results/validation')
    args=parser.parse_args()
    if args.archive_id and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',args.archive_id): raise ValueError('Unsafe archive ID')
    archive=ROOT/'results/validation'/args.archive_id if args.archive_id else None
    if archive is not None and archive.exists(): raise ValueError('Archive already exists; choose a new ID')
    import pipeline
    folder=pipeline.run_case(ROOT,args.case,model='prescribed-cycle',no_build=True)
    report=read_json(folder/'result.json'); equations=validate_cycle(report,(folder/'input.ini').read_text(encoding='utf-8-sig'))
    if args.archive_id:
        archive.mkdir(parents=True,exist_ok=False)
        records=[]
        for filename in ('input.ini','result.json','stdout.txt','stderr.txt','run-manifest.json','build-manifest.json','test-report.json'):
            shutil.copy2(folder/filename,archive/filename)
            records.append({'path':filename,'sha256':digest(archive/filename)})
        atomic_json(archive/'manifest.json',{'schema_version':2,'validation_version':VALIDATION_VERSION,'kind':'cycle-accounting-validation','model':MODEL,
            'equations':equations,'files':records,'scope':'Synthetic bookkeeping and component checks, not independent engine/combustion validation'})
        print(f'Archived: {archive}')
    print(f'Cycle accounting: {len(equations)} equations PASS')


def check_archive(folder):
    folder = Path(folder)
    record = read_json(folder/'manifest.json')
    if not isinstance(record,dict): raise ValueError('Cycle archive must be an object')
    version=record.get('schema_version')
    if type(version) is not int or version not in (1,2) or (version == 2 and record.get('validation_version') != VALIDATION_VERSION):
        raise ValueError('Unsupported cycle archive validation version')
    expected = {'input.ini','result.json','stdout.txt','stderr.txt','run-manifest.json','build-manifest.json','test-report.json'}
    files=record.get('files',[])
    if (not isinstance(files,list) or any(not isinstance(f,dict) or set(f) != {'path','sha256'}
        or not isinstance(f['path'],str) or not isinstance(f['sha256'],str) for f in files)
        or record.get('kind') != 'cycle-accounting-validation' or record.get('model') != MODEL or len(files) != len(expected) or {f['path'] for f in files} != expected):
        raise ValueError('Incomplete cycle archive')
    for item in files:
        if digest(folder/item['path']) != item['sha256']: raise ValueError('Cycle archive hash mismatch')
    run=read_json(folder/'run-manifest.json'); build=read_json(folder/'build-manifest.json'); tests=read_json(folder/'test-report.json')
    if any(not isinstance(r,dict) for r in (run,build,tests)): raise ValueError('Invalid cycle archive report shape')
    if run.get('status') != 'SUCCESS' or build.get('status') != 'PASS' or tests.get('status') != 'PASS' or run.get('command',[None])[1:3] != ['cycle','prescribed']:
        raise ValueError('Cycle archive has no successful tested run')
    for field, filename in [('input_sha256','input.ini'),('output_sha256','result.json'),('build_manifest_sha256','build-manifest.json'),('test_report_sha256','test-report.json')]:
        if run[field] != digest(folder/filename): raise ValueError('Cycle run snapshot mismatch')
    if tests['build_manifest_sha256'] != digest(folder/'build-manifest.json') or run['executable_sha256'] != build['application']['sha256']:
        raise ValueError('Cycle tested binary identity mismatch')
    if digest(folder/'stdout.txt') != digest(folder/'result.json') or (folder/'stderr.txt').stat().st_size != 0:
        raise ValueError('Cycle stdout/stderr protocol mismatch')
    equations=validate_cycle(read_json(folder/'result.json'),(folder/'input.ini').read_text(encoding='utf-8-sig'))
    if version == 1:
        # Recheck every new invariant, retain the historical count/order honestly.
        historical=record['equations']
        if not isinstance(historical,list) or len(historical) != 86 or historical != equations[:len(historical)] or run['accounting_checks'] != len(historical):
            raise ValueError('Historical cycle equation evidence mismatch')
        return historical
    from pipeline import verify_test_report
    verify_test_report(tests,build,digest(folder/'build-manifest.json'))
    if record['equations'] != equations or run['accounting_checks'] != len(equations) or run.get('validation_version') != VALIDATION_VERSION:
        raise ValueError('Cycle archive equation evidence mismatch')
    return equations


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try: main()
    except (ValueError,OSError,KeyError) as exc:
        print(f'cycle validation: {exc}',file=sys.stderr);sys.exit(1)
