"""Run the pure-C gas method cases against pinned CEA printed values."""
import argparse
import math
import re
import subprocess
import shutil
import sys
import uuid

from cea_reference import check_reference
from pipeline import strict_json, verified_build
from projectlib import ROOT, atomic_json, atomic_text, digest, now, read_json, subprocess_env
from gas_checks import database, mixture
from feed_candidates import parse_anchors
from thermo_data import RAW, SOURCE_HASHES

ANCHOR_DATASET = "cea-v3.3.4-ch4l-o2l-assigned-v1"
KEROSENE_DATASET = "cea-v3.3.4-rp1-o2l-assigned-v1"
CONTINUOUS_LIMITATIONS = [
    "Restricted nine-species ideal-gas products; no ions, condensed products or soot.",
    "Assumed pure single-phase liquid table states; no flash, extrapolation or measured engine inlet claim.",
    "HEOS enthalpy uses one CEA ideal-zero alignment; remaining ideal-cp differences are retained.",
    "Inlet pressures select enthalpy, not a pump path or injector feasibility calculation.",
    "Q=0 with no inlet kinetic energy or shaft work; no split-flow or full-cycle closure.",
]


def liquid_anchors():
    path = ROOT / RAW / "thermo.inp"
    if digest(path) != SOURCE_HASHES["thermo.inp"]:
        raise ValueError("Pinned assigned-reactant source differs")
    return parse_anchors(path.read_text(encoding="ascii"))[:2]


