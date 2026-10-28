"""WBASE development-side measurements; never a production solver or real-engine model."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time

from projectlib import ROOT, atomic_json, atomic_text, digest, git, now, read_json, subprocess_env

PROTOCOL = 'Work2/research/baseline-protocol-v1.md'
ARCHIVE = 'Work2/results/baseline_v1'
SPECIES = ['H2', 'O2', 'H2O', 'CO', 'CO2', 'CH4', 'H', 'O', 'OH']
IGNORED_OUTPUT = {'kernel_wall_seconds', 'kernel_cpu_seconds', 'counts'}
COUNTERS = ['tp_calls', 'temperature_solves', 'gibbs_vectors', 'equilibrium_nasa9_calls',
            'residual_jacobian_evaluations', 'newton_steps', 'linear_solves', 'line_search_trials',
            'backtrack_reductions', 'warm_attempts', 'warm_successes', 'cold_starts',
            'cold_fallbacks', 'hp_trials', 'mixture_evaluations']


def instrument(source):
    """Exact, reviewable integer-only probes; fail if the pinned implementation drifts."""
    replacements = [
        ('#define RP_EQUILIBRIUM_DIMENSION 4U', '#include "work2_baseline_counters.h"\n\n#define RP_EQUILIBRIUM_DIMENSION 4U'),
        ('    *norm = 0.0;', '    ++rp_baseline_counters.residual_jacobian_evaluations;\n    *norm = 0.0;'),
        ('    for (unsigned int col = 0U; col < RP_EQUILIBRIUM_DIMENSION; ++col) {\n        unsigned int pivot',
         '    ++rp_baseline_counters.linear_solves;\n    for (unsigned int col = 0U; col < RP_EQUILIBRIUM_DIMENSION; ++col) {\n        unsigned int pivot'),
        ('    RpStatus status = gibbs_at_temperature(temperature, gibbs, error);',
         '    ++rp_baseline_counters.temperature_solves;\n    RpStatus status = gibbs_at_temperature(temperature, gibbs, error);'),
        ('        ++*iterations;', '        ++*iterations;\n        ++rp_baseline_counters.newton_steps;'),
        ('            if (evaluate_system(trial,', '            ++rp_baseline_counters.line_search_trials;\n            if (evaluate_system(trial,'),
        ('            damping *= 0.5;', '            ++rp_baseline_counters.backtrack_reductions;\n            damping *= 0.5;'),
        ('    RpCombustionResult result = {0};', '    ++rp_baseline_counters.tp_calls;\n    RpCombustionResult result = {0};'),
        ('        warm = solve_temperature(', '        ++rp_baseline_counters.warm_attempts;\n        warm = solve_temperature('),
        ('    if (!warm) {\n        result.equilibrium_iterations = 0U;',
         '    if (warm) { ++rp_baseline_counters.warm_successes; }\n    if (!warm) {\n        ++rp_baseline_counters.cold_starts;\n        if (seed != NULL && fabs(seed->result.gas.temperature_k - temperature_k) <= RP_WARM_START_SPAN_K) { ++rp_baseline_counters.cold_fallbacks; }\n        result.equilibrium_iterations = 0U;'),
        ('    status = rp_cho_mixture_evaluate(fractions, temperature_k, pressure_pa, &result.gas, error);',
         '    ++rp_baseline_counters.mixture_evaluations;\n    status = rp_cho_mixture_evaluate(fractions, temperature_k, pressure_pa, &result.gas, error);'),
        ('        const double width = upper - lower;', '        ++rp_baseline_counters.hp_trials;\n        const double width = upper - lower;'),
        ('        RpStatus status = rp_nasa9_evaluate(species, temperature, &state, error);',
         '        ++rp_baseline_counters.equilibrium_nasa9_calls;\n        RpStatus status = rp_nasa9_evaluate(species, temperature, &state, error);'),
        ('    const RpStatus status = rp_nasa9_evaluate(&rp_graphite, temperature, &state, error);',
         '    ++rp_baseline_counters.equilibrium_nasa9_calls;\n    const RpStatus status = rp_nasa9_evaluate(&rp_graphite, temperature, &state, error);'),
        ('    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {\n        const RpNasa9Species *species',
         '    ++rp_baseline_counters.gibbs_vectors;\n    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {\n        const RpNasa9Species *species'),
    ]
    for anchor, replacement in replacements:
        if source.count(anchor) != 1:
            raise ValueError('Instrumentation anchor absent/ambiguous: ' + anchor[:70])
        source = source.replace(anchor, replacement, 1)
    return source


def logged(command, folder, name, timeout=180):
    started = time.perf_counter()
    try:
        result = subprocess.run([str(a) for a in command], cwd=ROOT, capture_output=True,
                                encoding='utf-8', errors='replace', timeout=timeout,
                                env=subprocess_env(), check=False)
    except subprocess.TimeoutExpired as exc:
        atomic_text(folder / (name + '.stdout.txt'), (exc.stdout or b'').decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else exc.stdout or '')
        atomic_text(folder / (name + '.stderr.txt'), (exc.stderr or b'').decode('utf-8', 'replace') if isinstance(exc.stderr, bytes) else exc.stderr or '')
        atomic_json(folder / (name + '.process.json'), {'command':list(map(str, command)), 'timed_out':True, 'wall_seconds':time.perf_counter()-started})
        raise
    row = {'command':list(map(str, command)), 'exit_code':result.returncode,
           'exit_code_hex':f'0x{result.returncode & 0xffffffff:08X}',
           'wall_seconds':time.perf_counter()-started, 'timed_out':False}
    atomic_text(folder / (name + '.stdout.txt'), result.stdout)
    atomic_text(folder / (name + '.stderr.txt'), result.stderr)
    atomic_json(folder / (name + '.process.json'), row)
    return result, row


def inputs():
    rows = []
    def add(identifier, mode='hp', p=1e7, ratio=3.4, temperature=3000.0, expected=0,
            category='domain', eqtol=1e-10, htol=0.01, maxeq=400, maxhp=80, lower=1000, upper=6000):
        rows.append(dict(id=identifier, mode=mode, pressure_pa=p, of_ratio=ratio, temperature_k=temperature,
                         expected_status=expected, category=category,
                         policy=dict(eqtol=eqtol, htol=htol, maxeq=maxeq, maxhp=maxhp, lower=lower, upper=upper)))
    for p in (1e5, 1e6, 1e7):
        for ratio in (2.0, 3.4, 5.0):
            for temperature in (1000, 2000, 3000, 4000, 6000):
                add(f'tp-p{p:g}-of{ratio:g}-t{temperature}', 'tp', p, ratio, temperature)
            add(f'hp-p{p:g}-of{ratio:g}', p=p, ratio=ratio)
    for p in (100, 1e9):
        for temperature in (1000, 6000):
            add(f'boundary-p{p:g}-t{temperature}', 'tp', p=p, temperature=temperature, category='boundary_probe')
    for mode in ('explicit', 'anchor', 'liquid', 'rp1', 'bisect'):
        add(mode, mode=mode, ratio=2.6 if mode == 'rp1' else 3.4)
    for ratio in (2.2, 4.0):
        add(f'rp1-of{ratio}', mode='rp1', ratio=ratio)
    add('tolerance-tight', eqtol=1e-12, htol=0.001)
    add('tolerance-loose', eqtol=1e-8, htol=1)
    add('reject-t-low', 'tp', temperature=999, expected=2, category='rejection')
    add('reject-t-high', 'tp', temperature=6000.1, expected=2, category='rejection')
    add('reject-t-nan', 'tp', temperature='nan', expected=1, category='rejection')
    add('reject-p-infinite', p='inf', expected=1, category='rejection')
    add('reject-p-low', p=99, expected=2, category='rejection')
    add('reject-p-high', p=1e9+1, expected=2, category='rejection')
    add('reject-of-low', ratio=0.09, expected=2, category='rejection')
    add('reject-no-bracket', lower=5000, expected=3, category='rejection')
    add('reject-inner-budget', maxeq=1, expected=4, category='rejection')
    add('reject-outer-budget', maxhp=1, expected=4, category='rejection')
    add('reject-carbon', ratio=0.5, expected=2, category='rejection')
    add('reject-carbon-tp', 'tp', ratio=0.5, temperature=1100, expected=2, category='rejection')
    add('reject-mixed-mass-half', 'mixed-scale', temperature=0.5, expected=1, category='rejection')
    add('reject-mixed-mass-double', 'mixed-scale', temperature=2, expected=1, category='rejection')
    add('reject-mixed-zero', 'mixed-zero', expected=1, category='rejection')
    add('reject-mixed-basis', 'mixed-basis', expected=2, category='rejection')
    add('reject-rp1-pressure', 'rp1', p=9e6, ratio=2.6, expected=2, category='rejection')
    return rows


def arguments(row, repetitions=1):
    p = row['policy']
    return [row['mode'], row['pressure_pa'], row['of_ratio'], row['temperature_k'],
            p['eqtol'], p['htol'], p['maxeq'], p['maxhp'], p['lower'], p['upper'], repetitions]


def independent_state(temperature, pressure, ratio):
    """Nine log amounts + six reaction affinities; finite-difference trust-region LS.
    No C solution/element potentials are used as a seed. Same NASA9 data, not experiment.
    """
    import numpy as np
    from scipy.optimize import least_squares
    from scipy.special import logsumexp
    from gas_checks import database, mixture
    data = database()
    fits = {s['id']:s for s in data['species']}
    atoms = np.array([[fits[s]['elements'].get(e, 0.0) for s in SPECIES] for e in ('C', 'H', 'O')])
    b = np.array([1 / (16.04246*(1+ratio)), 4 / (16.04246*(1+ratio)), 2*ratio / (31.9988*(1+ratio))])
    nu = np.array([[-1,0,0,0,0,0,2,0,0], [0,-1,0,0,0,0,0,2,0],
                   [1,.5,-1,0,0,0,0,0,0], [0,.5,0,1,-1,0,0,0,0],
                   [3,0,-1,1,0,-1,0,0,0], [0,.5,0,0,0,0,1,0,-1]])
    g = []
    for species in SPECIES:
        values = mixture({species:1.0}, temperature, data['reference_pressure_pa'], data)
        g.append((values['h_j_per_kg']/temperature-values['s_j_per_kg_k']) /
                 (data['gas_constant_j_kmol_k']/fits[species]['molar_mass_kg_per_kmol']))
    g = np.array(g)
    def residual(logn):
        balances = [logsumexp(logn[atoms[e]>0] + np.log(atoms[e, atoms[e]>0])) - math.log(b[e]) for e in range(3)]
        mu = g + logn - logsumexp(logn) + math.log(pressure/data['reference_pressure_pa'])
        return np.r_[balances, nu @ mu]
    initial = np.full(9, math.log(float(sum(b))/9))
    start = time.perf_counter()
    sol = least_squares(residual, initial, jac='3-point', method='trf', x_scale='jac',
                        ftol=1e-13, xtol=1e-13, gtol=1e-13, max_nfev=2000)
    norm = float(np.max(np.abs(residual(sol.x))))
    fractions = np.exp(sol.x-logsumexp(sol.x))
    gas = mixture(dict(zip(SPECIES, map(float, fractions))), temperature, pressure, data)
    return dict(temperature_k=temperature, pressure_pa=pressure, mole_fractions=list(map(float, fractions)),
                **gas, residual_norm=norm, success=bool(sol.success and norm<=1e-10),
                nfev=int(sol.nfev), njev=int(sol.njev), message=sol.message,
                wall_seconds=time.perf_counter()-start)


def assess_gas(row, output):
    from gas_checks import database, mixture
    data = database(); fits = {s['id']:s for s in data['species']}
    gas = output['gas']; fractions = dict(zip(SPECIES, gas['mole_fractions']))
    ratios = {e:sum(fractions[s]*fits[s]['elements'].get(e, 0) for s in SPECIES) for e in ('C', 'H', 'O')}
    expected_hc = 1.95 if row['mode']=='rp1' else 4.0
    fuel_mw = 13.976183 if row['mode']=='rp1' else 16.04246
    expected_oc = 2*row['of_ratio']*fuel_mw/31.9988
    element = max(abs(ratios['H']/ratios['C']/expected_hc-1), abs(ratios['O']/ratios['C']/expected_oc-1))
    potentials = []
    for species, x in fractions.items():
        state = mixture({species:1.0}, gas['temperature_k'], data['reference_pressure_pa'], data)
        potentials.append((state['h_j_per_kg']/gas['temperature_k']-state['s_j_per_kg_k']) /
                          (data['gas_constant_j_kmol_k']/fits[species]['molar_mass_kg_per_kmol']) +
                          math.log(x) + math.log(gas['pressure_pa']/data['reference_pressure_pa']))
    nu = [(-1,0,0,0,0,0,2,0,0),(0,-1,0,0,0,0,0,2,0),
          (1,.5,-1,0,0,0,0,0,0),(0,.5,0,1,-1,0,0,0,0),
          (3,0,-1,1,0,-1,0,0,0),(0,.5,0,0,0,0,1,0,-1)]
    affinity = max(abs(sum(a*b for a,b in zip(reaction,potentials))) for reaction in nu)
    result = dict(element_ratio_relative=element, fraction_sum_error=abs(sum(fractions.values())-1),
                  max_affinity_over_rt=affinity, positive_fractions=all(0<x<=1 for x in fractions.values()),
                  equilibrium_residual=output['equilibrium_residual'],
                  enthalpy_residual_j_per_kg=abs(output['enthalpy_residual_j_per_kg']))
    result['accepted'] = (element<=5e-9 and result['fraction_sum_error']<=1e-12 and affinity<=1e-8 and
                          result['positive_fractions'] and output['equilibrium_residual']<=row['policy']['eqtol'] and
                          (row['mode']=='tp' or result['enthalpy_residual_j_per_kg']<=row['policy']['htol']))
    return result


def execute(run_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}', run_id): raise ValueError('Unsafe RunId')
    folder = ROOT/'build/work2/baseline'/run_id
    folder.mkdir(parents=True, exist_ok=False)
    cases = inputs()
    atomic_json(folder/'inputs.json', cases)
    shutil.copy2(ROOT/PROTOCOL, folder/'protocol.md')
    modules = read_json(ROOT/'project/modules.json')['modules']
    sources = [s for m in modules if m['id'] in {'core','thermo','nozzle','cycle'} for s in m['sources']]
    from pipeline import source_records
    record = dict(schema_version=1, kind='work2-baseline', run_id=run_id, status='RUNNING', started_at=now(),
                  source_head=git(ROOT,'rev-parse','HEAD',check=True).stdout.strip(), source_inputs=source_records(ROOT),
                  protocol_sha256=digest(folder/'protocol.md'),
                  environment=dict(python=sys.version, os=platform.platform(), processor=platform.processor(),
                                   machine=platform.machine(), threads=1, precision='C double / Python float64',
                                   timing_note='Kernel wall: QueryPerformanceCounter; process CPU: GetProcessTimes user+kernel (OS timer granularity). CLI process wall includes startup. Python reference wall separately recorded.'),
                  builds=[], debug_repeats=[], cases=[], independent_references=[], timings=[], cea=[], issues=[])
    atomic_json(folder/'manifest.json', record)
    try:
        record['research_tool_inputs']=[dict(path=p,sha256=digest(ROOT/p)) for p in
            ('tools/work2_baseline.py','tools/work2_baseline_probe.c','tools/work2_baseline_counters.h')]
        compiler = shutil.which('gcc')
        if compiler is None: raise ValueError('GCC unavailable')
        version, _ = logged([compiler,'--version'],folder,'compiler',30)
        record['environment']['compiler'] = compiler
        record['environment']['compiler_version'] = version.stdout.splitlines()[0]
        flags = ['-std=c17','-Wall','-Wextra','-Wpedantic','-Werror','-Wconversion','-Wshadow',
                 '-Wstrict-prototypes','-Wmissing-prototypes','-fno-common','-Iinclude','-Isrc/thermo','-Itools']
        suffix = '.exe' if os.name=='nt' else ''
        atomic_text(folder/'equilibrium-counted.c', instrument((ROOT/'src/thermo/equilibrium.c').read_text(encoding='utf-8')))
        record['instrumentation'] = dict(original_sha256=digest(ROOT/'src/thermo/equilibrium.c'),
            counted_sha256=digest(folder/'equilibrium-counted.c'), scope='Research-only integer counters, single process; equilibrium_nasa9_calls excludes inlet/mixture/nozzle property calls.')
        plain = folder/('plain'+suffix); counted = folder/('counted'+suffix)
        for name, exe, source_list in [('plain',plain,sources),('counted',counted,[s for s in sources if s!='src/thermo/equilibrium.c']+[str(folder/'equilibrium-counted.c')])]:
            command = [compiler,*flags,'-O2','-DNDEBUG',*source_list,'tools/work2_baseline_probe.c','-lm','-o',str(exe)]
            result, process = logged(command,folder,'compile-'+name)
            if result.returncode: raise ValueError('Probe compilation failed: '+name)
            record['builds'].append(dict(id=name, sha256=digest(exe), command=process['command'], flags=flags+['-O2','-DNDEBUG']))
        for identity in ('debug-a','debug-b'):
            exe = folder/(identity+suffix)
            command = [compiler,*flags,'-O0','-g3',*sources,'tests/test_cycle.c','-lm','-o',str(exe)]
            result, process = logged(command,folder,'compile-'+identity)
            if result.returncode: raise ValueError('Debug cycle compilation failed')
            record['builds'].append(dict(id=identity, sha256=digest(exe), command=process['command'], flags=flags+['-O0','-g3']))
            for i in range(30):
                name = f'{identity}-{i+1:02d}'
                run, process = logged([exe],folder,name,120)
                match = re.search(r'cycle: (\d+) checks, (\d+) failures',run.stdout)
                process.update(build=identity, binary_sha256=digest(exe), checks=int(match[1]) if match else 0,
                               failures=int(match[2]) if match else None,
                               passed=bool(run.returncode==0 and not run.stderr and match and int(match[2])==0 and int(match[1])>0))
                record['debug_repeats'].append(process)
                if not process['passed']:
                    record['issues'].append('Debug failure: '+name)
                    debugger = shutil.which('gdb')
                    if debugger:
                        logged([debugger,'--batch','-ex','run','-ex','bt','-ex','info registers','--args',exe],folder,name+'-gdb',120)
            atomic_json(folder/'manifest.json',record)
        print('Independent Debug builds: 60 process attempts recorded',flush=True)
        for row in cases:
            values = {}
            for name, exe in [('plain',plain),('counted',counted)]:
                result, process = logged([exe,*arguments(row)],folder,row['id']+'-'+name,30)
                if result.returncode or result.stderr: raise ValueError('Probe transport failed: '+row['id'])
                values[name] = json.loads(result.stdout)
            equivalence = {k:v for k,v in values['plain'].items() if k not in IGNORED_OUTPUT} == {k:v for k,v in values['counted'].items() if k not in IGNORED_OUTPUT}
            actual = values['counted']
            checks = assess_gas(row,actual) if actual['status']==0 else {'accepted':actual['failure_output_unchanged']}
            passed = equivalence and actual['status']==row['expected_status'] and checks['accepted']
            record['cases'].append(dict(input=row, output=actual, instrumentation_equivalent=equivalence, assessment=checks, passed=passed))
            if not passed: record['issues'].append('Case assessment: '+row['id'])
        print(f'Plain/counted cases: {len(cases)} attempts each',flush=True)
        atomic_json(folder/'manifest.json',record)
        # Independent log-amount reaction-basis solve, cold uniform seed, same data.
        import scipy
        import numpy
        record['environment'].update(scipy=scipy.__version__, numpy=numpy.__version__)
        for item in record['cases']:
            row = item['input']
            if row['mode']!='tp' or row['category']!='domain': continue
            ref = independent_state(row['temperature_k'],row['pressure_pa'],row['of_ratio'])
            difference = max(abs(a-b) for a,b in zip(ref['mole_fractions'],item['output']['gas']['mole_fractions'])) if item['output']['status']==0 else None
            passed = ref['success'] and difference is not None and difference<=1e-8
            record['independent_references'].append(dict(id=row['id'],kind='TP-nine-log-amounts',reference=ref,max_fraction_absolute_difference=difference,passed=passed))
            if not passed: record['issues'].append('Independent TP reference: '+row['id'])
        from scipy.optimize import brentq
        from gas_checks import database, mixture
        data = database()
        hf = mixture({'CH4':1},298.15,1e5,data)['h_j_per_kg']; ho=mixture({'O2':1},298.15,1e5,data)['h_j_per_kg']
        for item in record['cases']:
            row=item['input']
            if row['mode']!='hp' or row['category']!='domain' or row['id'].startswith('tolerance-'): continue
            ratio=row['of_ratio']; hin=(hf+ratio*ho)/(1+ratio); history=[]
            def residual(temperature):
                ref=independent_state(temperature,row['pressure_pa'],ratio)
                history.append(dict(temperature_k=temperature,residual_norm=ref['residual_norm'],nfev=ref['nfev'],success=ref['success']))
                if not ref['success']: raise ValueError('Independent inner reference did not converge')
                return ref['h_j_per_kg']-hin
            start=time.perf_counter()
            root=brentq(residual,1000,6000,xtol=1e-8,rtol=1e-14)
            ref=independent_state(root,row['pressure_pa'],ratio)
            dt=abs(root-item['output']['gas']['temperature_k'])
            dy=max(abs(a-b) for a,b in zip(ref['mole_fractions'],item['output']['gas']['mole_fractions']))
            # Equilibrium-path enthalpy derivative, not frozen cp.
            derivative=(independent_state(root+.01,row['pressure_pa'],ratio)['h_j_per_kg']-independent_state(root-.01,row['pressure_pa'],ratio)['h_j_per_kg'])/.02
            passed=dt<=1e-4 and dy<=1e-8 and ref['success']
            record['independent_references'].append(dict(id=row['id'],kind='HP-Brent-nine-log-amounts',reference=ref,history=history,
                inlet_h_j_per_kg=hin,temperature_absolute_difference_k=dt,max_fraction_absolute_difference=dy,
                equilibrium_dh_dt_j_per_kg_k=derivative,outer_enthalpy_temperature_budget_k=.01/derivative,
                wall_seconds=time.perf_counter()-start,passed=passed))
            if not passed: record['issues'].append('Independent HP reference: '+row['id'])
        print(f'Independent references: {len(record["independent_references"])} states',flush=True)
        # Timings of unchanged C equations. Counted version is not used for claims of speed.
        timing_rows=[next(r for r in cases if r['id']=='tp-p1e+07-of3.4-t3000'),
                     next(r for r in cases if r['id']=='hp-p1e+07-of3.4'), next(r for r in cases if r['id']=='bisect')]
        for row in timing_rows:
            for repeat in range(8):
                run, process=logged([plain,*arguments(row,100)],folder,f'timing-{row["id"]}-{repeat}',120)
                out=json.loads(run.stdout)
                record['timings'].append(dict(id=row['id'],repeat=repeat,warmup=repeat==0,repetitions=100,
                    exit_code=run.returncode,output=out,process_wall_seconds=process['wall_seconds']))
                if run.returncode or out['status']!=0 or out['repetitions_completed']!=100:
                    record['issues'].append('Timing failure: '+row['id'])
        record['status']='PASS' if not record['issues'] else 'FAIL'
    except Exception as exc:
        record.update(status='FAIL',error=str(exc))
        raise
    finally:
        record['finished_at']=now()
        record['files']=[dict(path=p.relative_to(folder).as_posix(),sha256=digest(p),bytes=p.stat().st_size)
                         for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='manifest.json' and p.suffix not in {'.exe'}]
        atomic_json(folder/'manifest.json',record)
    return folder


def verify(folder, root=ROOT):
    """Stdlib-only data/semantics checks suitable for the unified quality entry."""
    folder=Path(folder); record=read_json(folder/'manifest.json')
    if record.get('kind')!='work2-baseline' or record.get('status')!='PASS': raise ValueError('Baseline archive is not PASS')
    if record['protocol_sha256']!=digest(folder/'protocol.md'): raise ValueError('Baseline protocol changed')
    files=record['files']
    if len({f['path'] for f in files})!=len(files): raise ValueError('Duplicate baseline file')
    for entry in files:
        path=(folder/entry['path']).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file() or path.stat().st_size!=entry['bytes'] or digest(path)!=entry['sha256']:
            raise ValueError('Baseline bytes changed: '+entry['path'])
    repeats=record['debug_repeats']
    if len(repeats)!=60 or {r['build'] for r in repeats}!={'debug-a','debug-b'} or any(not r['passed'] or r['exit_code']!=0 or r['checks']<=0 or r['failures']!=0 for r in repeats):
        raise ValueError('Baseline Debug process evidence incomplete')
    cases=record['cases']
    if [c['input'] for c in cases]!=read_json(folder/'inputs.json') or len({c['input']['id'] for c in cases})!=len(cases):
        raise ValueError('Baseline input/case identity mismatch')
    for item in cases:
        row=item['input']; out=item['output']
        if not item['passed'] or not item['instrumentation_equivalent'] or out['status']!=row['expected_status']:
            raise ValueError('Baseline case has an unaccepted result')
        raw=json.loads((folder/(row['id']+'-counted.stdout.txt')).read_text(encoding='utf-8'))
        plain=json.loads((folder/(row['id']+'-plain.stdout.txt')).read_text(encoding='utf-8'))
        if raw!=out or {k:v for k,v in raw.items() if k not in IGNORED_OUTPUT}!={k:v for k,v in plain.items() if k not in IGNORED_OUTPUT}:
            raise ValueError('Baseline raw result differs')
        if out['status']==0:
            if assess_gas(row,out)!=item['assessment'] or not item['assessment']['accepted']:
                raise ValueError('Baseline physical checks differ')
            counts=out['counts']
            if set(counts)!=set(COUNTERS) or any(type(v) is not int or v<0 for v in counts.values()): raise ValueError('Invalid cumulative counters')
            if counts['newton_steps']!=counts['linear_solves'] or counts['warm_successes']>counts['warm_attempts'] or counts['tp_calls']<1:
                raise ValueError('Cumulative counter relationships differ')
            if (counts['newton_steps']<out['final_equilibrium_iterations'] or
                counts['gibbs_vectors']!=counts['temperature_solves']+counts['cold_starts'] or
                counts['equilibrium_nasa9_calls']!=9*counts['gibbs_vectors']+counts['mixture_evaluations']):
                raise ValueError('Cumulative work was reset or property accounting differs')
            if row['mode']=='bisect':
                if counts['tp_calls']!=out['outer_tp_calls'] or counts['hp_trials']!=0: raise ValueError('Independent outer accounting differs')
            elif row['mode']=='tp':
                if counts['tp_calls']!=1 or counts['hp_trials']!=0: raise ValueError('TP accounting differs')
            elif counts['tp_calls']!=out['hp_iterations']+2 or counts['hp_trials']!=out['hp_iterations']:
                raise ValueError('HP endpoint/trial accounting differs')
        elif not out['failure_output_unchanged']: raise ValueError('Baseline rejected state changed output')
    refs=record['independent_references']
    if len(refs)!=54 or any(not r['passed'] or not r['reference']['success'] or r['reference']['residual_norm']>1e-10 for r in refs):
        raise ValueError('Independent baseline reference incomplete')
    return dict(cases=len(cases),debug_processes=len(repeats),independent_references=len(refs))


def archive(source):
    source=Path(source).resolve(); target=ROOT/ARCHIVE
    verify(source)
    target.mkdir(parents=True,exist_ok=False)
    record=read_json(source/'manifest.json')
    for entry in record['files']:
        destination=target/entry['path'];destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source/entry['path'],destination)
    shutil.copy2(source/'manifest.json',target/'manifest.json')
    verify(target)
    return target


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    run=sub.add_parser('execute');run.add_argument('--run-id',required=True)
    for name in ('verify','archive'):
        p=sub.add_parser(name);p.add_argument('folder')
    args=parser.parse_args()
    try:
        if args.action=='execute':
            folder=execute(args.run_id)
            if read_json(folder/'manifest.json')['status']!='PASS': raise ValueError('Baseline run failed; see '+str(folder/'manifest.json'))
            print(folder)
        elif args.action=='verify': print(json.dumps(verify(Path(args.folder)),ensure_ascii=False))
        else: print(archive(args.folder))
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        print('work2-baseline: '+str(exc),file=sys.stderr);sys.exit(1)
