"""Interactive include graph of the C core: one self-contained dark dashboard."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/architecture/code-graph.html"
SCAN = [ROOT / "src", ROOT / "include"]
INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)

MODULES = {
    "cli": ("cli 命令行", "#58a6ff"),
    "adapters": ("adapters 输入输出", "#3fb9c4"),
    "thermo": ("thermo 热化学", "#f0883e"),
    "nozzle": ("nozzle 喷管", "#d2a679"),
    "cycle": ("cycle 循环", "#e3b341"),
    "core": ("core 数值", "#8b949e"),
    "include": ("公共头文件", "#bc8cff"),
}

files = {}
for base in SCAN:
    for path in base.rglob("*"):
        if path.suffix not in (".c", ".h") or path.name.endswith("_generated.h"):
            continue
        rel = path.relative_to(ROOT).as_posix()
        module = rel.split("/")[1] if rel.startswith("src/") else "include"
        files[rel] = {"module": module, "includes": INCLUDE.findall(path.read_text(encoding="utf-8", errors="replace"))}

index = {Path(rel).name: rel for rel in files}
edges = []
for rel, info in files.items():
    for inc in info["includes"]:
        target = index.get(Path(inc).name)
        if target and target != rel:
            edges.append([rel, target])

nodes = [{"id": rel, "name": Path(rel).name, "module": info["module"],
          "kind": "c" if rel.endswith(".c") else "h"} for rel, info in sorted(files.items())]

TEMPLATE = r"""<!doctype html>
<meta charset="utf-8"><title>rocketperf · C 代码关系</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--line:#21262d;--fg:#e6edf3;--mut:#8b949e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:"Segoe UI","Microsoft YaHei",sans-serif;
 display:grid;grid-template-columns:236px 1fr 320px;grid-template-rows:54px 1fr;height:100vh}