def compare_report(report, reference, mode, area=None, *, expected_inputs=None):
    """Check provenance, conservation and print-precision-aware reference errors."""
    explicit_h = mode in {'hp-h','frozen-h'}
    rp1 = mode in {'hp-rp1','frozen-rp1'}
    anchor = mode in {'hp-liquid','frozen-liquid','hp-rp1','frozen-rp1'}
    continuous = mode in {'hp-liquid-state','frozen-liquid-state'}
    nozzle_mode = mode in {'frozen','frozen-tp','frozen-h','frozen-liquid','frozen-liquid-state','frozen-rp1'}
    fixed = mode in {'frozen-tp','frozen-h','frozen-liquid','frozen-liquid-state','frozen-rp1'}
    if mode not in {'tp','hp','frozen','frozen-tp','hp-h','frozen-h','hp-liquid','frozen-liquid','hp-liquid-state','frozen-liquid-state','hp-rp1','frozen-rp1'} or (nozzle_mode and area not in {10,40}):
        raise ValueError('Unsupported fixed reference mode/area')
    if not isinstance(report, dict):
        raise ValueError('Combustion report must be an object')
    expected_model = 'ch4_o2_tp_frozen_fixed_area_v1' if fixed else 'ch4_o2_chamber_frozen_v1' if nozzle_mode else 'ch4_o2_gas_equilibrium_v1'
    if explicit_h:
        expected_model = 'ch4_o2_hp_enthalpy_frozen_fixed_area_v1' if fixed else 'ch4_o2_hp_enthalpy_v1'
    if anchor:
        expected_model = ('rp1_o2l_hp_frozen_fixed_area_v1' if fixed else 'rp1_o2l_hp_assigned_v1') if rp1 else ('ch4l_o2l_hp_frozen_fixed_area_v1' if fixed else 'ch4l_o2l_hp_assigned_v1')
    if continuous:
        expected_model = 'ch4_o2_continuous_liquid_hp_frozen_fixed_area_v1' if fixed else 'ch4_o2_continuous_liquid_hp_v1'
    required={'schema_version','model','mode','dataset_id','inputs','chamber','diagnostics','limitations'}
    if nozzle_mode: required.add('nozzle')
    if fixed: required.add('geometry')
    if explicit_h or anchor or continuous: required.add('boundary')
    if anchor: required.add('reactant_dataset_id')
    if continuous: required.update({'liquid_dataset_id','provenance'})
    if (set(report)!=required or type(report.get('schema_version')) is not int or report['schema_version'] != 1
        or report.get('mode') != mode or report.get('model') != expected_model):
        raise ValueError('Combustion mode/model/schema mismatch')
    limits=report.get('limitations')
    if (report.get('dataset_id') != 'cea-v3.3.4-neutral-cho-n-v1' or not isinstance(limits,list) or not limits
        or any(not isinstance(x,str) or not x.strip() for x in limits)):
        raise ValueError('Dataset or limitations missing')
    if anchor:
        expected_limits = [
            "Restricted nine-species ideal-gas products; no ions, condensed products or soot.",
            "Fixed liquid reactant enthalpies only; no liquid EOS, density, pressure correction or phase-stability solve.",
            "Frozen nozzle is chamber-frozen, inviscid and without shocks or separation.",
        ]
        if fixed:
            expected_limits.append("Fixed-area performance is single-nozzle only, not feed-system or full-cycle closure.")
        expected_limits.append("Pressure denotes ideal-gas product chamber pressure; no pump, shaft work or real-engine validation.")
        if rp1:
            expected_limits.extend([
                "Fixed CEA RP-1 pseudo-reactant; not an identified Chinese kerosene batch.",
                "Product p=10 MPa and O/F=2.2..4.0; rich-mixture condensation is outside this method."])
        if limits != expected_limits:
            raise ValueError('Fixed anchor limitations do not match implemented scope')
    if continuous:
        if limits != CONTINUOUS_LIMITATIONS + ([
            "Single fixed-area chamber-frozen inviscid nozzle; no shocks, separation or hardware losses."
        ] if fixed else []):
            raise ValueError('Continuous liquid scope mismatch')
    expected_input = dict(feed_phase='gas', pressure_pa=1e7, oxidizer_fuel_mass_ratio=3.4,
                          fuel_temperature_k=298.15, oxidizer_temperature_k=298.15)
    if explicit_h:
        expected_input = dict(feed_phase='gas', enthalpy_basis='nasa9-cea-v3.3.4',
                              pressure_pa=1e7, oxidizer_fuel_mass_ratio=3.4,
                              fuel_h_j_per_kg=0.0, oxidizer_h_j_per_kg=0.0)
        if expected_inputs is None: raise ValueError('Explicit enthalpy requires independent declared inputs')
    if anchor:
        anchor_dataset = KEROSENE_DATASET if rp1 else ANCHOR_DATASET
        expected_input = dict(feed_phase='liquid', anchor_dataset_id=anchor_dataset,
                              fuel_anchor_id='RP-1' if rp1 else 'CH4(L)', oxidizer_anchor_id='O2(L)',
                              pressure_pa=1e7, oxidizer_fuel_mass_ratio=3.4,
                              fuel_temperature_k=298.15 if rp1 else 111.643, oxidizer_temperature_k=90.170)
        if report['reactant_dataset_id'] != anchor_dataset or expected_inputs is None:
            raise ValueError('Assigned inlet requires pinned dataset and independent declared inputs')
    if continuous:
        from liquid_table import BASIS, REFERENCE_SHA
        from liquid_feed import DATASET
        expected_input = dict(feed_phase='liquid',enthalpy_basis=BASIS,
                              fuel_temperature_k=120.0,fuel_pressure_pa=1e7,
                              oxidizer_temperature_k=100.0,oxidizer_pressure_pa=1e7,
                              pressure_pa=1e7,oxidizer_fuel_mass_ratio=3.4)
        if expected_inputs is None or report['liquid_dataset_id'] != DATASET:
            raise ValueError('Continuous liquid requires independent inputs and pinned dataset')
        if report['provenance'] != dict(reference_manifest_sha256=REFERENCE_SHA,
                                       input_role='assumed_research',
                                       density_mass_basis='CoolProp7.1.0 EOS molar mass',
                                       chemical_mass_basis='CEA v3.3.4 molar mass'):
            raise ValueError('Continuous liquid provenance mismatch')
    if mode in {'tp','frozen-tp'}:
        expected_input['temperature_k'] = 3000.0
    if nozzle_mode:
        expected_input.update(area_ratio=area, ambient_pressure_pa=0.0)
    if fixed:
        expected_input['throat_area_m2'] = 1.0
        if expected_inputs is None: raise ValueError('Fixed geometry reference requires explicit TP inputs')
    if expected_inputs is not None:
        strings = {'feed_phase','enthalpy_basis','anchor_dataset_id','fuel_anchor_id','oxidizer_anchor_id'}
        if (mode not in {'tp','frozen-tp','hp-h','frozen-h','hp-liquid','frozen-liquid','hp-liquid-state','frozen-liquid-state','hp-rp1','frozen-rp1'} or not isinstance(expected_inputs,dict) or set(expected_inputs)!=set(expected_input)
            or expected_inputs.get('feed_phase')!=('liquid' if anchor or continuous else 'gas')
            or (explicit_h and expected_inputs.get('enthalpy_basis')!='nasa9-cea-v3.3.4')
            or (anchor and any(expected_inputs.get(k) != expected_input[k] for k in
                {'anchor_dataset_id','fuel_anchor_id','oxidizer_anchor_id','fuel_temperature_k','oxidizer_temperature_k'}))
            or any(type(x) not in (int,float) or not math.isfinite(x)
                   or (k not in {'fuel_h_j_per_kg','oxidizer_h_j_per_kg'} and (x<0 if k=='ambient_pressure_pa' else x<=0))
                   for k,x in expected_inputs.items() if k not in strings)
            or (fixed and expected_inputs.get('area_ratio') != area)):
            raise ValueError('Custom reference inputs require a positive numeric gas TP contract')
        expected_input=dict(expected_inputs)
    actual_input = report.get('inputs')
    if (not isinstance(actual_input, dict) or set(actual_input) != set(expected_input)
        or any(type(value) not in (int, float) or not math.isfinite(value)
               for key, value in actual_input.items() if key not in {'feed_phase','enthalpy_basis','anchor_dataset_id','fuel_anchor_id','oxidizer_anchor_id'})
        or actual_input != expected_input):
        raise ValueError('Report does not correspond to the fixed method inputs')
    errors = []

    def bounded(name, actual, target, tolerance):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(actual):
            raise ValueError(f'Non-finite or non-numeric {name}')
        delta = actual - target
        if abs(delta) > tolerance:
            raise ValueError(f'{name} error {delta} exceeds {tolerance}')
        errors.append(dict(field=name, actual=actual, reference=target, difference=delta, absolute_tolerance=tolerance))

    chamber = report['chamber']
    fits=database()
    def same(actual, expected, label, absolute=1e-6):
        if type(actual) not in (int,float) or not math.isfinite(actual) or not math.isclose(actual,expected,rel_tol=1e-9,abs_tol=absolute):
            raise ValueError('Combustion state relation failed: '+label)
    def gas(state):
        keys={'temperature_k','pressure_pa','molar_mass_kg_per_kmol','gas_constant_j_per_kg_k','cp_frozen_j_per_kg_k','h_j_per_kg','s_j_per_kg_k','mole_fractions'}
        if not isinstance(state,dict) or set(state)!=keys:
            raise ValueError('Invalid combustion gas shape')
        for key in keys-{'mole_fractions'}:
            x=state[key]
            if type(x) not in (int,float) or not math.isfinite(x) or (key not in {'h_j_per_kg','s_j_per_kg_k'} and x<=0):
                raise ValueError('Invalid combustion gas quantity: '+key)
        y=state['mole_fractions']
        if (not isinstance(y,dict) or set(y)!={'H2','O2','H2O','CO','CO2','CH4','H','O','OH'}
            or any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1 for x in y.values())):
            raise ValueError('Invalid combustion gas composition')
        same(sum(y.values()),1.0,'composition sum',1e-12)
        expected=mixture(y,state['temperature_k'],state['pressure_pa'],fits)
        for key,value in expected.items(): same(state[key],value,key)
        same(state['molar_mass_kg_per_kmol'],fits['gas_constant_j_kmol_k']/expected['gas_constant_j_per_kg_k'],'molar mass')
        if state['cp_frozen_j_per_kg_k']<=state['gas_constant_j_per_kg_k']: raise ValueError('Nonpositive mixture cv')
    gas(chamber)
    summary = reference['summary']
    rows = summary['rows']
    bounded('chamber.temperature_k', chamber['temperature_k'], rows['temperature_k'][0], 0.02)
    bounded('chamber.pressure_pa', chamber['pressure_pa'], rows['pressure_bar'][0] * 1e5, 1e-5)
    bounded('chamber.h_j_per_kg', chamber['h_j_per_kg'], rows['enthalpy_kj_kg'][0] * 1000, 3.0)
    bounded('chamber.molar_mass_kg_per_kmol', chamber['molar_mass_kg_per_kmol'], rows['molar_mass_kg_kmol'][0], 5e-5)
    bounded('chamber.s_j_per_kg_k', chamber['s_j_per_kg_k'], rows['entropy_kj_kg_k'][0] * 1000, 0.5)
    expected_ids = {'H2', 'O2', 'H2O', 'CO', 'CO2', 'CH4', 'H', 'O', 'OH'}
    fractions = chamber['mole_fractions']
    if set(fractions) != expected_ids:
        raise ValueError('Unexpected gas species set')
    for species, value in fractions.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0 or value > 1:
            raise ValueError('Invalid or non-positive species fraction')
        printed = summary['mole_fractions'].get(species)
        if printed is None:
            bounded('chamber.mole_fractions.' + species, value, 0.0, summary['output_trace_threshold'])
        else:
            bounded('chamber.mole_fractions.' + species, value, printed[0], 2e-6)
    bounded('fraction_sum', sum(fractions.values()), 1.0, 1e-12)
    carbon = fractions['CO'] + fractions['CO2'] + fractions['CH4']
    hydrogen = 2 * fractions['H2'] + 2 * fractions['H2O'] + 4 * fractions['CH4'] + fractions['H'] + fractions['OH']
    oxygen = 2 * fractions['O2'] + fractions['H2O'] + fractions['CO'] + 2 * fractions['CO2'] + fractions['O'] + fractions['OH']
    bounded('element_ratio.H_C', hydrogen / carbon, 1.95 if rp1 else 4.0, 2e-8)
    of_ratio=expected_input['oxidizer_fuel_mass_ratio']
    bounded('element_ratio.O_C', oxygen / carbon, 2 * of_ratio * (13.976183 if rp1 else 16.04246) / 31.9988, 2e-8)
    diagnostics = report['diagnostics']
    if (not isinstance(diagnostics,dict) or set(diagnostics)!={'element_relative_residual','equilibrium_residual','enthalpy_residual_j_per_kg','equilibrium_iterations','hp_iterations'}
        or not isinstance(diagnostics['element_relative_residual'],list)
        or any(type(diagnostics[k]) is not int or not 0<=diagnostics[k]<=100000 for k in ('equilibrium_iterations','hp_iterations'))):
        raise ValueError('Invalid combustion diagnostics shape/counts')
    if continuous:
        from liquid_table import expected_report, reference as liquid_reference
        from liquid_table import BASIS
        tables,_ = liquid_reference()
        if expected_input['enthalpy_basis'] != BASIS:
            raise ValueError('Continuous liquid enthalpy basis mismatch')
        boundary=report['boundary']
        keys={'fuel','oxidizer','fuel_mass_fraction','oxidizer_mass_fraction',
              'inlet_mixture_h_j_per_kg','element_inventory_kmol_per_kg',
              'heat_transfer_j_per_kg','inlet_kinetic_energy_j_per_kg','shaft_work_j_per_kg'}
        if (not isinstance(boundary,dict) or set(boundary)!=keys
            or not isinstance(boundary['element_inventory_kmol_per_kg'],list)
            or len(boundary['element_inventory_kmol_per_kg'])!=3
            or any(type(boundary[k]) not in (int,float) or boundary[k]!=0 for k in
                   ('heat_transfer_j_per_kg','inlet_kinetic_energy_j_per_kg','shaft_work_j_per_kg'))):
            raise ValueError('Continuous liquid boundary schema mismatch')
        for name,fluid in (('fuel','Methane'),('oxidizer','Oxygen')):
            target=expected_report(fluid,expected_input[name+'_temperature_k'],
                                   expected_input[name+'_pressure_pa'],tables)['results']
            actual=boundary[name]
            if not isinstance(actual,dict) or set(actual)!=set(target):
                raise ValueError('Continuous liquid state shape mismatch')
            for key,value in target.items():
                same(actual[key],value,'continuous '+name+' '+key,1e-9)
        fuel=boundary['fuel']['h_j_per_kg']; oxidizer=boundary['oxidizer']['h_j_per_kg']
        same(boundary['fuel_mass_fraction'],1/(1+of_ratio),'liquid fuel fraction',1e-14)
        same(boundary['oxidizer_mass_fraction'],of_ratio/(1+of_ratio),'liquid oxidizer fraction',1e-14)
        same(boundary['inlet_mixture_h_j_per_kg'],(fuel+of_ratio*oxidizer)/(1+of_ratio),'liquid mixture h',1e-7)
        for e,element in enumerate(('C','H','O')):
            expected=[1/(16.04246*(1+of_ratio)),4/(16.04246*(1+of_ratio)),
                      2*of_ratio/(31.9988*(1+of_ratio))][e]
            same(boundary['element_inventory_kmol_per_kg'][e],expected,'liquid element '+element,1e-14)
            amount=sum(y*int(next(s for s in fits['species'] if s['id']==species)['elements'].get(element,0))
                       for species,y in fractions.items())/chamber['molar_mass_kg_per_kmol']
            same(amount,expected,'liquid product element '+element,1e-11)
        if not 100<=expected_input['pressure_pa']<=1e9 or not 0.1<=of_ratio<=20 or not 1000<=chamber['temperature_k']<=6000:
            raise ValueError('Continuous liquid product outside guards')
    elif anchor:
        if rp1:
            anchors = parse_anchors((ROOT / RAW / 'thermo.inp').read_text(encoding='ascii'))
            fuel_anchor, oxidizer_anchor = anchors[2], anchors[1]
        else:
            fuel_anchor, oxidizer_anchor = liquid_anchors()
        fuel = fuel_anchor['assigned_enthalpy_j_per_mol']*1000/fuel_anchor['molar_mass_kg_per_kmol']
        oxidizer = oxidizer_anchor['assigned_enthalpy_j_per_mol']*1000/oxidizer_anchor['molar_mass_kg_per_kmol']
        boundary = report['boundary']
        if (not isinstance(boundary,dict) or set(boundary)!={
            'fuel_h_j_per_kg','oxidizer_h_j_per_kg','inlet_mixture_h_j_per_kg',
            'heat_transfer_j_per_kg','pressure_correction_applied','element_inventory_kmol_per_kg'}
            or boundary['pressure_correction_applied'] is not False
            or type(boundary['heat_transfer_j_per_kg']) not in (int,float)
            or boundary['heat_transfer_j_per_kg']!=0
            or not isinstance(boundary['element_inventory_kmol_per_kg'],list)
            or len(boundary['element_inventory_kmol_per_kg'])!=3):
            raise ValueError('Assigned inlet boundary mismatch')
        same(boundary['fuel_h_j_per_kg'],fuel,'assigned fuel h',1e-7)
        same(boundary['oxidizer_h_j_per_kg'],oxidizer,'assigned oxidizer h',1e-7)
        same(boundary['inlet_mixture_h_j_per_kg'],(fuel+of_ratio*oxidizer)/(1+of_ratio),'assigned mixed inlet h',1e-7)
        for e, element in enumerate(('C','H','O')):
            expected = (fuel_anchor['elements'].get(element,0)/fuel_anchor['molar_mass_kg_per_kmol'] +
                        of_ratio*oxidizer_anchor['elements'].get(element,0)/oxidizer_anchor['molar_mass_kg_per_kmol'])/(1+of_ratio)
            same(boundary['element_inventory_kmol_per_kg'][e],expected,'assigned element '+element,1e-14)
            amount=sum(y*int(next(s for s in fits['species'] if s['id']==species)['elements'].get(element,0))
                       for species,y in fractions.items())/chamber['molar_mass_kg_per_kmol']
            same(amount,expected,'product inventory '+element,1e-11)
        if not 100<=expected_input['pressure_pa']<=1e9 or not 0.1<=of_ratio<=20 or not 1000<=chamber['temperature_k']<=6000:
            raise ValueError('Assigned inlet outside product guards')
        if rp1 and (expected_input['pressure_pa'] != 1e7 or not 2.2 <= of_ratio <= 4.0):
            raise ValueError('RP-1 outside method domain')
    elif explicit_h:
        fuel=expected_input['fuel_h_j_per_kg']; oxidizer=expected_input['oxidizer_h_j_per_kg']
        for species,value in [('CH4',fuel),('O2',oxidizer)]:
            bounds=[mixture({species:1.0},t,expected_input['pressure_pa'],fits)['h_j_per_kg'] for t in (200,6000)]
            if not bounds[0]-1e-7<=value<=bounds[1]+1e-7: raise ValueError('Explicit inlet h outside gas fit')
        boundary=report['boundary']
        if (not isinstance(boundary,dict) or set(boundary)!={'inlet_mixture_h_j_per_kg','heat_transfer_j_per_kg'}
            or type(boundary['heat_transfer_j_per_kg']) not in (int,float) or boundary['heat_transfer_j_per_kg'] != 0):
            raise ValueError('Explicit HP must declare zero heat transfer')
        same(boundary['inlet_mixture_h_j_per_kg'],(fuel+of_ratio*oxidizer)/(1+of_ratio),'explicit mixed inlet h',1e-7)
        if not 100<=expected_input['pressure_pa']<=1e9 or not 0.1<=of_ratio<=20 or not 1000<=chamber['temperature_k']<=6000:
            raise ValueError('Explicit inlet outside equilibrium guards')
    else:
        fuel=mixture({'CH4':1.0},expected_input['fuel_temperature_k'],expected_input['pressure_pa'],fits)['h_j_per_kg']
        oxidizer=mixture({'O2':1.0},expected_input['oxidizer_temperature_k'],expected_input['pressure_pa'],fits)['h_j_per_kg']
    same(diagnostics['enthalpy_residual_j_per_kg'],chamber['h_j_per_kg']-(fuel+of_ratio*oxidizer)/(1+of_ratio),'enthalpy residual identity',1e-5)
    if len(diagnostics['element_relative_residual']) != 3:
        raise ValueError('Element residual dimension mismatch')
    if mode in {'tp','frozen-tp'} and diagnostics['hp_iterations'] != 0:
        raise ValueError('Assigned-TP report cannot claim HP iterations')
    for i, residual in enumerate(diagnostics['element_relative_residual']):
        bounded(f'diagnostics.element[{i}]', residual, 0.0, 2e-10)
    bounded('diagnostics.equilibrium', diagnostics['equilibrium_residual'], 0.0, 1e-10)
    if mode in {'hp','frozen','hp-h','frozen-h','hp-liquid','frozen-liquid','hp-liquid-state','frozen-liquid-state','hp-rp1','frozen-rp1'}:
        bounded('diagnostics.enthalpy_j_per_kg', diagnostics['enthalpy_residual_j_per_kg'], 0.0, 0.01)
    if nozzle_mode:
        nozzle = report['nozzle']
        if (not isinstance(nozzle,dict) or set(nozzle)!={'freeze_location','throat','exit','cstar_m_per_s','vacuum_effective_velocity_m_per_s','effective_velocity_m_per_s','thrust_coefficient','continuity_relative_residual','sonic_relative_residual'}):
            raise ValueError('Invalid frozen nozzle shape')
        if nozzle['freeze_location'] != 'chamber':
            raise ValueError('Wrong freeze location')
        exit_col = 2 if area == 10 else 3
        performance_col = 1 if area == 10 else 2
        for name, col in [('throat', 1), ('exit', exit_col)]:
            station = nozzle[name]
            if not isinstance(station,dict) or set(station)!={'gas','velocity_m_per_s','mach','mass_flux_kg_per_m2_s','energy_residual_j_per_kg','entropy_residual_j_per_kg_k'}:
                raise ValueError('Invalid frozen station shape')
            gas(station['gas'])
            g=station['gas']; cp=g['cp_frozen_j_per_kg_k']; rg=g['gas_constant_j_per_kg_k']; t=g['temperature_k']
            speed=station['velocity_m_per_s']
            if type(speed) not in (int,float) or not math.isfinite(speed) or speed<=0: raise ValueError('Invalid frozen velocity')
            same(station['mach'],speed/math.sqrt(cp/(cp-rg)*rg*t),'station Mach')
            same(station['mass_flux_kg_per_m2_s'],g['pressure_pa']/(rg*t)*speed,'station mass flux')
            same(station['energy_residual_j_per_kg'],g['h_j_per_kg']+speed**2/2-chamber['h_j_per_kg'],'station energy residual identity',1e-5)
            same(station['entropy_residual_j_per_kg_k'],g['s_j_per_kg_k']-chamber['s_j_per_kg_k'],'station entropy residual identity',1e-7)
            if station['gas']['mole_fractions'] != fractions:
                raise ValueError('Frozen composition changed')
            bounded(name + '.temperature_k', station['gas']['temperature_k'], rows['temperature_k'][col], 0.03)
            bounded(name + '.pressure_pa', station['gas']['pressure_pa'], rows['pressure_bar'][col] * 1e5, 30.0 if name == 'throat' else 10.0)
            bounded(name + '.velocity_m_per_s', station['velocity_m_per_s'], rows['isp_velocity_m_s'][0 if name == 'throat' else performance_col], 0.03)
            bounded(name + '.mach', station['mach'], rows['mach'][col], 2e-4)
            bounded(name + '.energy_residual', station['energy_residual_j_per_kg'], 0.0, 1e-5)
            bounded(name + '.entropy_residual', station['entropy_residual_j_per_kg_k'], 0.0, 1e-7)
            bounded(name + '.recomputed_energy', station['gas']['h_j_per_kg'] + station['velocity_m_per_s'] ** 2 / 2 - chamber['h_j_per_kg'], 0.0, 1e-5)
        bounded('nozzle.cstar_m_per_s', nozzle['cstar_m_per_s'], rows['cstar_m_s'][performance_col], 0.03)
        bounded('nozzle.ivac_m_per_s', nozzle['vacuum_effective_velocity_m_per_s'], rows['ivac_m_s'][performance_col], 0.03)
        bounded('nozzle.continuity', nozzle['continuity_relative_residual'], 0.0, 1e-8)
        bounded('nozzle.recomputed_continuity', nozzle['exit']['mass_flux_kg_per_m2_s'] * area / nozzle['throat']['mass_flux_kg_per_m2_s'] - 1.0, 0.0, 1e-8)
        bounded('nozzle.sonic', nozzle['sonic_relative_residual'], 0.0, 1e-8)
        flux = nozzle['throat']['mass_flux_kg_per_m2_s']
        bounded('nozzle.recomputed_cstar', nozzle['cstar_m_per_s'], chamber['pressure_pa'] / flux, 1e-8)
        bounded('nozzle.recomputed_ivac', nozzle['vacuum_effective_velocity_m_per_s'], nozzle['exit']['velocity_m_per_s'] + nozzle['exit']['gas']['pressure_pa'] * area / flux, 1e-8)
        bounded('nozzle.recomputed_effective_velocity', nozzle['effective_velocity_m_per_s'], nozzle['vacuum_effective_velocity_m_per_s']-expected_input['ambient_pressure_pa']*area/flux, 1e-8)
        bounded('nozzle.recomputed_cf', nozzle['thrust_coefficient'], nozzle['effective_velocity_m_per_s'] / nozzle['cstar_m_per_s'], 1e-10)
        same(nozzle['sonic_relative_residual'],nozzle['throat']['mach']**2-1,'sonic residual identity',1e-12)
        same(nozzle['continuity_relative_residual'],nozzle['exit']['mass_flux_kg_per_m2_s']*area/flux-1,'continuity residual identity',1e-12)
        if fixed:
            geometry=report['geometry']
            keys={'throat_area_m2','exit_area_m2','mass_flow_kg_per_s','thrust_n','specific_impulse_s'}
            if (not isinstance(geometry,dict) or set(geometry)!=keys
                or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in geometry.values())):
                raise ValueError('Invalid fixed-geometry quantities')
            throat=expected_input['throat_area_m2'];flow=throat*flux
            for key,target in {'throat_area_m2':throat,'exit_area_m2':throat*area,
                               'mass_flow_kg_per_s':flow,'thrust_n':flow*nozzle['effective_velocity_m_per_s'],
                               'specific_impulse_s':nozzle['effective_velocity_m_per_s']/9.80665}.items():
                same(geometry[key],target,'geometry.'+key)
            same(geometry['thrust_n'],flow*nozzle['exit']['velocity_m_per_s']+
                 (nozzle['exit']['gas']['pressure_pa']-expected_input['ambient_pressure_pa'])*geometry['exit_area_m2'],
                 'momentum plus pressure thrust')
            if expected_input['ambient_pressure_pa']>nozzle['exit']['gas']['pressure_pa']:
                raise ValueError('Fixed-geometry output outside back-pressure domain')
            if anchor or continuous:
                # Derived from independently printed CEA c*/Ivac, not experimental thrust.
                ref_cstar=rows['cstar_m_s'][performance_col]
                ref_flow=expected_input['pressure_pa']*throat/ref_cstar
                ref_velocity=rows['ivac_m_s'][performance_col]-expected_input['ambient_pressure_pa']*area*ref_cstar/expected_input['pressure_pa']
                bounded('geometry.cea_derived_mass_flow',geometry['mass_flow_kg_per_s'],ref_flow,
                        ref_flow*0.03/(ref_cstar-0.03)+1e-8)
                bounded('geometry.cea_derived_thrust',geometry['thrust_n'],ref_flow*ref_velocity,
                        abs(ref_flow*rows['ivac_m_s'][performance_col])*0.03/(ref_cstar-0.03)+ref_flow*0.03+1e-6)
    return errors


