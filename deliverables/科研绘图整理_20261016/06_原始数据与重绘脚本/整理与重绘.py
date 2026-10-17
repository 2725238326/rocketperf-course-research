"""Curate presentation figures without changing sources or the slide deck."""
import csv
import hashlib
import html
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('E:/Work/火发原理')
OUT = ROOT / 'deliverables/科研绘图整理_20261016'
DATA = ROOT / 'deliverables/ppt-materials'
BLUE, ORANGE, INK, GRAY = '#24579B', '#C76A27', '#243345', '#697888'
FONT = 'C:/Windows/Fonts/msyh.ttc'
font_manager.fontManager.addfont(FONT)
plt.rcParams.update({'font.family': [font_manager.FontProperties(fname=FONT).get_name(), 'DejaVu Sans'],
    'font.size': 15, 'axes.labelsize': 16, 'axes.titlesize': 18,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.linewidth': 1,
    'axes.edgecolor': INK, 'text.color': INK, 'axes.labelcolor': INK,
    'xtick.color': INK, 'ytick.color': INK, 'axes.unicode_minus': False,
    'svg.fonttype': 'path', 'pdf.fonttype': 42, 'savefig.facecolor': 'white'})

DIRS = ['01_正文直接插入', '02_补充科研图', '03_矢量版_SVG_PDF',
        '04_架构与流程图', '05_全部表格及可编辑源', '06_原始数据与重绘脚本',
        '07_其他研究工况_勿混用']
for d in DIRS:
    (OUT / d).mkdir(parents=True, exist_ok=True)
records = []
gallery = []

def load(name):
    with (DATA / name).open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def register(path, sources, note):
    records.append({'file': path.relative_to(OUT).as_posix(),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'sources': sources, 'note': note})

def copy(src, folder, name=None, note='原文件逐字节复制'):
    dst = OUT / folder / (name or src.name)
    shutil.copy2(src, dst)
    assert src.read_bytes() == dst.read_bytes()
    register(dst, [src.relative_to(ROOT).as_posix()], note)
    return dst

def base(title, subtitle, panels=1):
    fig, ax = plt.subplots(1, panels, figsize=(12, 7.2), dpi=300)
    fig.subplots_adjust(left=.11, right=.965, bottom=.19, top=.80, wspace=.36)
    fig.text(.07, .945, title, fontsize=22, weight='bold', va='top')
    fig.text(.07, .876, subtitle, fontsize=12, color=GRAY, va='top')
    for a in ([ax] if panels == 1 else ax):
        a.set_axisbelow(True)
        a.grid(axis='y', color='#E2E7EC', lw=.7)
    return fig, ax

def save(fig, name, source, footer, main=False):
    fig.text(.07, .045, footer, fontsize=11, color=GRAY, va='bottom')
    paths=[]
    for ext in ('png', 'svg', 'pdf'):
        folder = ('01_正文直接插入' if main else '02_补充科研图') if ext == 'png' else '03_矢量版_SVG_PDF'
        p = OUT / folder / (name + '.' + ext)
        fig.savefig(p, dpi=300)
        register(p, [s if s.startswith('results/') else f'deliverables/ppt-materials/{s}' for s in source], footer)
        paths.append(p)
    gallery.append((name, paths[0]))
    plt.close(fig)

# Independent axes keep unlike units separate. Lines only connect sampled points.
rows = load('p6-chamber.csv')
x = [float(r['of']) for r in rows]
for key, name, title, ylabel, color in [
    ('cstar_m_s', 'P07_燃烧特征速度', '温度最高，不等于 c* 最高', '特征速度 c* (m/s)', BLUE),
    ('tc_k', '补充01_燃烧温度', '燃烧温度的采样峰位于 O/F＝3.7', '燃烧温度 T (K)', ORANGE)]:
    y = [float(r[key]) for r in rows]
    fig, ax = base(title, '液态 CH₄/O₂研究工况  |  Pc＝10 MPa  |  入口：CH₄ 120 K、O₂ 100 K，两路均10 MPa')
    ax.plot(x, y, color=color, lw=2.3, marker='o', ms=4.5)
    i = max(range(len(y)), key=lambda k: y[k])
    ax.scatter(x[i], y[i], s=90, facecolor='white', edgecolor=color, linewidth=2, zorder=5)
    text = f'采样峰：O/F＝{x[i]:.1f}\n{y[i]:.2f} ' + ('m/s' if key == 'cstar_m_s' else 'K')
    ax.annotate(text, (x[i], y[i]), xytext=(2.10, 1812) if key=='cstar_m_s' else (2.10, 3450),
        arrowprops={'arrowstyle':'->', 'color':color}, color=color, fontsize=14)
    if key == 'cstar_m_s':
        ax.axvline(3.7, color=ORANGE, ls='--', lw=1.4)
        ax.text(3.66, 1839, '温度采样峰\nO/F＝3.7\n3619.03 K', ha='right', va='top', color=ORANGE, fontsize=13)
        ax.set_ylim(1740, 1865)
    else:
        ax.set_ylim(2450, 3775)
    ax.set(xlabel='氧燃质量比 O/F', ylabel=ylabel, xlim=(1.98,4.03))
    save(fig, name, ['p6-chamber.csv'], '点为保存的离散计算结果，连线仅作引导；采样峰不代表连续全局最优。', key=='cstar_m_s')