header{grid-column:1/4;display:flex;align-items:center;gap:14px;padding:0 18px;background:#010409;border-bottom:1px solid var(--line)}
h1{font-size:15px;margin:0;font-weight:650;letter-spacing:.02em}
h1 em{color:var(--mut);font-style:normal;font-weight:400;font-size:12.5px;margin-left:12px}
input{margin-left:auto;background:#0d1117;border:1px solid #30363d;color:var(--fg);border-radius:6px;padding:7px 12px;width:230px;font-size:13px;outline:none}
input:focus{border-color:#58a6ff}
aside,#detail{background:var(--panel);overflow:auto}
aside{border-right:1px solid var(--line);padding:14px 14px}
#detail{border-left:1px solid var(--line);padding:18px}
h2{font-size:11px;color:var(--mut);letter-spacing:.1em;text-transform:uppercase;margin:12px 0 6px}
.mod{display:flex;align-items:center;gap:8px;padding:5px 6px;font-size:13px;cursor:pointer;border-radius:6px;user-select:none}
.mod:hover{background:#1c2330}.mod.off{opacity:.35}
.mod i{width:9px;height:9px;border-radius:2px;flex:none}.mod .cnt{margin-left:auto;color:var(--mut);font-size:11px}
svg{width:100%;height:100%;background:radial-gradient(ellipse at 50% 42%,#141b24,#0d1117)}
.node{cursor:pointer}.node text{pointer-events:none}
#detail h3{font-size:15px;margin:0 0 3px;word-break:break-all}
.path{color:var(--mut);font:12px Consolas,monospace;word-break:break-all}
.badge{display:inline-block;font-size:11px;padding:2px 9px;border-radius:10px;border:1px solid;margin:9px 0}
ul{list-style:none;padding:0;margin:4px 0 12px}
li{font:12.5px Consolas,monospace;padding:3px 2px;cursor:pointer;border-radius:4px}
li:hover{background:#1c2330;color:#58a6ff}
.empty{color:var(--mut);font-size:13px;line-height:1.6}
</style>
<header><h1>rocketperf · C 代码关系<em id="stat"></em></h1>
<input id="q" placeholder="筛选文件名…"></header>
<aside><h2>模块</h2><div id="mods"></div>
<h2>图例</h2><div class="empty">方块 = .c 源文件<br>圆角 = .h 头文件<br>连线 = #include 依赖<br><br>滚轮缩放 · 拖动画布<br>拖节点微调 · 点击看依赖</div></aside>
<svg id="stage"></svg>
<div id="detail"><div class="empty" id="placeholder">点击一个文件，查看它 include 了谁、被谁引用。</div></div>
<script>
const DATA=__DATA__, COLOR=__COLOR__;
const NS='http://www.w3.org/2000/svg', svg=document.getElementById('stage');
const nodes=DATA.nodes.map(n=>({...n,x:0,y:0,vx:0,vy:0}));
const byId=Object.fromEntries(nodes.map(n=>[n.id,n]));
const edges=DATA.edges.map(([a,b])=>({a:byId[a],b:byId[b]})).filter(e=>e.a&&e.b);
const adj={}; edges.forEach(e=>{(adj[e.a.id]=adj[e.a.id]||new Set()).add(e.b.id);(adj[e.b.id]=adj[e.b.id]||new Set()).add(e.a.id)});
document.getElementById('stat').textContent=nodes.length+' 个文件 · '+edges.length+' 条依赖';

const hidden=new Set();
document.getElementById('mods').innerHTML=Object.entries(COLOR).map(([m,[label,c]])=>{
  const n=nodes.filter(x=>x.module===m).length; return n?
  '<div class="mod" data-m="'+m+'"><i style="background:'+c+'"></i>'+label+'<span class="cnt">'+n+'</span></div>':''}).join('');
document.getElementById('mods').onclick=ev=>{const d=ev.target.closest('.mod'); if(!d) return;
  hidden.has(d.dataset.m)?hidden.delete(d.dataset.m):hidden.add(d.dataset.m); d.classList.toggle('off'); paint()};

const g=document.createElementNS(NS,'g'); svg.appendChild(g);
const linkG=document.createElementNS(NS,'g'), nodeG=document.createElementNS(NS,'g');
g.append(linkG,nodeG);
const curves=edges.map(()=>{const p=document.createElementNS(NS,'path'); p.setAttribute('fill','none'); linkG.appendChild(p); return p});
const marks=nodes.map(n=>{const s=document.createElementNS(NS,'g'); s.classList.add('node');
  const r=document.createElementNS(NS,'rect'), t=document.createElementNS(NS,'text');
  r.setAttribute('height','26'); r.setAttribute('rx', n.kind==='c'?5:13);
  r.setAttribute('fill','#1c2333'); r.setAttribute('stroke',COLOR[n.module][1]); r.setAttribute('stroke-width','1.5');
  t.textContent=n.name; t.setAttribute('fill','#e6edf3'); t.setAttribute('font-size','12');
  s.append(r,t); nodeG.appendChild(s);
  s.onpointerdown=ev=>{ev.stopPropagation(); dragNode=n; sx=ev.clientX; sy=ev.clientY; moved=false};
  s.onclick=ev=>{ev.stopPropagation(); if(!moved){sel=sel===n?null:n; detail(n)}};
  return s});

const cols={cli:0,adapters:1,thermo:2,nozzle:3,cycle:4,core:5,include:6};
const groups={}; nodes.forEach(n=>{(groups[n.module]=groups[n.module]||[]).push(n)});
Object.values(groups).forEach(a=>a.sort((p,q)=>p.name.localeCompare(q.name)));
const X=n=>150+cols[n.module]*215, Y=n=>50+groups[n.module].indexOf(n)*(740/groups[n.module].length);
nodes.forEach(n=>{n.x=X(n); n.y=Y(n)+20});
for(let k=0;k<600;k++){
  for(let i=0;i<nodes.length;i++) for(let j=i+1;j<nodes.length;j++){const a=nodes[i],b=nodes[j];
    let dx=a.x-b.x,dy=a.y-b.y,d=Math.hypot(dx,dy)||1; if(d>240) continue;
    const f=Math.min(50,1600/(d*d)); a.vx+=dx/d*f; a.vy+=dy/d*f; b.vx-=dx/d*f; b.vy-=dy/d*f}
  edges.forEach(e=>{let dx=e.b.x-e.a.x,dy=e.b.y-e.a.y; e.a.vx+=dx*.006; e.a.vy+=dy*.006; e.b.vx-=dx*.006; e.b.vy-=dy*.006});
  nodes.forEach(n=>{n.vx+=(X(n)-n.x)*.14; n.vy+=(Y(n)-n.y)*.14; n.vx*=.4; n.vy*=.4;
    n.x=Math.max(30,Math.min(1580,n.x+n.vx)); n.y=Math.max(24,Math.min(800,n.y+n.vy))});
}

let sel=null, dragNode=null, dragPan=false, moved=false, sx=0, sy=0, tx=0, ty=0, sc=1, query='';
function vis(n){return !hidden.has(n.module) && (!query || n.name.toLowerCase().includes(query))}
function paint(){ const near = sel? new Set([sel.id, ...(adj[sel.id]||[])]) : null;
  curves.forEach((p,i)=>{const e=edges[i], on=vis(e.a)&&vis(e.b);
    const mx=(e.a.x+e.b.x)/2, my=(e.a.y+e.b.y)/2-18;
    p.setAttribute('d','M'+e.a.x+' '+e.a.y+' Q'+mx+' '+my+' '+e.b.x+' '+e.b.y);
    const hot=near&&near.has(e.a.id)&&near.has(e.b.id);
    p.setAttribute('stroke', hot? COLOR[e.b.module][1] : '#3a4454');
    p.setAttribute('stroke-width', hot?1.8:1);
    p.setAttribute('stroke-opacity', on ? (hot ? .9 : (near ? .08 : .5)) : .04); });
  marks.forEach((s,i)=>{const n=nodes[i], w=n.name.length*7.1+18;
    s.setAttribute('transform','translate('+(n.x-w/2)+','+(n.y-13)+')');
    s.firstChild.setAttribute('width',w);
    s.lastChild.setAttribute('x',9); s.lastChild.setAttribute('y',17);
    const on=vis(n), hot=!near||near.has(n.id);
    s.setAttribute('opacity', on ? (hot ? 1 : .14) : .05);
    s.firstChild.setAttribute('stroke-width', sel===n?2.6:1.5); }); }
paint();
const xs=nodes.map(n=>n.x), ys=nodes.map(n=>n.y);
const minX=Math.min(...xs)-90, maxX=Math.max(...xs)+110, minY=Math.min(...ys)-36, maxY=Math.max(...ys)+36;
sc=Math.min(svg.clientWidth/(maxX-minX), svg.clientHeight/(maxY-minY));
tx=(svg.clientWidth-(minX+maxX)*sc)/2; ty=(svg.clientHeight-(minY+maxY)*sc)/2; apply();

function detail(n){ document.getElementById('detail').innerHTML =
  '<h3>'+n.name+'</h3><div class="path">'+n.id+'</div>'
  +'<span class="badge" style="color:'+COLOR[n.module][1]+';border-color:'+COLOR[n.module][1]+'">'+COLOR[n.module][0]+'</span>'
  +section('include', edges.filter(e=>e.a===n).map(e=>e.b))
  +section('被引用', edges.filter(e=>e.b===n).map(e=>e.a)); }
function section(title,list){ return '<h2>'+title+' · '+list.length+'</h2>'
  +(list.length? '<ul>'+list.map(n=>'<li data-id="'+n.id+'">'+n.name+'</li>').join('')+'</ul>'
    : '<div class="empty">无</div>'); }
document.getElementById('detail').onclick=ev=>{const li=ev.target.closest('li'); if(!li) return;
  sel=byId[li.dataset.id]; detail(sel); paint(); };

svg.onpointerdown=ev=>{dragPan=true; dragNode=null; sx=ev.clientX; sy=ev.clientY; moved=false};
addEventListener('pointermove',ev=>{ if(dragNode){ moved=true;
    dragNode.x=(ev.clientX-tx)/sc; dragNode.y=(ev.clientY-ty)/sc; paint(); }
  else if(dragPan && ev.buttons){ tx+=ev.clientX-sx; ty+=ev.clientY-sy; sx=ev.clientX; sy=ev.clientY; apply(); }});
addEventListener('pointerup',()=>{dragNode=null; dragPan=false});
svg.onclick=()=>{sel=null; paint(); document.getElementById('detail').innerHTML='<div class="empty">点击一个文件，查看它 include 了谁、被谁引用。</div>'};
svg.onwheel=ev=>{ev.preventDefault(); const k=ev.deltaY<0?1.12:.89;
  tx=ev.clientX-(ev.clientX-tx)*k; ty=ev.clientY-(ev.clientY-ty)*k; sc*=k; apply(); };
function apply(){ g.setAttribute('transform','translate('+tx+','+ty+') scale('+sc+')'); }
document.getElementById('q').oninput=ev=>{query=ev.target.value.trim().toLowerCase(); paint()};
</script>
"""

page = TEMPLATE.replace("__DATA__", json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False))
page = page.replace("__COLOR__", json.dumps(MODULES, ensure_ascii=False))
OUT.write_text(page, encoding="utf-8", newline="\n")
print(f"{OUT}  {len(nodes)} files, {len(edges)} edges")