def run_reference(binary, folder):
    folder.mkdir(parents=True, exist_ok=False)
    record = dict(schema_version=1, kind='combustion-reference', status='RUNNING', started_at=now(),
                  cases=[], scope='Gas-feed method verification; no flight-engine or equilibrium-nozzle performance claim.')
    atomic_json(folder / 'manifest.json', record)
    # Snapshot both the actual binary and the complete reference manifest.
    try:
        references = check_reference()
        cases = {case['id']: case for case in references['cases']}
        record['binary_sha256'] = digest(binary)
        record['cea_manifest_sha256'] = digest(ROOT / 'tests/reference/cea/manifest.json')
        shutil.copy2(binary, folder / binary.name)
        shutil.copy2(ROOT / 'tests/reference/cea/manifest.json', folder / 'cea-manifest.json')
        executable = folder / binary.name
        if digest(executable) != record['binary_sha256']:
            raise ValueError('Binary snapshot changed')
        specs = [('tp', None, ['3000', '10000000', '3.4', '298.15', '298.15'], 'ch4_o2_tp'),
                 ('hp', None, ['10000000', '3.4', '298.15', '298.15'], 'ch4_o2_hp'),
                 ('frozen', 10, ['10000000', '3.4', '298.15', '298.15', '10', '0'], 'ch4_o2_rocket_frozen_chamber'),
                 ('frozen', 40, ['10000000', '3.4', '298.15', '298.15', '40', '0'], 'ch4_o2_rocket_frozen_chamber')]
        for mode, area, arguments, ref_id in specs:
            case_id = mode + (str(area) if area else '')
            command = [str(executable), 'combustion', mode, *arguments]
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8', errors='strict', timeout=15, env=subprocess_env(), check=False)
            atomic_text(folder / (case_id + '-stdout.json'), completed.stdout)
            atomic_text(folder / (case_id + '-stderr.txt'), completed.stderr)
            if completed.returncode or completed.stderr:
                raise ValueError(f'{case_id}: exit={completed.returncode}, stderr={completed.stderr}')
            errors = compare_report(strict_json(completed.stdout), cases[ref_id], mode, area)
            record['cases'].append(dict(id=case_id, reference=ref_id, command=[executable.name, *command[1:]],
                                        output_sha256=digest(folder / (case_id + '-stdout.json')), comparisons=errors))
        record['status'] = 'PASS'
    except Exception as exc:
        record.update(status='FAIL', error=str(exc))
        raise
    finally:
        record['finished_at'] = now()
        atomic_json(folder / 'manifest.json', record)
    return record


