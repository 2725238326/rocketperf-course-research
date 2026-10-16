"""Scientific figures from saved C outputs; no physical solver in Python."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

OUT = Path(__file__).resolve().parent
DATA = OUT.parent / "data"
BLUE, ORANGE, TEAL, RED = "#24557A", "#B85C2E", "#277F78", "#AA4141"
INK, GRAY, GRID = "#25313D", "#62717D", "#DEE4E8"
plt.rcParams.update({
    "font.family": ["Microsoft YaHei", "DejaVu Sans"], "font.size": 9,
    "axes.labelsize": 9, "axes.titlesize": 9.5, "axes.titlepad": 10,
    "axes.edgecolor": INK, "axes.labelcolor": INK, "axes.linewidth": .7,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "xtick.color": INK,
    "ytick.color": INK, "text.color": INK, "axes.unicode_minus": False,
    "svg.fonttype": "path", "svg.hashsalt": "rocketperf-report-v1", "pdf.fonttype": 42, "savefig.facecolor": "white",
    "figure.facecolor": "white", "lines.linewidth": 1.5, "lines.markersize": 3.5,
    "mathtext.fontset": "stix", "legend.fontsize": 8, "legend.frameon": False,
})
SAVED = json.loads((DATA / "saved-demo-results.json").read_text(encoding="utf-8"))
MANIFEST = []


def save(fig, stem, sources):
    for ext in ("svg", "pdf", "png"):
        metadata = {"Date": None} if ext == "svg" else ({"CreationDate": None, "ModDate": None} if ext == "pdf" else None)
        fig.savefig(OUT / f"{stem}.{ext}", dpi=450, bbox_inches="tight", pad_inches=.07, metadata=metadata)
    MANIFEST.append({"figure": stem, "sources": sources, "formats": ["svg", "pdf", "png"],
                     "png_dpi": 450, "svg_text": "outlined for portable rendering",
                     "sha256": {ext: hashlib.sha256((OUT / f"{stem}.{ext}").read_bytes()).hexdigest()
                                for ext in ("svg", "pdf", "png")}})
    plt.close(fig)


def axes(ax, grid=True):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=3, width=.7)
    if grid:
        ax.grid(axis="y", color=GRID, linewidth=.6)
    ax.set_axisbelow(True)


def note(fig, text):
    fig.text(.015, .012, text, fontsize=7.3, color=GRAY, va="bottom", linespacing=1.5)


def box(ax, x, y, w, h, text, color=BLUE, size=8):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=color, linewidth=.85))
    ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=size, linespacing=1.45)


def arrow(ax, start, end, color=GRAY):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=8,
                                linewidth=.9, color=color, shrinkA=1, shrinkB=1))


def figure_flow():
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    fig.subplots_adjust(left=.005, right=.995, top=.99, bottom=.08)
    ax.set(xlim=(0, 12), ylim=(0, 10.7)); ax.axis("off")
    box(ax, 2.4, 9.7, 7.2, .75, "命令行 / 交互菜单 → 输入解析、单位与范围校验", INK, 9)
    ax.plot([.35, 11.65], [9.25, 9.25], color=GRAY, lw=.9)
    arrow(ax, (6,9.7), (6,9.25))
    rows = [
        (7.75, "combustion", "入口焓与元素\nHP 绝热平衡", "组分冻结喷管\n喉部 → 出口", BLUE),
        (5.9, "cycle adiabatic", "泵 → 预燃室 HP\n涡轮 / 单轴闭合", "主室 HP → 冻结喷管\n外排或内部回流计账", ORANGE),
        (4.05, "run / nozzle", "给定总温、总压\n定比热理想气体", "临界流量 → 膨胀\n压力推力与比冲", TEAL),
        (2.2, "cycle（历史）", "给定主室 / 发生器\n热状态与循环输入", "轴功及两路喷管\n所需热量计账", GRAY),
        (.35, "nozzle regime", "显式选择域评估\n给定气体 / HP 状态", "理想出口压力与比值\n匹配 / 经验参考几何", INK),
    ]
    for y, name, a, b, color in rows:
        box(ax,.3,y,2.25,1.05,name,color,8)
        box(ax,3.05,y,3.55,1.05,a,color,8)
        box(ax,7.1,y,4.65,1.05,b,color,8)
        arrow(ax,(2.55,y+.525),(3.05,y+.525),color)
        arrow(ax,(6.6,y+.525),(7.1,y+.525),color)
    ax.plot([.04,.04],[.875,9.25],color=GRAY,lw=.8)
    ax.plot([.04,.35],[9.25,9.25],color=GRAY,lw=.8)
    for y,*_ in rows:
        arrow(ax,(.04,y+.525),(.3,y+.525),GRAY)
    note(fig,"各入口独立选择；研究扫描重复调用相同 C API。\n所有求解均检查残差与有限值；成功输出 JSON / 中文表格，失败保持原输出并返回诊断。")
    save(fig,"fig01_calculation_flow",["docs/architecture/report-flow.svg", "C API model contracts"])


def figure_chamber():
    records=[(float(k),v) for k,v in SAVED["chamber"].items()]
    good=[(r,v) for r,v in records if v["status"]=="ok" and r>=2]
    xx=np.array([r for r,v in good])
    fig,axs=plt.subplots(1,3,figsize=(6.5,3.05))
    fig.subplots_adjust(left=.09,right=.985,top=.85,bottom=.29,wspace=.55)
    for ax,key,label,color in zip(axs[:2],["tc","cstar"],["燃烧温度 / K","特征速度 / (m/s)"],[ORANGE,BLUE]):
        yy=np.array([v[key] for r,v in good]); i=yy.argmax()
        axes(ax); ax.plot(xx,yy,"o-",color=color,markersize=2.6)
        ax.scatter(xx[i],yy[i],s=30,facecolor="white",edgecolor=color,zorder=4)
        ax.annotate(f"{yy[i]:.1f}\nO/F={xx[i]:.1f}",(xx[i],yy[i]),xytext=(-18,-32),
                    textcoords="offset points",fontsize=7.5,ha="center",color=color,
                    arrowprops={"arrowstyle":"-","color":color,"lw":.7})
        ax.set(xlabel="质量混合比 O/F",ylabel=label,xlim=(1.95,4.05))
    axs[0].set(ylim=(2450,3750)); axs[0].set_title("(a) 温度峰值",loc="left")
    axs[1].set(ylim=(1740,1865)); axs[1].set_title("(b) 特征速度峰值",loc="left")
    ax=axs[2]; axes(ax)
    for success,marker,color,label in [(True,"o",TEAL,"未触发判据"),(False,"x",RED,"返回越域")]:
        sel=[(r,v["ac"]) for r,v in records if .5<=r<=1.5 and (v["status"]=="ok")==success]
        ax.plot([r for r,a in sel],[a for r,a in sel],linestyle="none",marker=marker,color=color,label=label,ms=4)
    ax.axhline(1,color=GRAY,ls="--",lw=.9)
    ax.text(1.5,1.08,"$a_C=1$",fontsize=8,ha="right")
    ax.annotate("0.9：1.09",(.9,1.09),xytext=(.57,1.55),fontsize=7.2,color=RED,
                arrowprops={"arrowstyle":"-","color":RED,"lw":.7})
    ax.annotate("1.0：0.883",(1,.882984),xytext=(.88,.36),fontsize=7.2,color=TEAL,
                arrowprops={"arrowstyle":"-","color":TEAL,"lw":.7})
    ax.set(xlabel="质量混合比 O/F",ylabel="石墨活度 $a_C$",xlim=(.45,1.55),ylim=(0,2.65))
    ax.set_xticks([.5,1,1.5]); ax.set_title("(c) 富燃侧模型边界",loc="left")
    ax.legend(loc="upper right",fontsize=6.7,handlelength=1,borderaxespad=.1)
    note(fig,"Pc=10 MPa；CH₄ 120 K / O₂ 100 K，入口均 10 MPa。\n(a,b) O/F=2–4 离散网格；(c) 拒绝点保留诊断活度，不连接为有效平衡曲线。")
    save(fig,"fig02_chamber_tradeoff",["saved-demo-results.json:chamber"])


def figure_propellant():
    data=json.loads((DATA/"common_2_6_A10_p0_pair-stdout.json").read_text(encoding="utf-8"))
    a,b=data["methane"],data["kerosene"]
    metrics=[("specific_impulse_s",1,"真空比冲 / s"),("mass_flow_kg_per_s",1,"质量流量 / (kg/s)"),
             ("thrust_n",.001,"推力 / kN")]
    fig,axs=plt.subplots(1,3,figsize=(6.5,2.9))
    fig.subplots_adjust(left=.08,right=.985,top=.84,bottom=.29,wspace=.42)
    for i,(ax,(key,scale,title)) in enumerate(zip(axs,metrics)):
        vals=[a["geometry"][key]*scale,b["geometry"][key]*scale]
        axes(ax); ax.bar([0,1],vals,width=.52,color=[BLUE,ORANGE])
        ax.set_xticks([0,1],["液态甲烷","固定 RP-1"]); ax.tick_params(axis="x",length=0,labelsize=7.5)
        ax.set_ylim(0,max(vals)*1.23); ax.set_title(f"({chr(97+i)}) {title}",loc="left")
        for x,v in enumerate(vals): ax.text(x,v+max(vals)*.035,f"{v:.3f}",ha="center",fontsize=8)
    note(fig,"共同 Pc=10 MPa，At=0.01 m²，ε=10，真空，O/F=2.6；柱轴从零起。\n两方法使用各自入口状态；相同质量 O/F 不等于相同当量比。")
    save(fig,"fig03_propellant_comparison",["common_2_6_A10_p0_pair-stdout.json"])


def nozzle_points(ambient=0):
    return [(e,SAVED["grid"]["ch4"][f"2.6|{e}|{ambient}"]) for e in SAVED["axes"]["area_ratios"]]


def figure_nozzle():
    points=[(e,p) for e,p in nozzle_points() if e in (4,6,8,10,20,40)]
    eps=[e for e,p in points]; isp=[p["isp"] for e,p in points]; ae=[p["ae"] for e,p in points]
    fig,axs=plt.subplots(1,2,figsize=(6.5,3.05))
    fig.subplots_adjust(left=.095,right=.98,top=.84,bottom=.27,wspace=.38)
    ax=axs[0]; axes(ax); ax.plot(eps,isp,"o-",color=BLUE)
    for e,p in points:
        if e in (10,20,40): ax.annotate(f"{p['isp']:.3f}",(e,p["isp"]),xytext=(0,7),textcoords="offset points",ha="center",fontsize=7.5)
    ax.set(xlabel="面积比 ε",ylabel="真空比冲 / s",xlim=(1,43),ylim=(295,355)); ax.set_title("(a) 计算性能",loc="left")
    ax=axs[1]; axes(ax); ax.plot(ae,isp,"s-",color=ORANGE)
    for (e,p),x in zip(points,ae):
        if e in (10,20,40): ax.annotate(f"ε={e}",(x,p["isp"]),xytext=(0,-16),textcoords="offset points",ha="center",fontsize=7.5)
    ax.set(xlabel="出口面积 / m²",ylabel="真空比冲 / s",xlim=(.01,.43),ylim=(295,355)); ax.set_title("(b) 性能与几何共同变化",loc="left")
    note(fig,"CH₄/O₂，Pc=10 MPa，O/F=2.6，At=0.01 m²，真空；CH₄ 120 K / O₂ 100 K，入口均 10 MPa。\n10→20：+13.118 s / +0.10 m²；20→40：+10.197 s / +0.20 m²。")
    save(fig,"fig04_nozzle_tradeoff",["saved-demo-results.json:grid.ch4 at O/F=2.6, pa=0"])


def figure_backpressure():
    fig,axs=plt.subplots(1,2,figsize=(6.5,3.15))
    fig.subplots_adjust(left=.095,right=.98,top=.84,bottom=.28,wspace=.38)
    styles=[(0,"真空",BLUE,"-","o"),(5000,"5 kPa",TEAL,"--","s"),
            (50000,"50 kPa",ORANGE,"-.","^"),(101325,"101.325 kPa",INK,":","D")]
    ax=axs[0]; axes(ax)
    for pa,label,color,ls,marker in styles:
        valid=[(e,p["isp"]) for e,p in nozzle_points(pa) if p["status"]=="ok"]
        ax.plot(*zip(*valid),color=color,ls=ls,marker=marker,markersize=3,label=label)
    ax.set(xlabel="面积比 ε",ylabel="比冲 / s",xlim=(0,63),ylim=(260,360)); ax.set_title("(a) 附着模型的成功结果",loc="left")
    ax.legend(loc="lower right",fontsize=7)
    ax=axs[1]; axes(ax)
    points=nozzle_points(); ax.semilogy([e for e,p in points],[p["pe"]/1000 for e,p in points],"o-",color=BLUE)
    for pa,label,color,ls,marker in styles[1:]:
        ax.axhline(pa/1000,color=color,ls=ls,lw=1)
        ax.text(61,pa/1000*1.07,label,ha="right",va="bottom",fontsize=7,color=color)
    ax.set(xlabel="面积比 ε",ylabel="理想出口压力 / kPa",xlim=(0,63),ylim=(4,1800)); ax.set_title("(b) 出口压力与背压比较",loc="left")
    ax.text(.05,.08,"pₑ < pₐ：当前附着求解拒绝",transform=ax.transAxes,fontsize=7.5,color=RED)
    note(fig,"同一 CH₄/O₂ 单室工况；仅背压与面积比变化。线连接离散计算点以辅助阅读。\n不绘制被拒绝点的比冲；拒绝表示模型越域，不能据此定位真实激波或分离。")
    save(fig,"fig05_backpressure_domain",["saved-demo-results.json:grid.ch4 at O/F=2.6"])


def figure_cycle():
    cycles = {row["case"]: row for row in SAVED["cycles"]}
    opened, staged = cycles["zq3_y1_stage1"], cycles["cz10b_first_stage1"]
    a, b = opened["balance"], staged["balance"]
    fig,axs=plt.subplots(2,1,figsize=(6.5,4.45))
    fig.subplots_adjust(left=.005,right=.995,top=.97,bottom=.12,hspace=.28)
    for ax in axs: ax.set(xlim=(0,12),ylim=(0,3)); ax.axis("off")
    ax=axs[0]
    ax.text(.15,2.75,"(a) 开式甲烷情景：外排支路离开整机",fontsize=9.5,color=BLUE)
    box(ax,.15,.95,2.1,1,f"总入口\n{opened['inputs']['total_mass_flow_kg_per_s']:.6g} kg/s",BLUE,8.5)
    box(ax,4.25,1.65,3.25,.8,f"主室 → 主喷管\n{a['main_mass_flow_kg_per_s']:.6g} kg/s",BLUE,8.5)
    box(ax,4.25,.15,3.25,.8,f"发生器 → 涡轮 → 外排\n{a['external_mass_flow_kg_per_s']:.6g} kg/s",ORANGE,8.5)
    ax.plot([2.25,3.2,3.2],[1.45,1.45,2.05],color=GRAY,lw=.9)
    ax.plot([3.2,3.2],[.55,1.45],color=GRAY,lw=.9)
    arrow(ax,(3.2,2.05),(4.25,2.05),BLUE); arrow(ax,(3.2,.55),(4.25,.55),ORANGE)
    arrow(ax,(7.5,2.05),(8.1,2.05),BLUE); arrow(ax,(7.5,.55),(8.1,.55),ORANGE)
    ax.text(8.2,2.05,f"主喷管 {a['main_thrust_n']/1000:.3f} kN",fontsize=8.5,va="center")
    ax.text(8.2,.55,f"外排轴向 {a['branch_thrust_n']/1000:.3f} kN",fontsize=8.5,va="center")
    ax=axs[1]
    ax.text(.15,2.75,"(b) 富氧补燃 RP-1 情景：涡轮排气返回主室",fontsize=9.5,color=TEAL)
    box(ax,.15,1.65,2.1,.8,f"氧化剂 {b['branch_oxidizer_mass_flow_kg_per_s']:.4f}\n支路燃料 {b['branch_fuel_mass_flow_kg_per_s']:.4f}",TEAL,8)
    box(ax,3.05,1.65,3.3,.8,f"预燃室 → 涡轮\n回流 {b['returned_mass_flow_kg_per_s']:.4f} kg/s",TEAL,8.5)
    box(ax,7.2,.95,2.25,1,f"主室 → 主喷管\n{b['main_mass_flow_kg_per_s']:.6g} kg/s",TEAL,8.5)
    box(ax,3.05,.15,3.3,.8,f"直接进入主室的新鲜燃料\n{b['main_fuel_mass_flow_kg_per_s']:.4f} kg/s",ORANGE,8)
    arrow(ax,(2.25,2.05),(3.05,2.05),TEAL)
    ax.plot([6.35,6.75,6.75],[2.05,2.05,1.45],color=TEAL,lw=.9)
    ax.plot([6.35,6.75,6.75],[.55,.55,1.45],color=ORANGE,lw=.9)
    arrow(ax,(6.75,1.45),(7.2,1.45),TEAL); arrow(ax,(9.45,1.45),(10.1,1.45),TEAL)
    ax.text(10.15,1.45,f"{b['total_thrust_n']/1000:.3f}\nkN",fontsize=8.5,va="center")
    note(fig,"流量单位均为 kg/s，箭头宽度不编码流量。开式：98.0662+1.93376≈100；补燃：74.6296+25.3704=100。\n回流是内部路径，不在总消耗上重复相加。两情景燃料、O/F 与泵压不同，图不作循环性能排名。")
    save(fig,"fig06_cycle_comparison",["saved-demo-results.json:cycles[*].balance"])


def figure_inlet():
    rows=json.loads((DATA/"inlet-response.json").read_text(encoding="utf-8"))
    base=rows[0]["result"]["geometry"]
    metrics=[("specific_impulse_s",1,"比冲变化 / s",BLUE),
             ("mass_flow_kg_per_s",1,"流量变化 / (kg/s)",TEAL),
             ("thrust_n",1,"推力变化 / N",ORANGE)]
    fig,axs=plt.subplots(1,3,figsize=(6.5,3.05))
    fig.subplots_adjust(left=.09,right=.98,top=.84,bottom=.30,wspace=.50)
    for i,(ax,(key,scale,title,color)) in enumerate(zip(axs,metrics)):
        vals=[(r["result"]["geometry"][key]-base[key])*scale for r in rows[1:]]
        axes(ax); ax.axhline(0,color=INK,lw=.8)
        ax.vlines(range(3),0,vals,color=color,lw=1.5); ax.scatter(range(3),vals,color=color,s=24,zorder=4)
        ax.set_xticks(range(3),["甲烷","氧","两路"]); ax.set_xlim(-.55,2.55)
        ax.set_title(f"({chr(97+i)}) {title}",loc="left")
        delta=max(abs(v) for v in vals)
        ax.set_ylim((-delta*1.32 if min(vals)<0 else -.04*delta),delta*1.32 if max(vals)>0 else .07*delta)
        for x,v in enumerate(vals): ax.annotate(f"{v:+.3f}",(x,v),xytext=(0,8 if v>0 else -14),textcoords="offset points",ha="center",fontsize=7.8)
        ax.set_xlabel("发生升温的入口")
    note(fig,"O/F=3.4，Pc=10 MPa，At=0.01 m²，ε=10，真空，入口压力 10 MPa。\n基线 CH₄/O₂=120/100 K；升温至 140/110 K。差值相对基线，不包含预热能耗、压降或相变。")
    save(fig,"fig07_inlet_response",["inlet-response.json"])


if __name__=="__main__":
    for draw in (figure_flow,figure_chamber,figure_propellant,figure_nozzle,figure_backpressure,figure_cycle,figure_inlet):
        draw()
    data_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.iterdir()) if p.is_file()}
    (OUT/"figure-manifest.json").write_text(json.dumps({"figures":MANIFEST,"data_sha256":data_hashes,
        "matplotlib":matplotlib.__version__},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"figures":len(MANIFEST),"directory":str(OUT)},ensure_ascii=False))