rows = {r['metric']:r for r in load('p7-propellants.csv')}
pair_source = 'results/research/propellant_comparison_v1/common_2_6_A10_p0_pair-stdout.json'
pair = json.loads((ROOT/pair_source).read_text(encoding='utf-8'))
for col, fuel in [('ch4','methane'),('rp1','kerosene')]:
    for metric,key,scale in [('isp','specific_impulse_s',1),('mdot','mass_flow_kg_per_s',1),('f','thrust_n',1000)]:
        rows[metric][col] = pair[fuel]['geometry'][key]/scale
fig, axs = base('甲烷比冲更高，主要收益表现为流量减少', '固定 Pc＝10 MPa、At＝0.01 m²、ε＝10、真空、O/F＝2.6；保留两种推进剂各自入口状态', 3)
for ax, key, title in zip(axs, ['isp','mdot','f'], ['真空比冲 (s)','质量流量 (kg/s)','推力 (kN)']):
    vals = [float(rows[key][c]) for c in ['ch4','rp1']]
    bars = ax.bar([0,1], vals, color=[BLUE,'#A1B6CF'], width=.58)
    ax.set_xticks([0,1], ['液态甲烷','固定RP-1'])
    ax.set_title(title, pad=15, fontsize=15)
    ax.tick_params(axis='x', labelsize=12)
    ax.set_ylim(0,max(vals)*1.19)
    for b,v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2,v+max(vals)*.025,f'{v:.2f}',ha='center',fontsize=14)
save(fig,'补充02_推进剂三指标',[pair_source], '各子图使用独立单位，柱图从零起画；由归档完整精度计算，ΔIsp≈13.85 s、质量流量约低4.46%、甲烷推力约低0.20%。')

rows = load('p8-nozzle-vacuum.csv')
e=[float(r['epsilon']) for r in rows]; isp=[float(r['isp_s']) for r in rows]
fig,ax=base('扩大喷管，单位面积收益逐渐减小', '液态 CH₄/O₂研究工况  |  Pc＝10 MPa  |  O/F＝2.6  |  At＝0.01 m²  |  真空')
ax.plot(e,isp,'o-',color=BLUE,lw=2.3,ms=6)
for a,b in zip(e,isp):
    if a in [10,20,40]:
        ax.annotate(f'ε＝{a:g}\n{b:.2f} s',(a,b),xytext=(8,-40 if a!=40 else -48),textcoords='offset points',fontsize=13,
            ha='left' if a!=40 else 'right')
ax.set(xlabel='喷管面积比 ε＝Ae / At',ylabel='真空比冲 Isp (s)',xlim=(2,44),ylim=(295,355))
save(fig,'P09_喷管面积比与比冲',['p8-nozzle-vacuum.csv'],'离散点之间不增加计算数据；尚未计算结构质量、冷却、长度及流动分离代价。',True)

by_e={float(r['epsilon']):r for r in rows}
gains=[]
for lo,hi in [(10,20),(20,40)]:
    a,b=by_e[lo],by_e[hi]
    gains.append((float(b['isp_s'])-float(a['isp_s']))/(float(b['exit_area_m2'])-float(a['exit_area_m2'])))