def archive_reference(run_folder, archive_folder, build_path):
    """Keep a small immutable result set in Git, binaries stay in build/."""
    record = read_json(run_folder / 'manifest.json')
    if record.get('status') != 'PASS':
        raise ValueError('Cannot archive a failed reference run')
    build_manifest = read_json(build_path)
    test_report = read_json(build_path.parent / 'test-report.json')
    if build_manifest.get('status') != 'PASS' or test_report.get('status') != 'PASS' or record['binary_sha256'] != build_manifest['application']['sha256']:
        raise ValueError('Archive build/test/binary identity mismatch')
    if test_report['build_manifest_sha256'] != digest(build_path):
        raise ValueError('Archive test report refers to a different build')
    # Copy only declared result files, not the executable or arbitrary run files.
    archive_folder.mkdir(parents=True, exist_ok=False)
    record['build_manifest_sha256'] = digest(build_path)
    record['test_report_sha256'] = digest(build_path.parent / 'test-report.json')
    record['build_inputs'] = build_manifest['inputs']
    record['validation_inputs'] = test_report['validation_inputs']
    for case in record['cases']:
        filename = case['id'] + '-stdout.json'
        source = run_folder / filename
        if digest(source) != case['output_sha256']:
            raise ValueError('Result changed before archive')
        shutil.copy2(source, archive_folder / filename)
        case['output'] = filename
    shutil.copy2(run_folder / 'cea-manifest.json', archive_folder / 'cea-manifest.json')
    atomic_json(archive_folder / 'manifest.json', record)


