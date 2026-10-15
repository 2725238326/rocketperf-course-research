"""Deterministic, editable SVG/Mermaid/offline HTML architecture views."""
from html import escape
import json
from assignment_diagram import assignment, MERMAID as ASSIGNMENT_MERMAID
from architecture_views import business, components, workflow
from projectlib import ROOT, atomic_text, read_json



def expected_architecture(root):
    modules=read_json(root/"project/modules.json")["modules"]
    visible={'cli','adapters','nozzle','core','thermo','cycle'}
    drawn={('cli','adapters'),('cli','nozzle'),('cli','core'),('cli','thermo'),('cli','cycle'),
           ('adapters','core'),('adapters','nozzle'),('adapters','thermo'),('adapters','cycle'),
           ('nozzle','core'),('nozzle','thermo'),('thermo','core'),('cycle','core'),('cycle','nozzle'),('cycle','thermo')}
    actual={(m['id'],dep) for m in modules if m['id'] in visible for dep in m['allowed_dependencies']}
    if actual != drawn: raise ValueError('Module dependencies changed: update and visually verify the SVG layout')
    diagrams={"assignment":assignment(),"business":business(),"components":components(modules),"workflow":workflow()}
    mermaid={
        "assignment":ASSIGNMENT_MERMAID,
        "business":"flowchart TD\n  A1[单点性能求解] --> T[thermo] & N[nozzle] & C[cycle]\n  A2[域评估 regime] --> N & T\n  A3[参数研究 study] --> N & T & C\n  C --> N --> T\n  C --> T\n  T & N & C -.-> F[数值核心 · 物性数据 · 错误契约]\n",
        "workflow":"flowchart LR\n  S1[用户输入] --> S2[INI解析] --> S3[HP平衡] --> S4[喷管计算] --> S5[循环闭合] --> S6[结果输出] -.-> S7[核验]\n  S4 -->|combustion无循环层| S6\n  S7 -. 偏差未解释 .-> S1\n",
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
*{box-sizing:border-box}body{margin:0;background:#f6f7f9;color:#1f2328;font-family:"Microsoft YaHei",Arial,sans-serif}a{color:#0277bd}header{padding:30px 4vw 20px;background:#fff;border-bottom:1px solid #e1e4e8}header p{color:#5f6670;max-width:900px;line-height:1.65}h1{font-size:29px;margin:0}nav{display:flex;gap:10px;flex-wrap:wrap}button{padding:11px 22px;border:1px solid #c5cad3;border-radius:5px;color:#1f2328;background:#fff;font-size:16px;cursor:pointer}button:hover{border-color:#0277bd}button:focus-visible{outline:2px solid #0277bd;outline-offset:2px}button[aria-selected=true]{background:#0277bd;color:#fff;border-color:#0277bd}main{max-width:1760px;margin:auto;padding:24px}.view{display:none;background:#fff;border:1px solid #e1e4e8;border-radius:8px;overflow:hidden}.view.selected{display:block}svg{width:100%;height:auto;display:block}aside{padding:28px 20px;background:#fff;border:1px solid #e1e4e8;border-radius:8px;margin-top:24px}h2{font-size:22px}table{border-collapse:collapse;width:100%;line-height:1.7;font-size:15px}td,th{padding:13px;text-align:left;border-bottom:1px solid #e1e4e8;vertical-align:top}th{color:#5f6670}footer{padding:22px 4vw;color:#5f6670;font-size:14px}@media print{header nav{display:none}.view{display:block;break-after:page}aside{break-before:page}main{padding:0}}@media(max-width:700px){main{padding:8px}aside{overflow:auto}header{padding:20px}h1{font-size:24px}}
</style>
<header><h1>Rocketperf · 作业与项目架构</h1><p>先看作业要求如何对应证据、C计算、研究分析和四项交付，再按业务、计算与执行三个视角查看维护边界。图中的方法能力不是两型真实性能；任务实况由项目登记维护。</p><nav role="tablist" aria-label="架构视图"><button data-view="assignment" aria-selected="true">作业对接总览</button><button data-view="business" aria-selected="false">01 业务层次</button><button data-view="components" aria-selected="false">02 功能核心</button><button data-view="workflow" aria-selected="false">03 工作流程</button></nav></header>
<main>'''+sections+'''<aside><h2>模块维护契约</h2><table><thead><tr><th>模块</th><th>维护职责</th><th>边界</th><th>实现状态</th></tr></thead><tbody>'''+contracts+'''</tbody></table></aside></main><footer>离线可用，无CDN或网络请求。生成源：project/modules.json、tools/render_architecture.py与tools/assignment_diagram.py；SVG与Mermaid源同目录保留。</footer>
<script>document.querySelectorAll('button[data-view]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('button[data-view]').forEach(x=>x.setAttribute('aria-selected',String(x===b)));document.querySelectorAll('.view').forEach(s=>s.classList.toggle('selected',s.id===b.dataset.view));}));</script></html>
'''
    return outputs


if __name__=="__main__":
    for relative,content in expected_architecture(ROOT).items(): atomic_text(ROOT/relative,content)
    print("Rendered 4 SVG, 4 Mermaid sources and offline HTML architecture browser")
