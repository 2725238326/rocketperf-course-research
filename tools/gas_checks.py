"""NASA9 report checks only; production thermodynamics and solvers remain C17."""
import math

from projectlib import ROOT, read_json


def database(root=ROOT):
    record = read_json(root / 'data/thermo/manifest.json')
    if record['dataset_id'] != 'cea-v3.3.4-neutral-cho-n-v1':
        raise ValueError('Unsupported report-check dataset')
    return record


def mixture(fractions, temperature, pressure, record):
    """Re-evaluate saved states, not equilibrium or performance predictions."""
    if temperature <= 0 or pressure <= 0:
        raise ValueError('Nonpositive gas temperature/pressure')
    species = {s['id']: s for s in record['species']}
    cp = enthalpy = entropy = mass = 0.0
    universal = record['gas_constant_j_kmol_k']
    for name, fraction in fractions.items():
        if fraction == 0: continue
        fit = species[name]
        interval = next((r for index,r in enumerate(fit['ranges'])
                         if r['t_min_k'] <= temperature < r['t_max_k']
                         or (index == len(fit['ranges'])-1 and temperature == r['t_max_k'])), None)
        if interval is None: raise ValueError('Gas state outside NASA9 interval')
        a = interval['coefficients']; t = temperature; log_t = math.log(t)
        cp_r = a[0]/t**2 + a[1]/t + a[2] + sum(a[k]*t**(k-2) for k in range(3,7))
        h_r = -a[0]/t + a[1]*log_t + a[7] + a[2]*t + sum(a[k]*t**(k-1)/(k-1) for k in range(3,7))
        s_r = -a[0]/(2*t**2) - a[1]/t + a[2]*log_t + a[8] + sum(a[k]*t**(k-2)/(k-2) for k in range(3,7))
        mass += fraction * fit['molar_mass_kg_per_kmol']
        cp += fraction * universal * cp_r
        enthalpy += fraction * universal * h_r
        entropy += fraction * universal * (s_r - math.log(fraction))
    if mass <= 0: raise ValueError('Empty gas composition')
    gas_constant = universal / mass
    return {'cp_frozen_j_per_kg_k':cp/mass, 'h_j_per_kg':enthalpy/mass,
            's_j_per_kg_k':entropy/mass - gas_constant*math.log(pressure/record['reference_pressure_pa']),
            'gas_constant_j_per_kg_k':gas_constant}


def check_elements(fractions, of_ratio, record):
    species = {s['id']: s for s in record['species']}
    amounts = {e:sum(y*species[s]['elements'].get(e,0) for s,y in fractions.items()) for e in ('C','H','O')}
    carbon = amounts['C']
    expected = 2*of_ratio*species['CH4']['molar_mass_kg_per_kmol']/species['O2']['molar_mass_kg_per_kmol']
    if carbon <= 0 or not math.isclose(amounts['H']/carbon,4,rel_tol=2e-9,abs_tol=2e-8) or not math.isclose(amounts['O']/carbon,expected,rel_tol=2e-9,abs_tol=2e-8):
        raise ValueError('Cycle composition violates feed element inventory')