def check_archive(folder):
    record = read_json(folder / 'manifest.json')
    if record.get('kind') != 'combustion-reference' or record.get('status') != 'PASS' or len(record['cases']) != 4:
        raise ValueError('Incomplete combustion validation archive')
    if digest(folder / 'cea-manifest.json') != record['cea_manifest_sha256']:
        raise ValueError('Archived CEA manifest changed')
    cases = {case['id']: case for case in read_json(folder / 'cea-manifest.json')['cases']}
    expected = {'tp', 'hp', 'frozen10', 'frozen40'}
    if {case['id'] for case in record['cases']} != expected:
        raise ValueError('Archive case identities changed')
    for case in record['cases']:
        filename = case['id'] + '-stdout.json'
        if case['output'] != filename or digest(folder / filename) != case['output_sha256']:
            raise ValueError('Archived C result changed')
        mode = 'frozen' if case['id'].startswith('frozen') else case['id']
        area = int(case['id'][6:]) if mode == 'frozen' else None
        errors = compare_report(strict_json((folder / filename).read_text(encoding='utf-8')), cases[case['reference']], mode, area)
        if errors != case['comparisons']:
            raise ValueError('Archived comparison changed')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', choices=['Debug', 'Release'], default='Release')
    parser.add_argument('--archive-id', help='New immutable version directory under results/validation; refuses existing paths')
    args = parser.parse_args()
    if args.archive_id and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}', args.archive_id):
        raise ValueError('Unsafe archive ID')
    build = verified_build(ROOT, args.configuration, require_tests=True)
    manifest = read_json(build)
    folder = ROOT / 'build/combustion-reference' / uuid.uuid4().hex
    record = run_reference(ROOT / manifest['application']['path'], folder)
    if args.archive_id:
        archive_reference(folder, ROOT / 'results/validation' / args.archive_id, build)
    print(f"C/CEA {record['status']}: {len(record['cases'])} runs; {folder}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(f'combustion-reference: {exc}', file=sys.stderr)
        sys.exit(1)
