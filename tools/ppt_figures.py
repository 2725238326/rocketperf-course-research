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


if __name__ == '__main__':
    chamber()
    nozzle()
    backpressure()
    print(f'Wrote 3 charts to {OUT.relative_to(ROOT)}')