fig,ax=base('后段单位出口面积收益约为前段的39%', '同一甲烷真空研究工况；单位面积收益＝ΔIsp / ΔAe')
bars=ax.bar(['面积比 10 → 20','面积比 20 → 40'],gains,color=[BLUE,'#A1B6CF'],width=.5)
ax.set_ylabel('单位出口面积的比冲增益 (s/m²)');ax.set_ylim(0,160)
for b,v in zip(bars,gains):
    ax.text(b.get_x()+b.get_width()/2,v+3,f'{v:.2f} s/m²',ha='center',fontsize=17)
save(fig,'补充03_喷管单位面积收益',['p8-nozzle-vacuum.csv'],'前段 ΔAe＝0.10 m²，后段 ΔAe＝0.20 m²；由归档CSV显示精度计算，末位可能有圆整差异。')

rows=load('backup-backpressures.csv')
fig,ax=base('背压越高，可用的附着流计算范围越窄', '液态 CH₄/O₂研究工况  |  Pc＝10 MPa  |  O/F＝2.6  |  At＝0.01 m²')
for key,label,color,style in [('isp_s_pa0','真空',BLUE,'-'),('isp_s_pa5000','5 kPa','#438F87','--'),
    ('isp_s_pa50000','50 kPa',ORANGE,'-.'),('isp_s_pa101325','海平面 101.325 kPa',INK,':')]:
    xx=[float(r['epsilon']) for r in rows]
    yy=[float(r[key]) if r[key] else float('nan') for r in rows]
    ax.plot(xx,yy,label=label,color=color,ls=style,marker='o',ms=4,lw=2)
ax.set(xlabel='喷管面积比 ε',ylabel='比冲 Isp (s)',xlim=(0,63),ylim=(260,360))
ax.legend(frameon=False,loc='lower right',fontsize=13)
save(fig,'补充04_多背压比冲曲线',['backup-backpressures.csv'],'曲线空缺表示当前模型未给出可用结果，不能补零或跨空缺连线；未预测实际分离位置。')

rows=load('p9-ambient.csv')
vac=next(r for r in rows if r['epsilon']=='10' and r['ambient_pa']=='0')
sea=next(r for r in rows if r['epsilon']=='10' and r['ambient_pa']=='101325')
fig,ax=base('同一喷管，海平面比冲比真空低约19秒', '液态 CH₄/O₂研究工况  |  Pc＝10 MPa  |  O/F＝2.6  |  At＝0.01 m²  |  ε＝10')
vals=[float(vac['isp_s']),float(sea['isp_s'])]
bars=ax.bar(['真空','海平面 101.325 kPa'],vals,color=[BLUE,'#A1B6CF'],width=.5)
ax.set(ylabel='比冲 Isp (s)',ylim=(0,375))
for b,v in zip(bars,vals):
    ax.text(b.get_x()+b.get_width()/2,v+6,f'{v:.2f} s',ha='center',fontsize=17)
save(fig,'补充05_真空与海平面比冲',['p9-ambient.csv'],'仅比较 ε＝10 的两个有效结果；ε＝40海平面工况没有可用比冲。')

fig,ax=base('面积比40：理想出口压力低于海平面背压', '液态 CH₄/O₂研究工况  |  Pc＝10 MPa  |  O/F＝2.6  |  ε＝40')
vals=[17.2398,101.325]
bars=ax.bar(['理想出口压力 pe','海平面背压 pa'],vals,color=[BLUE,ORANGE],width=.5)
ax.set(ylabel='压力 (kPa)',ylim=(0,125))
for b,v in zip(bars,vals):
    ax.text(b.get_x()+b.get_width()/2,v+2,f'{v:.2f} kPa',ha='center',fontsize=17)
save(fig,'补充06_海平面过膨胀压力',['p9-ambient.csv','p8-nozzle-vacuum.csv'],'pe＜pa提示过膨胀，需进一步考虑流动分离；此图不预测实际分离位置。')

# Keep existing approved tables as the main-slide choices.
for p in sorted((ROOT/'deliverables/表格素材').iterdir()):
    if p.suffix.lower() in ['.png','.xlsx']:
        copied=copy(p,'05_全部表格及可编辑源')
        if p.name in ['P08_推进剂对比.png','P10_背压对比.png','P11_循环对比.png']:
            dst=copy(p,'01_正文直接插入')
            gallery.append((p.stem,dst))
