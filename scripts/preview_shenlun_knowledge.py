#!/usr/bin/env python3
"""从正式申论 Markdown 生成只读移动端结构预览，不连接数据库。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.services.knowledge_md import parse_md  # noqa: E402

SOURCE = ROOT / "docs/content/knowledge-framework/申论.md"
OUTPUT = ROOT / "docs/prototypes/申论知识框架移动端预览.html"


def compact_node(node, parent_id: int | None, counter: list[int]) -> dict:
    counter[0] += 1
    node_id = counter[0]
    children = [compact_node(child, node_id, counter) for child in node.children]
    return {
        "id": node_id,
        "parentId": parent_id,
        "title": node.title,
        "path": node.path,
        "children": children,
        "descendants": sum(child["descendants"] + 1 for child in children),
    }


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>申论知识框架 · 移动端预览</title>
  <style>
    :root{--zk-primary:#d0021b;--zk-primary-dark:#8b0000;--zk-primary-light:#fbeaec;--zk-text:#1a1a1a;--zk-sub:#686868;--zk-muted:#949494;--zk-page:#f3f4f6;--zk-card:#fff;--zk-border:#ebebeb;--zk-soft:#f8f8f9}
    *{box-sizing:border-box}
    body{margin:0;background:#e8e9ec;color:var(--zk-text);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
    button,input{font:inherit}
    button{cursor:pointer}
    .app{max-width:460px;min-height:100vh;margin:auto;background:var(--zk-page);box-shadow:0 0 36px rgba(0,0,0,.08);padding-bottom:calc(86px + env(safe-area-inset-bottom))}
    .hero{background:linear-gradient(160deg,var(--zk-primary) 0%,#ae1225 52%,var(--zk-primary-dark) 100%);color:#fff;padding:calc(24px + env(safe-area-inset-top)) 20px 24px;border-radius:0 0 24px 24px}
    .hero-top{display:flex;align-items:center;justify-content:space-between;font-size:12px;opacity:.92}
    .brand{font-weight:700;letter-spacing:.08em}
    .badge{padding:5px 9px;border-radius:99px;background:rgba(255,255,255,.18)}
    h1{font-size:26px;line-height:1.2;margin:29px 0 9px}
    .hero p{font-size:13px;line-height:1.65;opacity:.93;margin:0}
    .stats{display:flex;gap:9px;margin-top:20px}
    .stat{flex:1;padding:11px 12px;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.12);border-radius:12px}
    .stat strong{display:block;font-size:18px;line-height:1.2}
    .stat span{font-size:11px;opacity:.88}
    .content{padding:18px 16px 12px}
    .notice{background:#fff;border:1px solid var(--zk-border);border-left:3px solid var(--zk-primary);border-radius:11px;padding:11px 12px;color:var(--zk-sub);font-size:12px;line-height:1.55;margin-bottom:18px}
    .section-head{display:flex;justify-content:space-between;align-items:flex-end;margin:18px 2px 10px}
    .section-head h2{font-size:17px;margin:0}
    .section-head span{font-size:12px;color:var(--zk-muted)}
    .search{display:flex;align-items:center;gap:9px;background:var(--zk-card);border:1px solid var(--zk-border);border-radius:12px;padding:0 13px;height:44px;margin-bottom:14px}
    .search-icon{color:var(--zk-muted);font-size:17px}
    .search input{border:0;outline:0;min-width:0;flex:1;background:transparent;font-size:14px;color:var(--zk-text)}
    .search input::placeholder{color:var(--zk-muted)}
    .branch,.row{width:100%;background:var(--zk-card);border:1px solid var(--zk-border);border-radius:15px;text-align:left;display:flex;align-items:center;gap:12px;color:inherit}
    .branch{padding:15px 14px;margin-bottom:10px;box-shadow:0 2px 8px rgba(24,24,30,.025)}
    .branch:active,.row:active,.map-group:active{transform:scale(.995);background:var(--zk-soft)}
    .branch-number{width:30px;height:30px;flex:none;border-radius:9px;background:var(--zk-primary-light);color:var(--zk-primary);display:grid;place-items:center;font-size:13px;font-weight:700}
    .branch-main,.row-main{flex:1;min-width:0}
    .branch-title,.row-title{display:block;font-weight:650;font-size:15px;line-height:1.35}
    .branch-sub,.row-sub{display:block;color:var(--zk-muted);font-size:12px;line-height:1.45;margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .chevron{color:#b1b1b5;font-size:20px;font-weight:300}
    .subhead{font-size:12px;color:var(--zk-muted);margin:18px 2px 9px}
    .breadcrumb{display:flex;gap:6px;align-items:center;overflow-x:auto;white-space:nowrap;margin:3px 0 16px;padding-bottom:4px;scrollbar-width:none}
    .breadcrumb button{background:none;border:0;padding:4px 0;color:var(--zk-primary);font-size:12px}
    .breadcrumb span{color:#bbb}
    .page-title{font-size:23px;font-weight:750;line-height:1.35;margin:0 0 7px}
    .page-meta{color:var(--zk-sub);font-size:13px;margin-bottom:18px}
    .row{padding:14px 13px;margin-bottom:9px;min-height:64px}
    .row-index{width:25px;height:25px;border-radius:8px;background:var(--zk-soft);color:var(--zk-sub);font-size:12px;display:grid;place-items:center;flex:none}
    .row-title{font-size:14px;font-weight:600;word-break:break-word}
    .leaf{font-size:11px;color:var(--zk-primary);background:var(--zk-primary-light);border-radius:99px;padding:4px 7px;flex:none}
    .map-intro{font-size:13px;color:var(--zk-sub);line-height:1.65;margin-bottom:16px}
    .map-group{border:1px solid var(--zk-border);background:var(--zk-card);border-radius:15px;margin-bottom:12px;padding:14px}
    .map-title{width:100%;border:0;background:none;padding:0;text-align:left;color:inherit;cursor:pointer;font-size:15px;font-weight:700;display:flex;justify-content:space-between;align-items:center}
    .map-title small{font-weight:400;color:var(--zk-muted)}
    .map-children{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px;padding-left:13px;border-left:2px solid var(--zk-primary-light)}
    .map-chip{border:1px solid var(--zk-border);background:var(--zk-soft);color:var(--zk-sub);border-radius:8px;padding:7px 9px;font-size:12px;line-height:1.35;text-align:left}
    .results-note{color:var(--zk-muted);font-size:12px;margin:4px 2px 14px}
    .empty{background:var(--zk-card);border-radius:12px;padding:35px 15px;text-align:center;color:var(--zk-muted);font-size:13px}
    .tabbar{position:fixed;bottom:0;width:min(100%,460px);display:grid;grid-template-columns:1fr 1fr;gap:0;background:var(--zk-card);border-top:1px solid var(--zk-border);padding:9px 12px calc(9px + env(safe-area-inset-bottom));box-shadow:0 -5px 24px rgba(0,0,0,.035)}
    .tabbar button{border:0;background:none;color:var(--zk-muted);padding:5px;font-size:12px}
    .tabbar .icon{display:block;font-size:18px;margin-bottom:2px}
    .tabbar .active{color:var(--zk-primary);font-weight:700}
    .sheet-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.35);display:none;align-items:flex-end;justify-content:center;z-index:5}
    .sheet-backdrop.show{display:flex}
    .sheet{width:min(100%,460px);background:var(--zk-card);border-radius:20px 20px 0 0;padding:22px 20px calc(28px + env(safe-area-inset-bottom))}
    .sheet small{color:var(--zk-primary);font-size:12px}
    .sheet h3{font-size:20px;line-height:1.45;margin:10px 0}
    .sheet p{font-size:13px;color:var(--zk-sub);line-height:1.7}
    .sheet-path{font-size:12px;color:var(--zk-muted);word-break:break-all}
    .sheet-close{width:100%;margin-top:16px;border:0;border-radius:10px;background:var(--zk-primary);color:#fff;padding:12px;font-weight:600}
    @media(min-width:600px){.app{margin-top:20px;min-height:calc(100vh - 40px);border-radius:24px;overflow:hidden}.hero{padding-top:24px}.tabbar{bottom:20px;border-radius:0 0 24px 24px}}
  </style>
</head>
<body>
<div class="app">
  <header class="hero">
    <div class="hero-top"><span class="brand">杜衡阁 · 知识框架</span><span class="badge">申论结构预览</span></div>
    <h1>读懂申论知识结构</h1>
    <p>按题型逐层展开，从大框架定位到具体方法。</p>
    <div class="stats"><div class="stat"><strong>8</strong><span>一级主题</span></div><div class="stat"><strong>535</strong><span>知识节点</span></div><div class="stat"><strong>7</strong><span>最深层级</span></div></div>
  </header>
  <main id="content" class="content"></main>
  <nav class="tabbar"><button id="tabDirectory" class="active"><span class="icon">▤</span>逐层浏览</button><button id="tabMap"><span class="icon">⌗</span>结构总览</button></nav>
</div>
<div id="sheetBackdrop" class="sheet-backdrop"><div class="sheet"><small>知识节点</small><h3 id="sheetTitle"></h3><div id="sheetPath" class="sheet-path"></div><p>当前资料只包含知识结构。知识讲解、例题和掌握度将在内容补齐后开放。</p><button id="sheetClose" class="sheet-close">继续浏览</button></div></div>
<script id="tree-data" type="application/json">__DATA__</script>
<script>
  const root = JSON.parse(document.getElementById('tree-data').textContent);
  const byId = new Map();
  function index(node){byId.set(node.id,node);(node.children||[]).forEach(index)}
  index(root);
  const state={mode:'directory',nodeId:root.id,query:''};
  const content=document.getElementById('content');
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function ancestors(node){const out=[];while(node){out.unshift(node);node=byId.get(node.parentId)}return out}
  function go(id){const n=byId.get(Number(id));if(!n)return;if(!n.children.length){openSheet(n);return}state.mode='directory';state.nodeId=n.id;state.query='';render();scrollTo(0,0)}
  function openSheet(n){document.getElementById('sheetTitle').textContent=n.title;document.getElementById('sheetPath').textContent=ancestors(n).slice(1).map(x=>x.title).join(' / ');document.getElementById('sheetBackdrop').classList.add('show')}
  function row(n,i){return `<button class="row" data-node="${n.id}"><span class="row-index">${String(i+1).padStart(2,'0')}</span><span class="row-main"><span class="row-title">${esc(n.title)}</span><span class="row-sub">${n.children.length?`${n.children.length} 个直接分支 · ${n.descendants} 个下级节点`:'查看所在知识路径'}</span></span>${n.children.length?'<span class="chevron">›</span>':'<span class="leaf">末级</span>'}</button>`}
  function renderHome(){
    const tops=root.children;
    const group=(title,items,start)=>`<div class="section-head"><h2>${title}</h2><span>${items.length} 个主题</span></div>${items.map((n,i)=>`<button class="branch" data-node="${n.id}"><span class="branch-number">${String(start+i+1).padStart(2,'0')}</span><span class="branch-main"><span class="branch-title">${esc(n.title)}</span><span class="branch-sub">${n.descendants} 个下级节点 · ${esc(n.children.slice(0,3).map(x=>x.title).join(' / '))}</span></span><span class="chevron">›</span></button>`).join('')}`;
    return `<div class="notice">先看题型之间的关系，再逐层进入考点。本预览只验证结构呈现，暂不把浏览节点当作“已经掌握”。</div><label class="search"><span class="search-icon">⌕</span><input id="search" placeholder="搜索 535 个知识节点" value="${esc(state.query)}" /></label>${group('五类题型',tops.slice(0,5),0)}${group('通用作答方法',tops.slice(5),5)}`
  }
  function renderBranch(){const n=byId.get(state.nodeId);const path=ancestors(n);return `<div class="breadcrumb">${path.map((p,i)=>`${i?'<span>›</span>':''}<button data-bread="${p.id}">${esc(p.title)}</button>`).join('')}</div><h2 class="page-title">${esc(n.title)}</h2><div class="page-meta">${n.children.length} 个直接分支 · ${n.descendants} 个下级节点</div>${n.children.map(row).join('')||'<div class="empty">此节点没有下级内容</div>'}<div class="subhead">逐层浏览 · 只显示当前层，避免手机上一次展开数百个节点</div>`}
  function renderMap(){return `<div class="section-head"><h2>申论结构总览</h2><span>只展示前两层</span></div><div class="map-intro">总览用于找位置；点击题型或分支，可进入逐层目录继续看。深层内容不压缩进一张长图。</div>${root.children.map(n=>`<div class="map-group"><button class="map-title" data-node="${n.id}">${esc(n.title)} <small>${n.descendants} 个下级节点 ›</small></button><div class="map-children">${n.children.map(c=>`<button class="map-chip" data-node="${c.id}">${esc(c.title)}</button>`).join('')}</div></div>`).join('')}`}
  function renderSearch(){const q=state.query.trim().toLowerCase();const all=[...byId.values()].filter(n=>n.id!==root.id&&n.title.toLowerCase().includes(q));const hit=all.slice(0,60);return `<div class="breadcrumb"><button data-home="1">申论</button><span>›</span><span>搜索</span></div><label class="search"><span class="search-icon">⌕</span><input id="search" placeholder="搜索知识节点" value="${esc(state.query)}" autofocus /></label><div class="results-note">找到 ${all.length} 个相关节点${all.length>60?'，先显示前 60 个':''}</div>${hit.length?hit.map((n,i)=>`<button class="row" data-node="${n.id}"><span class="row-index">${i+1}</span><span class="row-main"><span class="row-title">${esc(n.title)}</span><span class="row-sub">${esc(ancestors(n).slice(1,-1).map(x=>x.title).join(' / '))}</span></span><span class="chevron">›</span></button>`).join(''):'<div class="empty">没有找到匹配的知识点</div>'}`}
  function render(){content.innerHTML=state.mode==='map'?renderMap():state.mode==='search'?renderSearch():state.nodeId===root.id?renderHome():renderBranch();document.getElementById('tabDirectory').classList.toggle('active',state.mode!=='map');document.getElementById('tabMap').classList.toggle('active',state.mode==='map');const input=document.getElementById('search');if(input){input.addEventListener('input',e=>{const pos=e.target.selectionStart;state.query=e.target.value;state.mode=state.query?'search':'directory';state.nodeId=root.id;render();const next=document.getElementById('search');next.focus();next.setSelectionRange(pos,pos)})}}
  content.addEventListener('click',e=>{const target=e.target.closest('[data-node],[data-bread],[data-home]');if(!target)return;if(target.dataset.node)go(target.dataset.node);else if(target.dataset.bread)go(target.dataset.bread);else{state.mode='directory';state.nodeId=root.id;state.query='';render()}});
  document.getElementById('tabDirectory').addEventListener('click',()=>{state.mode='directory';state.nodeId=root.id;state.query='';render();scrollTo(0,0)});
  document.getElementById('tabMap').addEventListener('click',()=>{state.mode='map';state.query='';render();scrollTo(0,0)});
  document.getElementById('sheetClose').addEventListener('click',()=>document.getElementById('sheetBackdrop').classList.remove('show'));
  document.getElementById('sheetBackdrop').addEventListener('click',e=>{if(e.target.id==='sheetBackdrop')e.currentTarget.classList.remove('show')});
  render();
</script>
</body>
</html>
"""


def main() -> None:
    parsed = parse_md(SOURCE.read_text(encoding="utf-8"))
    if parsed.has_errors or not parsed.tree:
        raise SystemExit("申论 Markdown 校验失败")
    if parsed.stats["nodeCount"] != 535:
        raise SystemExit(f"申论节点数变化：{parsed.stats['nodeCount']}，预期 535")
    tree = compact_node(parsed.tree, None, [0])
    payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
    print(f"已生成 {OUTPUT}（{parsed.stats['nodeCount']} 个节点）")


if __name__ == "__main__":
    main()
