"""Render ready-to-paste PPT charts from deliverables/ppt-materials CSVs.

Run tools/presentation_materials.py first. Charts use the template-5 blue and
1600x900 px so they stay sharp when stretched to half a slide.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'deliverables/ppt-materials'
OUT = DATA / 'figures'
BLUE, INK, GREY = '#1f4e9c', '#1a1a1a', '#8a94a6'

font = Path('C:/Windows/Fonts/msyh.ttc')
if font.exists():
    font_manager.fontManager.addfont(str(font))
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams.update({'font.size': 20, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': INK, 'axes.linewidth': 1.4, 'axes.unicode_minus': False})


def rows(name):
    with open(DATA / name, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def figure():
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=200)
    ax.grid(axis='y', color='#dde3ec', linewidth=1)
    return fig, ax


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / name, transparent=True)
    plt.close(fig)


def chamber():
    data = rows('p6-chamber.csv')
    of = [float(r['of']) for r in data]
    cstar = [float(r['cstar_m_s']) for r in data]
    fig, ax = figure()
    ax.plot(of, cstar, color=BLUE, linewidth=3, marker='o', markersize=5)
    peak = max(range(len(of)), key=cstar.__getitem__)
    ax.plot(of[peak], cstar[peak], 'o', color=BLUE, markersize=12)
    ax.annotate(f'c*峰  O/F {of[peak]:.1f}\n{cstar[peak]:.2f} m/s', (of[peak], cstar[peak]),
                xytext=(of[peak] - 0.3, cstar[peak] - 50), color=BLUE, fontweight='bold')
    hot = max(data, key=lambda r: float(r['tc_k']))
    x = float(hot['of'])
    ax.axvline(x, color=GREY, linestyle='--', linewidth=1.5)
    ax.text(x + 0.05, max(cstar) - 2, f'温度峰\nO/F {x:.1f}\n{float(hot["tc_k"]):.0f} K',
            color=GREY, va='top')
    ax.set_xlabel('混合比 O/F')
    ax.set_ylabel('特征速度 c* (m/s)')
    save(fig, 'p6-cstar.png')


def nozzle():
    data = rows('p8-nozzle-vacuum.csv')
    eps = [float(r['epsilon']) for r in data]
    isp = [float(r['isp_s']) for r in data]
    fig, ax = figure()
    ax.plot(eps, isp, color=BLUE, linewidth=3, marker='o', markersize=6)
    for e, v in zip(eps, isp):
        if e in (10, 20, 40):
            ax.plot(e, v, 'o', color=BLUE, markersize=12)
            ax.annotate(f'ε={e:.0f}\n{v:.2f} s', (e, v), xytext=(e + 1, v - 9), color=INK)
    ax.set_xlabel('面积比 ε')
    ax.set_ylabel('真空比冲 Isp (s)')
    save(fig, 'p8-isp-epsilon.png')


def backpressure():
    data = rows('backup-backpressures.csv')
    eps = [float(r['epsilon']) for r in data]
    labels = {'isp_s_pa0': '真空', 'isp_s_pa5000': '5 kPa', 'isp_s_pa50000': '50 kPa',
              'isp_s_pa101325': '海平面 101.3 kPa'}
    colors = [BLUE, '#4f7cc4', '#8aa7d8', INK]
    fig, ax = figure()
    for (key, label), color in zip(labels.items(), colors):
        pts = [(e, float(r[key])) for e, r in zip(eps, data) if r[key]]
        ax.plot(*zip(*pts), color=color, linewidth=2.6, marker='o', markersize=4, label=label)
    ax.set_xlabel('面积比 ε（空缺处为附着模型拒算）')
    ax.set_ylabel('比冲 Isp (s)')
    ax.legend(frameon=False, fontsize=16, loc='lower right')
    save(fig, 'p17-backpressure.png')


def propellants():
    data = rows('p7-propellants.csv')
    metrics = [('isp', '真空比冲 Isp (s)'), ('cstar', '特征速度 c* (m/s)')]
    rows_i = [i for i, r in enumerate(data) if r['metric'] in ('isp', 'cstar')]
    labels = ['Isp (s)', 'c* (m/s)']
    ch4 = [float(data[i]['ch4']) for i in rows_i]
    rp1 = [float(data[i]['rp1']) for i in rows_i]
    fig, ax = figure()
    x = range(len(rows_i))
    w = 0.36
    b1 = ax.bar([i - w / 2 for i in x], ch4, w, color=BLUE, label='液态甲烷 CH4')
    b2 = ax.bar([i + w / 2 for i in x], rp1, w, color='#8aa7d8', label='RP-1（指定温度）')
    for bars in (b1, b2):
        for rect in bars:
            ax.annotate(f'{rect.get_height():.1f}', (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                        xytext=(0, 4), textcoords='offset points', ha='center', fontsize=16, color=INK)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.legend(frameon=False, fontsize=16, loc='upper right')
    ax.text(0.98, 0.55, '同喉面积 ε10 真空\nIsp 差 +13.85 s', transform=ax.transAxes,
            ha='right', fontsize=17, color=BLUE, fontweight='bold')
    save(fig, 'p7-propellants.png')


def cycle():
    data = {r['metric']: r for r in rows('p10-cycle.csv')}
    metrics = [('total_thrust_n', '推力 (kN)', '推力 F'),
               ('engine_specific_impulse_s', '比冲 (s)', '整机 Isp')]
    gg = [float(data[m]['gg']) for m, _, _ in metrics]
    orsc = [float(data[m]['orsc']) for m, _, _ in metrics]
    fig, ax = figure()
    x = range(len(metrics))
    w = 0.36
    b1 = ax.bar([i - w / 2 for i in x], gg, w, color='#8aa7d8', label='GG 开式外排')
    b2 = ax.bar([i + w / 2 for i in x], orsc, w, color=BLUE, label='ORSC 富氧补燃')
    for bars in (b1, b2):
        for rect in bars:
            ax.annotate(f'{rect.get_height():.1f}', (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                        xytext=(0, 4), textcoords='offset points', ha='center', fontsize=16, color=INK)
    ax.set_xticks(list(x))
    ax.set_xticklabels([label for _, _, label in metrics])
    ax.legend(frameon=False, fontsize=16, loc='upper right')
    ax.text(0.98, 0.55, '轴功闭合后残差\n质量 |元素|焓 |轴功 全核对', transform=ax.transAxes,
            ha='right', fontsize=16, color=GREY)
    save(fig, 'p10-cycle.png')


def ambient():
    data = rows('p9-ambient.csv')
    fig, ax = figure()
    eps = sorted({r['epsilon'] for r in data if r['status'] == 'ok'})
    def val(e, pa):
        m = [r for r in data if r['epsilon'] == e and r['ambient_pa'] == pa and r['status'] == 'ok']
        return float(m[0]['isp_s']) if m else None
    vac = [val(e, '0') for e in eps]
    sl = [val(e, '101325') for e in eps]
    x = list(range(len(eps)))
    w = 0.36
    for i, (v, s) in enumerate(zip(vac, sl)):
        if v is not None:
            r1 = ax.bar(i - w / 2, v, w, color=BLUE, label='真空' if i == 0 else None)
            ax.annotate(f'{v:.1f}', (i - w / 2, v), xytext=(0, 4), textcoords='offset points',
                        ha='center', fontsize=16, color=INK)
        if s is not None:
            r2 = ax.bar(i + w / 2, s, w, color='#8aa7d8', label='海平面 101.3 kPa' if i == 0 else None)
            ax.annotate(f'{s:.1f}', (i + w / 2, s), xytext=(0, 4), textcoords='offset points',
                        ha='center', fontsize=16, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([f'ε{e}' for e in eps])
    ax.set_ylabel('比冲 Isp (s)')
    ax.legend(frameon=False, fontsize=16, loc='upper right')
    ax.text(0.02, 0.55, 'ε40 海平面过膨胀\n模型拒算，不填假值', transform=ax.transAxes,
            fontsize=16, color=GREY)
    save(fig, 'p9-ambient.png')


if __name__ == '__main__':
    chamber()
    nozzle()
    backpressure()
    propellants()
    cycle()
    ambient()
    print(f'Wrote 6 charts to {OUT.relative_to(ROOT)}')