for p in sorted((ROOT/'deliverables/ppt-figures-package/architecture').iterdir()):
    if p.suffix in ['.svg','.png']:
        dst=copy(p,'04_架构与流程图',note='components-ppt为当前P6简图；其他旧架构图仅供参考，行数未重新核对，workflow不可解释为全部任务串行调用。')
        if p.name=='components-ppt.png':
            copy(p,'01_正文直接插入','P06_程序架构.png')
            gallery.append(('P06_程序架构',dst))
for p in sorted(DATA.glob('*.csv')):
    copy(p,'06_原始数据与重绘脚本')
copy(ROOT/pair_source,'06_原始数据与重绘脚本')
for p in ['adiabatic-inlet-response.svg','area-ratio-tradeoff.svg','propellant-comparison.svg']:
    copy(ROOT/'docs'/p,'07_其他研究工况_勿混用',note='历史研究图，保留图内工况。气态入口或给定热状态算例不能与当前液态主线数值混用。')
copy(Path(__file__),'06_原始数据与重绘脚本','整理与重绘.py',note='重绘和整理脚本；ROOT指向原工作区，复跑时使用原CSV。')

# One visual index for immediate use.
W,H=2400,430*3
sheet=Image.new('RGB',(W,H),'#EDF1F5')
draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype(FONT,23)
for i,(name,p) in enumerate(gallery):
    x0=(i%4)*600;y0=(i//4)*430
    im=Image.open(p).convert('RGBA')
    white=Image.new('RGBA',im.size,'white');white.alpha_composite(im)
    im=white.convert('RGB');im.thumbnail((580,375))
    sheet.paste(im,(x0+(600-im.width)//2,y0+15+(375-im.height)//2))
    draw.text((x0+15,y0+395),name,font=font,fill=INK)
sheet.save(OUT/'00_图表总览.jpg',quality=94)
index=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>科研绘图整理</title>',
    '<style>body{font:17px Microsoft YaHei,sans-serif;margin:35px;background:#eef2f6;color:#243345}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}article{background:white;padding:18px}img{width:100%;height:310px;object-fit:contain}a{color:#24579b}</style>',
    '<h1>科研绘图整理 · 当前15页PPT</h1><p>正文直接取用01文件夹；PNG可直接插入。新科研图为3600×2160，另附SVG与PDF。当前P8、P10、P11继续使用表格。</p><main>']
for name,p in gallery:
    rel=p.relative_to(OUT).as_posix()
    index.append(f'<article><h2>{html.escape(name)}</h2><a href="{rel}"><img src="{rel}"></a><p><a href="{rel}">打开原图</a></p></article>')
index.append('</main></html>')
(OUT/'00_打开图表总览.html').write_text('\n'.join(index),encoding='utf-8')
(OUT/'素材清单.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'00_怎么用.txt').write_text('''科研绘图整理（2026-10-16）

当前PPT直接插入：01_正文直接插入
P6：P06_程序架构.png
P7：P07_燃烧特征速度.png
P8：P08_推进剂对比.png（表格）
P9：P09_喷管面积比与比冲.png
P10：P10_背压对比.png（表格）
P11：P11_循环对比.png（表格，不按不同输入的比冲给循环排名）

插入→图片→此设备，选PNG；拖动四角等比例缩放，不截图、不横向拉伸。
表格与架构保留现有清晰原版，不通过放大像素冒充高清。
8张新科研图为白底、3600×2160 PNG（300 dpi），同名SVG/PDF在03目录。
需要在PPT缩放时优先插入SVG；PDF用于打印/排版。
SVG文字转为路径，避免换电脑缺字体；PDF嵌入字体。
02为补充图，不必全部塞入正文。P8、P10、P11保留已确定的表格。
05收齐7张原表和可编辑Excel，P13_四级段表为旧方案备选，不代表要改当前P13。
04包括当前P6简图及旧版架构备选；推荐components-ppt，旧图行数未重新核对。
07为其他历史工况原图，气态入口/给定热状态不可与主线液态工况拼接。

图中只使用保存的离散结果，不插值增加数据、不填虚构结果。
曲线连线仅作引导；采样峰不代表连续全局最优。
海平面ε40没有可用比冲，不填0；压力比较不能预测实际分离位置。
原CSV和原图来源/哈希见素材清单.json；本次不重跑核心计算，不改变模型。
未修改PPT或任何原始图片。
''',encoding='utf-8-sig')
print(json.dumps({'folder':str(OUT),'scientific_charts':8,'registered_files':len(records),'gallery':len(gallery)},ensure_ascii=False))
