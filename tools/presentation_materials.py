"""Export C-derived chart/table data for students assembling their own PPT.

Does not create or modify any PowerPoint file. Reproduction of the source data is
checked separately with tools/demo_data.py --check.
"""
import csv
import hashlib
import io
import json
from pathlib import Path

import demo_page

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables/ppt-materials'


def export():
    page_bytes = demo_page.PAGE.read_bytes()
    data = json.loads(demo_page.DATA.search(page_bytes.decode('utf-8')).group(1))
    OUT.mkdir(parents=True, exist_ok=True)
    records = []

    def save(name, rows):
        buffer = io.StringIO(newline='')
        writer = csv.writer(buffer, lineterminator='\n')
        writer.writerows(rows)
        content = buffer.getvalue().encode('utf-8-sig')
        (OUT / name).write_bytes(content)
        records.append({'file': name, 'data_rows': len(rows)-1,
                        'sha256': hashlib.sha256(content).hexdigest()})

    def g(e, pa=0, fuel='ch4'):
        return data['grid'][fuel][f'2.6|{e}|{pa}']

    save('p5-chamber.csv', [['of','tc_k','cstar_m_s','graphite_activity']] + [
        [v, data['chamber'][f'{v:.1f}']['tc'], data['chamber'][f'{v:.1f}']['cstar'], data['chamber'][f'{v:.1f}']['ac']]
        for v in data['axes']['ch4_of']])
    save('p6-propellants.csv', [['metric','unit','ch4','rp1']] + [
        [key, unit, g(10)[key]/scale, g(10,fuel='rp1')[key]/scale]
        for key, unit, scale in [('isp','s',1),('mdot','kg/s',1),('f','kN',1000),('cstar','m/s',1),('cf','1',1)]])
    save('p7-nozzle-vacuum.csv', [['epsilon','isp_s','exit_area_m2','exit_pressure_pa']] + [
        [e,g(e)['isp'],g(e)['ae'],g(e)['pe']] for e in [4,6,8,10,20,40]])
    save('p8-ambient.csv', [['epsilon','ambient_pa','status','isp_s','exit_pressure_pa']] + [
        [e,pa,g(e,pa)['status'],g(e,pa).get('isp',''),g(e,pa).get('pe','')]
        for e,pa in [(10,0),(10,101325),(40,0),(40,101325)]])
    gg, sc = data['cycles']
    save('p9-cycle.csv', [
        ['metric','unit','gg','orsc'],
        ['fuel_identity','text','methane_liquid_table','rp1_assigned'],
        ['total_mass_flow','kg/s',gg['inputs']['total_mass_flow_kg_per_s'],sc['inputs']['total_mass_flow_kg_per_s']],
        ['overall_of','1',gg['inputs']['overall_oxidizer_fuel_ratio'],sc['inputs']['overall_oxidizer_fuel_ratio']],
        ['preburner_of','1',gg['inputs']['preburner_oxidizer_fuel_ratio'],sc['inputs']['preburner_oxidizer_fuel_ratio']],
        ['pump_outlet_pressure','MPa',gg['inputs']['fuel_pump_outlet_pressure_pa']/1e6,sc['inputs']['fuel_pump_outlet_pressure_pa']/1e6],
        ['preburner_pressure','MPa',gg['inputs']['preburner_pressure_pa']/1e6,sc['inputs']['preburner_pressure_pa']/1e6],
        ['turbine_outlet_pressure','MPa',gg['turbine']['out_pa']/1e6,sc['turbine']['out_pa']/1e6],
        ['turbine_pressure_role','text','given','solved'],
        ['turbine_pressure_iterations','count',gg['turbine_pressure_iterations'],sc['turbine_pressure_iterations']],
    ] + [[key,unit,gg['balance'][key]/scale,sc['balance'][key]/scale] for key,unit,scale in [
        ('external_mass_flow_kg_per_s','kg/s',1),('returned_mass_flow_kg_per_s','kg/s',1),('main_mass_flow_kg_per_s','kg/s',1),
        ('pump_power_w','MW',1e6),('total_thrust_n','kN',1000),('engine_specific_impulse_s','s',1),
        ('mass_relative_residual','1',1),('shaft_residual_w','W',1),('energy_residual_w','W',1)]] + [
        ['maximum_element_relative_residual','1',max(map(abs,gg['element_residual'])),max(map(abs,sc['element_residual']))]])
    save('backup-backpressures.csv', [['epsilon']+[f'isp_s_pa{pa}' for pa in data['axes']['ambients_pa']]] + [
        [e]+[g(e,pa).get('isp','') if g(e,pa)['status']=='ok' else '' for pa in data['axes']['ambients_pa']]
        for e in data['axes']['area_ratios']])
    manifest = {'source':'deliverables/demo/index.html', 'source_sha256':hashlib.sha256(page_bytes).hexdigest(),
                'claim_boundary':'Saved C output, not measured vehicle performance; export only, no PPT created.',
                'refused_points':'Empty cells, never zero or extrapolated performance.', 'files':records}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Exported {len(records)} data files for manual PPT assembly; no PPT written.')


if __name__ == '__main__':
    export()
