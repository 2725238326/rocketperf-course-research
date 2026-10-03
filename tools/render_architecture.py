"""Deterministic, editable SVG/Mermaid/offline HTML architecture views."""
from html import escape
import json
from projectlib import ROOT, atomic_text, read_json

INK="#15263c"; MUTED="#52667c"; BLUE="#2261bd"; GREEN="#087f78"; LINE="#bdcad8"; BG="#f6f8fb"


def text(x,y,value,size=20,color=INK,weight=400,anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>'


def node(x,y,w,title,body,footer="",state="implemented",h=132):
    color=BLUE if state=="implemented" else MUTED
    fill="#ffffff" if state=="implemented" else "#eef2f6"
    dash=' stroke-dasharray="7 5"' if state=="planned" else ""
    result=f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{color}" stroke-width="1.5"{dash}/>'
    result+=f'<rect x="{x+1}" y="{y+18}" width="4" height="34" fill="{color}"/>'
    result+=text(x+20,y+38,title,23,INK,650)
    for i,line in enumerate(body): result+=text(x+20,y+70+i*24,line,18,MUTED)
    if footer: result+=text(x+20,y+h-17,footer,14,color,600)
    return result+'</g>'


def arrow(points,label=None,label_x=0,label_y=0,dashed=False):
    p=" ".join(f"{x},{y}" for x,y in points)
    dash=' stroke-dasharray="6 5"' if dashed else ""
    out=f'<polyline points="{p}" fill="none" stroke="{MUTED if dashed else BLUE}" stroke-width="2" stroke-linejoin="round" marker-end="url(#arrow)"{dash}/>'
    if label: out+=text(label_x,label_y,label,16,MUTED,anchor="middle")
    return out


def frame(number,title,subtitle,height,body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1680" height="{height}" viewBox="0 0 1680 {height}" role="img" aria-labelledby="title-{number} desc-{number}">'
            f'<title id="title-{number}">{escape(title)}</title><desc id="desc-{number}">{escape(subtitle)}</desc>'
            f'<defs><marker id="arrow-{number}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#52667c"/></marker></defs>'
            '<g font-family="Microsoft YaHei,Noto Sans CJK SC,Arial,sans-serif">'
            f'<rect width="1680" height="{height}" fill="{BG}"/>'
            +text(60,58,f"ROCKETPERF  /  ARCHITECTURE {number}",16,BLUE,650)
            +text(60,111,title,36,INK,700)+text(60,150,subtitle,20,MUTED)
            +f'<line x1="60" y1="183" x2="1620" y2="183" stroke="{LINE}"/>'
            +body.replace('url(#arrow)',f'url(#arrow-{number})')+f'<line x1="60" y1="{height-64}" x2="1620" y2="{height-64}" stroke="{LINE}"/>'
            +text(60,height-30,"输入来源、计算条件与验证记录分别保留",16,MUTED)
            +text(1620,height-30,"SVG / Mermaid 可编辑源 · 由项目登记生成",15,MUTED,anchor="end")+'</g></svg>\n')


def business():
    body=""
    steps=[("研究问题",["对象、级段、比较条件"],"课程要求 → 研究契约"),
           ("证据与参数",["版本、单位、系统边界"],"已积累资料 · 继续核验"),
           ("模型与算例",["假设、输入、独立基准"],"气相方法基准已固定"),
           ("C17 计算",["纯核心、显式状态"],"燃烧 / 喷管 / 外排支路"),
           ("验证与研究",["误差、敏感性、改进"],"基础验证已有 · 研究待深化"),
           ("可复现交付",["程序、报告、展示"],"最终课程成果待完成")]
    for i,(title,lines,footer) in enumerate(steps):
        body+=node(60+i*264,252,240,title,lines,footer)
        if i<5: body+=arrow([(300+i*264,310),(324+i*264,310)])
    body+=arrow([(1236,384),(1236,440),(444,440),(444,384)],"证据不足 / 误差未解释：回到参数和模型",840,429,True)
    body+=text(60,509,"三类资料始终分开",22,INK,650)
    for x,heading,detail in [(60,"事实","原文、日期、子型与工况"),(600,"假设 / 派生量","过程可解释，不冒充实测"),(1140,"计算结果","关联输入、代码与验证记录")]:
        body+=text(x,555,heading,21,GREEN,650)+text(x,589,detail,19,MUTED)
    return frame("01","业务流程：从证据到研究结论","核心目标是回答性能与改进问题。软件、文献和图表共同支撑同一条证据链。",710,body)


def components(modules):
    m={x['id']:x for x in modules}
    body=node(60,230,310,m['cli']['name'],["run / thermo / combustion","cycle prescribed"],"src/cli · 用例入口",h=145)
    body+=node(470,230,430,m['adapters']['name'],["闭合INI / JSON / UTF-8路径"],"src/adapters · 成功求解后才输出",h=145)
    body+=node(470,510,430,m['cycle']['name'],["液泵 → 轴功率 → 外排支路","主 / 支推力与所需热交换"],"prototype · 给定热状态，拒绝回流",state=m['cycle']['state'],h=165)
    body+=node(1160,230,460,m['thermo']['name'],["NASA9 → TP / HP燃烧室"],"九种C/H/O理想气体 · cp / h / s",h=145)
    body+=node(1160,510,460,m['nozzle']['name'],["定比热基线 / 温变冻结喷管","连续 / 能量 / 熵 / 声速残差"],"主喷管与支路复用相同核心",h=165)
    body+=node(650,870,430,m['core']['name'],["夹逼求根 / 状态码 / 显式失败"],"所有计算模块允许依赖的公共基础",h=120)
    body+=arrow([(370,280),(470,280)],"文件流程",420,266)
    body+=arrow([(685,375),(685,510)],"循环用例",751,450)
    body+=arrow([(900,570),(1020,570),(1020,300),(1160,300)],"发生器 / 主室TP",1030,423)
    body+=arrow([(900,625),(1160,625)],"两路喷管",1030,611)
    body+=arrow([(1390,510),(1390,375)],"组分 / 物性",1479,450)
    body+=arrow([(215,375),(215,450),(970,450),(970,250),(1160,250)],"thermo / combustion 直接用例",570,435)
    body+=arrow([(150,375),(150,745),(1480,745),(1480,675)],"定比热 / 冻结喷管直接用例",1240,733)
    body+=arrow([(685,675),(685,870)],"core",723,791,True)
    body+=arrow([(1160,330),(1110,330),(1110,930),(1080,930)],"core",1140,812,True)
    body+=arrow([(1390,675),(1390,930),(1080,930)],"core",1220,916,True)
    body+=arrow([(540,375),(400,375),(400,930),(650,930)],"值类型 / 状态契约",495,916,True)
    body+=text(60,1035,"纯计算核心无I/O；失败保持输出。热量是维持给定状态所需的交换，不是燃烧预测。",20,GREEN,650)
    body+=text(60,1070,"为避免连线遮挡：CLI → core，adapters → nozzle / thermo 的公共依赖在Mermaid中完整列出。",18,MUTED)
    return frame("02","功能核心：支路功率与两路喷管如何连接","实线为主要用例 / 求解；虚线为公共基础依赖。灰色为受限循环原型，不代表补燃已实现。",1180,body)


def workflow():
    body=""
    for x,title,lines,footer in [(60,"READY",["契约与前置满足"],"可领取，不等于已开工"),
                               (388,"ACTIVE",["负责人明确，控制在制数"],"执行、产物、失败记录"),
                               (716,"REVIEW",["产物齐备，质量证据通过"],"提交待验收，不冒充人审"),
                               (1044,"DONE",["证据指纹仍与输入一致"],"完成后解锁后续依赖"),
                               (1372,"Git 检查点",["审查暂存区、本地提交"],"无授权不推送远端")]:
        body+=node(x,250,248,title,lines,footer)
    for x in (308,636,964,1292): body+=arrow([(x,310),(x+80,310)])
    body+=arrow([(840,382),(840,437),(512,437),(512,382)],"验收不通过：继续实现",676,425,True)
    body+=text(60,490,"支撑机制",22,INK,650)
    body+=node(60,530,450,"单一状态来源",["project/tasks.json + 事件链"],"自动生成任务板和 worknow",h=144)
    body+=node(600,530,470,"质量与运行证据",["文档 / 边界 / 测试 / 哈希 / 失败语义"],"过期报告不能提交为当前验收",h=144)
    body+=node(1160,530,460,"阻塞与交接",["BLOCKED：写清原因与解除条件","解除后重新检查依赖"],"移交负责人留事件，不直接改 Markdown",h=144)
    body+=text(60,744,"人员交接：版本固定 → 包内成功/失败演示 → 接手者复跑 → 明确维护/研究/讲解责任",21,INK,650)
    body+=text(60,782,"交接包保留源码、已测程序和哈希；接收记录只证明软件复验，不代替科学结论审查。",18,MUTED)
    return frame("03","任务流程：执行、检查、本地提交与交接","状态变更通过命令完成；测试记录证明软件检查，研究结论仍需按来源和模型审核。",880,body)


def expected_architecture(root):
    modules=read_json(root/"project/modules.json")["modules"]
    visible={'cli','adapters','nozzle','core','thermo','cycle'}
    drawn={('cli','adapters'),('cli','nozzle'),('cli','core'),('cli','thermo'),('cli','cycle'),
           ('adapters','core'),('adapters','nozzle'),('adapters','thermo'),('adapters','cycle'),
           ('nozzle','core'),('nozzle','thermo'),('thermo','core'),('cycle','core'),('cycle','nozzle'),('cycle','thermo')}
    actual={(m['id'],dep) for m in modules if m['id'] in visible for dep in m['allowed_dependencies']}
    if actual != drawn: raise ValueError('Module dependencies changed: update and visually verify the SVG layout')
    diagrams={"business":business(),"components":components(modules),"workflow":workflow()}
    mermaid={
        "business":"flowchart LR\n  Q[研究问题] --> E[证据与参数]\n  E --> M[模型与算例]\n  M --> C[C17计算]\n  C --> V[验证与研究]\n  V --> D[可复现交付]\n  V -. 证据或误差未解决 .-> E\n",
        "workflow":"flowchart LR\n  R[READY] -->|领取与依赖检查| A[ACTIVE]\n  A -->|产物和质量证据| V[REVIEW]\n  V -->|新鲜指纹验收| D[DONE]\n  V -. 继续实现 .-> A\n  A -->|记录原因| B[BLOCKED]\n  B -->|依赖重检| R\n  D --> G[Git审查与本地提交]\n  G --> P[固定版本交接包]\n  P --> T[接手者复跑成功与失败]\n  T --> O[明确维护/研究/讲解责任]\n",
        "components":"flowchart TD\n"+"".join(f"  {m['id']}[{m['name']} · {m['state']}]\n" for m in modules)+"".join(f"  {m['id']} --> {d}\n" for m in modules for d in m['allowed_dependencies'])
    }
    outputs={f"docs/architecture/{name}.svg":svg for name,svg in diagrams.items()}
    outputs.update({f"docs/architecture/{name}.mmd":code for name,code in mermaid.items()})
    sections="".join(f'<section id="{name}" class="view {"selected" if i==0 else ""}">{svg}</section>' for i,(name,svg) in enumerate(diagrams.items()))
    contracts="".join(f'<tr><td>{escape(m["name"])}</td><td>{escape(m["owner_role"])}</td><td>{escape(m["contract"])}</td><td>{"已实现" if m["state"]=="implemented" else "部分实现" if m["state"]=="prototype" else "计划中"}</td></tr>' for m in modules)
    outputs["docs/architecture/index.html"]='''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rocketperf · 架构与维护</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#edf2f7;color:#15263c;font-family:"Microsoft YaHei",Arial,sans-serif}header{padding:30px 4vw 20px;background:white;border-bottom:1px solid #ccd7e3}header p{color:#52667c;max-width:900px;line-height:1.65}h1{font-size:29px;margin:0}nav{display:flex;gap:10px;flex-wrap:wrap}button{padding:11px 22px;border:1px solid #bdcad8;border-radius:5px;color:#15263c;background:white;font-size:16px;cursor:pointer}button[aria-selected=true]{background:#2261bd;color:white;border-color:#2261bd}main{max-width:1760px;margin:auto;padding:24px}.view{display:none;background:#f6f8fb;border:1px solid #dce3eb}.view.selected{display:block}svg{width:100%;height:auto;display:block}aside{padding:28px 20px;background:white;margin-top:24px}h2{font-size:22px}table{border-collapse:collapse;width:100%;line-height:1.7;font-size:15px}td,th{padding:13px;text-align:left;border-bottom:1px solid #dce3eb;vertical-align:top}th{color:#52667c}footer{padding:22px 4vw;color:#52667c;font-size:14px}@media print{header nav{display:none}.view{display:block;break-after:page}aside{break-before:page}main{padding:0}}@media(max-width:700px){main{padding:8px}aside{overflow:auto}header{padding:20px}h1{font-size:24px}}
</style>
<header><h1>Rocketperf · 项目架构</h1><p>按业务、计算和执行三个视角理解系统。教学基线、气相模型与给定热状态的外排循环分别标明；任务实时状态由项目登记维护。</p><nav role="tablist" aria-label="架构视图"><button data-view="business" aria-selected="true">01 业务流程</button><button data-view="components" aria-selected="false">02 功能核心</button><button data-view="workflow" aria-selected="false">03 任务流程</button></nav></header>
<main>'''+sections+'''<aside><h2>模块维护契约</h2><table><thead><tr><th>模块</th><th>维护职责</th><th>边界</th><th>实现状态</th></tr></thead><tbody>'''+contracts+'''</tbody></table></aside></main><footer>离线可用，无CDN或网络请求。生成源：project/modules.json + tools/render_architecture.py；SVG与Mermaid源同目录保留。</footer>
<script>document.querySelectorAll('button[data-view]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('button[data-view]').forEach(x=>x.setAttribute('aria-selected',String(x===b)));document.querySelectorAll('.view').forEach(s=>s.classList.toggle('selected',s.id===b.dataset.view));}));</script></html>
'''
    return outputs


if __name__=="__main__":
    for relative,content in expected_architecture(ROOT).items(): atomic_text(ROOT/relative,content)
    print("Rendered 3 SVG, 3 Mermaid sources and offline HTML architecture browser")
