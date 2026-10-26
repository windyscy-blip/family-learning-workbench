# -*- coding: utf-8 -*-
"""Build family-learning-workbench v2: integrate phonics V13 module + english/chinese dictation modules."""
import re
from pathlib import Path

ROOT = Path(r"C:/Users/sPark/WorkBuddy/2026-10-09-16-55-37")
V13 = (ROOT / "outputs" / "phonics-parent-tool-v13.html").read_text(encoding="utf-8")

# ---------- extract phonics style / body / script ----------
style_m = re.search(r"<style>([\s\S]*?)</style>", V13)
phonics_css = style_m.group(1)
body_m = re.search(r"<body>([\s\S]*?)<script>", V13)
phonics_body = body_m.group(1)
script_m = re.search(r"<script>([\s\S]*?)</script>\s*</body>", V13)
phonics_js = script_m.group(1)


def scope_css(css: str, scope: str = "#phonicsApp") -> str:
    """Scope all top-level rules under #phonicsApp; keep @keyframes/@media inner rules scoped too."""
    out = []
    i, n = 0, len(css)

    def find_close(text, start):
        depth = 0
        j = start
        while j < len(text):
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return j
            j += 1
        return len(text) - 1

    def split_commas(sel):
        parts, depth, cur = [], 0, ""
        for ch in sel:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        if cur.strip():
            parts.append(cur)
        return [p.strip() for p in parts if p.strip()]

    while i < n:
        while i < n and css[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        brace = css.find("{", i)
        if brace == -1:
            break
        sel = css[i:brace].strip()
        close = find_close(css, brace)
        block = css[brace + 1: close]
        if sel.startswith("@media"):
            out.append(sel + "{" + scope_css(block, scope) + "}")
        elif sel.startswith("@keyframes") or sel.startswith("@font-face") or sel.startswith("@charset"):
            out.append(sel + "{" + block + "}")
        else:
            newsels = []
            for s in split_commas(sel):
                if s in (":root", "body"):
                    newsels.append(scope)
                elif s == "html":
                    continue
                elif s == "*":
                    newsels.append(scope + " *")
                else:
                    newsels.append(scope + " " + s)
            if newsels:
                out.append(", ".join(newsels) + "{" + block + "}")
        i = close + 1
    return "\n".join(out)


scoped_css = scope_css(phonics_css)

# ---------- transform phonics js ----------
js = phonics_js
# ---------- simplify phonics material selection: random draw only, no manual picking ----------
# List: plain cards, no checkboxes.
js = js.replace(
    "document.getElementById('items').innerHTML=arr.map(m=>`<label class=\"word-item\"><input type=\"checkbox\" data-material=\"${m.id}\" ${context.selected.includes(m.id)?'checked':''}><span><b>${esc(m.word)}</b><br><span class=\"tag\">${esc(m.meaning)} · ${esc(m.primaryLessonId)}${m.reviewed?'':' · 家长增词，未审校'}</span></span><span class=\"word-symbol\" aria-hidden=\"true\">${esc(m.emoji)}</span></label>`).join('');",
    "document.getElementById('items').innerHTML=arr.map(m=>`<div class=\"word-item\"><span><b>${esc(m.word)}</b><br><span class=\"tag\">${esc(m.meaning)} · ${esc(m.primaryLessonId)}${m.reviewed?'':' · 家长增词，未审校'}</span></span><span class=\"word-symbol\" aria-hidden=\"true\">${esc(m.emoji)}</span></div>`).join('');",
)
# Status texts: pool size instead of selected count.
js = js.replace(
    "document.getElementById('selectionM').textContent=`已选 ${context.selected.length} 个材料`;",
    "document.getElementById('selectionM').textContent=`本课 ${materials.filter(m=>m.course===c[0]).length} 个材料 · 随机抽取`;",
)
js = js.replace(
    "document.getElementById('counts').textContent=`当前显示 ${arr.length} 项 / 本课 ${materials.filter(m=>m.course===c[0]).length} 项`;",
    "",
)
js = js.replace(
    "document.getElementById('prepareCount').textContent=`本轮 ${context.quantity} 题 · 已选 ${context.selected.length} 个材料`;",
    "document.getElementById('prepareCount').textContent=`本轮 ${context.quantity} 题 · 从本课 ${materials.filter(m=>m.course===c[0]).length} 个材料随机抽取`;",
)
js = js.replace(
    "document.getElementById('trainStart').disabled=!context.selected.length||!context.quantity||context.quantity>context.selected.length;document.getElementById('flashStart').disabled=!context.selected.length;",
    "document.getElementById('trainStart').disabled=!context.selected.length||!context.quantity||context.quantity>context.selected.length;",
)
# Drop checkbox change handlers and saved-group UI (manual selection is gone).
js = js.replace(
    "document.querySelectorAll('[data-material]').forEach(box=>box.onchange=()=>{context.selected=box.checked?[...new Set([...context.selected,box.dataset.material])]:context.selected.filter(id=>id!==box.dataset.material);if(context.quantity>context.selected.length)context.quantity=context.selected.length;persistConfig();renderDetail()});document.querySelectorAll('[data-group-load]').forEach(b=>b.onclick=()=>loadGroup(+b.dataset.groupLoad));document.querySelectorAll('[data-group-rename]').forEach(b=>b.onclick=()=>renameGroup(+b.dataset.groupRename));document.querySelectorAll('[data-group-delete]').forEach(b=>b.onclick=()=>deleteGroup(+b.dataset.groupDelete));",
    "",
)
js = js.replace(
    "document.getElementById('groups').innerHTML=state.savedGroups.filter(g=>g.courseId===c[0]).map((g,i)=>`<span>${esc(g.name)} (${g.itemIds.length}) <button data-group-load=\"${i}\">加载</button><button data-group-rename=\"${i}\">改名</button><button data-group-delete=\"${i}\">删除</button></span>`).join('')+'<button id=\"saveGroup\">保存当前选择为常用组</button>';document.getElementById('saveGroup').onclick=saveGroup;",
    "document.getElementById('groups').innerHTML='';",
)
# Drop bindings of removed controls.
js = js.replace(
    "document.getElementById('selectVisible').onclick=()=>{context.selected=[...new Set([...context.selected,...filtered().map(m=>m.id)])];context.quantity=Math.min(Math.max(context.quantity,1),context.selected.length);persistConfig();renderDetail()};document.getElementById('selectCourse').onclick=()=>{context.selected=materials.filter(m=>m.course===context.courseId).map(m=>m.id);context.quantity=Math.min(8,context.selected.length);persistConfig();renderDetail()};document.getElementById('clearCourse').onclick=()=>{context.selected=[];context.quantity=0;persistConfig();renderDetail()};document.getElementById('search').oninput=e=>{context.search=e.target.value;renderDetail()};document.getElementById('lessonFilter').onchange=e=>{context.lesson=e.target.value;renderDetail()};document.getElementById('sort').onchange=e=>{context.sort=e.target.value;context.randomIds=[];renderDetail()};document.getElementById('reshuffle').onclick=()=>{context.randomIds=shuffle(filtered().map(m=>m.id));persistConfig();renderDetail()};",
    "",
)
js = js.replace(
    "document.getElementById('randomTrain').onchange=e=>{context.randomTrain=e.target.checked;persistConfig()};",
    "",
)
# renderDetail: stop touching removed elements.
js = js.replace(
    "document.getElementById('lessonFilter').innerHTML='<option value=\"all\">全部小课与标签</option>'+lessons.map(x=>`<option value=\"${esc(x)}\">${esc(x)}</option>`).join('');document.getElementById('lessonFilter').value=context.lesson;document.getElementById('search').value=context.search;document.getElementById('sort').value=context.sort;document.getElementById('quantity').value=context.quantity;document.getElementById('randomTrain').checked=context.randomTrain;",
    "document.getElementById('quantity').value=context.quantity;",
)
# enterCourse: default to the whole course pool, always random draw.
js = js.replace(
    "const courseItems=materials.filter(m=>m.course===id),defaults=id==='C02'?courseItems.filter(m=>m.tags.includes('基础')):courseItems;context={courseId:id,selected:defaults.map(m=>m.id),lesson:'all',search:'',sort:'order',randomIds:[],scrollY:0,quantity:Math.min(8,defaults.length),randomTrain:false};document.getElementById('search').value='';document.getElementById('sort').value='order';document.getElementById('quantity').value=context.quantity;persistConfig()}",
    "const courseItems=materials.filter(m=>m.course===id);context={courseId:id,selected:courseItems.map(m=>m.id),lesson:'all',search:'',sort:'order',randomIds:[],scrollY:0,quantity:Math.min(8,courseItems.length),randomTrain:true};document.getElementById('quantity').value=context.quantity;persistConfig()}",
)
# Start button draws a random subset from the course pool.
js = js.replace(
    "document.getElementById('flashStart').onclick=()=>beginFlash(context.selected);document.getElementById('trainStart').onclick=()=>startSession(false);",
    "document.getElementById('trainStart').onclick=()=>{const pool=context.selected.map(byId).filter(Boolean);if(!pool.length)return notice('本课暂无材料。',true);const n=Math.max(1,Math.min(context.quantity||8,pool.length));startSession(false,shuffle(pool).slice(0,n).map(m=>m.id))};",
)
# flash page: "用这组训练" draws randomly from the flash list.
js = js.replace(
    "document.getElementById('flashToTrain').onclick=()=>{context.selected=flash.list.map(x=>x.id);context.quantity=Math.min(context.quantity||8,flash.list.length);startSession(false)}",
    "document.getElementById('flashToTrain').onclick=()=>{const pool=flash.list.slice();const n=Math.max(1,Math.min(context.quantity||8,pool.length));startSession(false,shuffle(pool).slice(0,n).map(m=>m.id))}",
)
# startSession: accept explicit ids as the draw pool (retry path unchanged).
js = js.replace(
    "let pool;if(retry)pool=ids.map(id=>lastResult?.itemSnapshot?.find(m=>m.id===id)).filter(Boolean);else pool=context.selected.map(byId).filter(Boolean);if(!pool.length)return notice('请选择训练材料。');let n=retry?pool.length:context.quantity;",
    "let pool;if(retry)pool=ids.map(id=>lastResult?.itemSnapshot?.find(m=>m.id===id)).filter(Boolean);else if(ids&&ids.length)pool=ids.map(byId).filter(Boolean);else pool=context.selected.map(byId).filter(Boolean);if(!pool.length)return notice('请选择训练材料。');let n=retry?pool.length:Math.min(context.quantity||pool.length,pool.length);",
)
# quantity change: clamp against pool size (selected == whole course now).
js = js.replace(
    "document.getElementById('quantity').onchange=e=>{let n=Number(e.target.value);context.quantity=context.selected.length?Math.max(1,Math.min(context.selected.length,n||1)):0;persistConfig();renderDetail()};",
    "document.getElementById('quantity').onchange=e=>{let n=Number(e.target.value);const pool=materials.filter(m=>m.course===context.courseId).length;context.quantity=pool?Math.max(1,Math.min(pool,n||1)):0;persistConfig();renderDetail()};",
)
# Guard dynamic controls
js = js.replace("document.getElementById('commitImport').onclick=()=>{", "var commitImportEl=document.getElementById('commitImport');if(commitImportEl)commitImportEl.onclick=()=>{")
js = js.replace("document.getElementById('saveGroup').onclick=saveGroup;", "var saveGroupEl=document.getElementById('saveGroup');if(saveGroupEl)saveGroupEl.onclick=saveGroup;")
# homeGroups container lives in the removed home section; its load-group handling moves to delegated document clicks.
js = js.replace("document.getElementById('homeGroups').addEventListener('click',e=>{const b=e.target.closest('[data-load-group]');if(b){const g=state.savedGroups[+b.dataset.loadGroup];if(g){const valid=prepareGroupLoad(g);if(!valid)return;enterCourse(g.courseId);context.selected=valid;context.quantity=Math.min(Math.max(1,context.quantity||8),valid.length);persistConfig();route('detail')}}});", "")
reps = [
    ("querySelectorAll('.view')", "querySelectorAll('#phonicsApp .view')"),
    ("location.hash='course-detail/'+context.courseId", "location.hash='ph/course-detail/'+context.courseId"),
    ("if(hash)location.hash=id;show(id)", "if(hash)location.hash='ph/'+id;show(id)"),
    (
        "window.addEventListener('hashchange',()=>{const h=location.hash.slice(1);if(h.startsWith('course-detail/'))",
        "window.addEventListener('hashchange',()=>{const rawH=location.hash.slice(1);if(!rawH.startsWith('ph/'))return;const h=rawH.slice(3);if(h.startsWith('course-detail/'))",
    ),
    (
        "const h=location.hash.slice(1);if(h.startsWith('course-detail/')){const id=h.split('/')[1];if(id!==context.courseId)enterCourse(id);show('detail')}else show(['home','courses','records','data','train','flash','result'].includes(h)?h:'home');",
        "show('courses');",
    ),
    # route('home') fallbacks -> courses
    ("if(id==='home')renderHome();if(id==='courses'){renderCourses()", "if(id==='courses'){renderCourses();renderLastSession()"),
    ("route('home')", "route('courses')"),
    # show('home') fallback -> courses
    ("?h:'home')", "?h:'courses')"),
    # init(): home resume button no longer exists; last-session strip owns resume.
    ("if(active){session=active;document.getElementById('resume').disabled=false}if(active)active.status='paused';", "if(active)active.status='paused';"),
    # Load-group handling via global delegation (home container removed).
    ("document.addEventListener('click',e=>{const b=e.target.closest('[data-go]');if(!b)return;",
     "document.addEventListener('click',e=>{const lg=e.target.closest('[data-load-group]');if(lg){const g=state.savedGroups[+lg.dataset.loadGroup];if(g){const valid=prepareGroupLoad(g);if(!valid)return;enterCourse(g.courseId);context.selected=valid;context.quantity=Math.min(Math.max(1,context.quantity||8),valid.length);persistConfig();route('detail')}}return;const b0=e.target.closest('[data-go]');if(!b0)return;const b=b0;if(!b)return;"),
    # renderTrain: tolerate sessions whose current item is missing (e.g. resumed legacy test data).
    ("const m=currentItem(),d=draft(),a=session.attempts[m.id];",
     "const m=currentItem(),d=draft();if(!m){notice('本题材料缺失，请重新选材。',true);return}const a=session.attempts[m.id];"),
]
for a, b in reps:
    assert a in js, "phonics js anchor missing: " + a[:60]
    js = js.replace(a, b)

ph_funcs = """
function phEnter(view){
 var shell=document.getElementById('workbenchShell');if(shell)shell.hidden=true;
 var app=document.getElementById('phonicsApp');if(app)app.hidden=false;
 show(view||'courses');
}
function phLeave(){
 try{stopSpeech()}catch(e){}
 try{document.getElementById('phonicsApp').hidden=true}catch(e){}
 var shell=document.getElementById('workbenchShell');if(shell)shell.hidden=false;
}
function renderLastSession(){
 var el=document.getElementById('lastSessionStrip');if(!el)return;
 var ls=state.sessions.filter(function(s){return s.status!=='active'}).slice(-1)[0];
 var active=state.sessions.find(function(s){return ['active','paused'].includes(s.status)});
 var html='';
 if(active){
  var done=Object.keys(active.attempts||{}).length;
  var cname=(courses.find(function(c){return c[0]===active.courseId})||[])[1]||active.courseId;
  html='<div class="ls-main"><span class="ls-tag">继续上次</span><div><b>'+esc(cname)+'</b><span>已完成 '+done+'/'+active.items.length+' 题 · 等待继续</span></div><button class="primary" id="lsResume">继续训练 →</button></div>';
 }else if(ls){
  var done=Object.keys(ls.attempts||{}).length;
  var cname=(courses.find(function(c){return c[0]===ls.courseId})||[])[1]||ls.courseId;
  html='<div class="ls-main"><span class="ls-tag ls-tag-done">上次学习</span><div><b>'+esc(cname)+'</b><span>完成 '+done+'/'+ls.items.length+' 题 · '+(ls.completedAt?new Date(ls.completedAt).toLocaleDateString():'已结束')+'</span></div><button id="lsRetry">再练一轮</button></div>';
 }
 if(html){el.innerHTML=html;el.hidden=false}else{el.hidden=true}
 var rb=document.getElementById('lsResume');
 if(rb)rb.onclick=function(){var s=state.sessions.find(function(x){return ['active','paused'].includes(x.status)});if(!s)return;session=s;session.status='active';undoPoint=session.undoPoint||null;persist();route('train')};
 var t=document.getElementById('lsRetry');
 if(t)t.onclick=function(){enterCourse(ls.courseId);route('detail')};
}
"""
js = js.rstrip()
assert js.endswith("init();")
js = js[: -len("init();")] + ph_funcs + "init();\n"

# ---------- transform phonics body: wrap in #phonicsApp ----------
assert '<main class="app">' in phonics_body
# Remove the standalone home section entirely: courses page is the entry.
home_start = phonics_body.find('<section id="home" class="view">')
home_end = phonics_body.find('<section id="courses"', home_start)
if home_start < 0 or home_end < 0:
    raise RuntimeError('phonics home section boundaries missing')
phonics_body = phonics_body[:home_start] + phonics_body[home_end:]
# Navigation: replace the standalone phonics brand header with the workbench-standard back button,
# so the phonics module looks and behaves like the english/chinese modules.
_old_header = '<header class="top"><div class="brand"><span class="brand-mark">a</span><div>小小拼读<small>PHONICS TOGETHER</small></div></div><nav class="nav" aria-label="主导航"><button data-go="home">首页</button><button data-go="courses">选择课程</button><button data-go="records">历史</button><button data-go="data">数据</button></nav></header>'
assert _old_header in phonics_body
phonics_body = phonics_body.replace(_old_header, '<button class="back" type="button" onclick="window.__WB&&window.__WB.route(\'learn\')">← 返回学习</button>', 1)
# The courses page is the landing view: drop its redundant "back home" button.
_old_courses_back = '</div><button data-go="home">返回首页</button></div><div id="courseGrid"'
assert _old_courses_back in phonics_body
phonics_body = phonics_body.replace(_old_courses_back, '</div></div><div id="courseGrid"', 1)
# Result page: keep the title row clean, no dead home button.
phonics_body = phonics_body.replace('<h1>本轮结果</h1><button data-go="home">首页</button>', '<h1>本轮结果</h1>', 1)
# Records / data pages get a consistent "back to courses" header row, like detail/flash pages.
phonics_body = phonics_body.replace('<section id="records" class="view"><h1>历史</h1>', '<section id="records" class="view"><div class="row between"><h1>历史</h1><button data-go="courses">返回课程</button></div>', 1)
phonics_body = phonics_body.replace('<section id="data" class="view"><h1>本机数据</h1>', '<section id="data" class="view"><div class="row between"><h1>本机数据</h1><button data-go="courses">返回课程</button></div>', 1)
# Insert last-session strip at the top of the courses page, below its header row.
_last_area = '<div id="lastSessionStrip" class="last-session-strip" hidden></div>'
phonics_body = phonics_body.replace('<section id="courses" class="view">', '<section id="courses" class="view">' + _last_area, 1)
# ---------- simplify phonics material selection: random draw only, no manual picking ----------
# Toolbar: drop search / lesson filter / sort / reshuffle / bulk-select buttons.
phonics_body = phonics_body.replace(
    '<div class="toolbar"><div class="row"><input id="search" type="text" placeholder="搜索词语" aria-label="搜索词语"><select id="lessonFilter" aria-label="小课筛选"></select><select id="sort" aria-label="材料排序"><option value="order">课程顺序</option><option value="random">随机顺序</option></select><button id="reshuffle">重新随机</button></div><div class="row"><button id="selectVisible">全选当前可见</button><button id="selectCourse">全选本课</button><button id="clearCourse">清空本课选择</button><span id="counts" class="muted"></span></div><div class="row"><label class="inline">本轮练习 <input id="quantity" type="number" min="1" value="8"></label><span id="selectionM" class="muted"></span><label class="inline"><input type="checkbox" id="randomTrain">训练随机</label><button id="addWord">家长增词</button></div><div id="groups" class="row"></div></div>',
    '<div class="toolbar"><div class="row"><label class="inline">本轮练习 <input id="quantity" type="number" min="1" value="8"> 题</label><span id="selectionM" class="muted"></span><button id="addWord">家长增词</button></div><div id="groups" class="row"></div></div>',
    1,
)
# Bottom bar: single start entry (flash entry removed; random draw covers practice).
phonics_body = phonics_body.replace('<div class="bar-actions"><button id="flashStart">开始闪卡</button><button class="primary" id="trainStart">开始训练</button></div>', '<div class="bar-actions"><button class="primary" id="trainStart">开始练习</button></div>', 1)
phonics_body = phonics_body.replace('<main class="app">', '<div id="phonicsApp" hidden><main class="app">', 1)
assert phonics_body.rstrip().endswith("</main>")
phonics_body = phonics_body.rstrip()[: -len("</main>")] + "</main></div>\n"

# ---------- workbench css ----------
WB_CSS = """
:root{--bg:#f3f0e8;--paper:#fffdf8;--ink:#25322d;--muted:#6e7771;--line:#dcd8cc;--green:#2f6e59;--green-soft:#dfeae2;--orange:#c96b3c;--orange-soft:#f4e2d3;--blue:#496f88;--blue-soft:#dfe8ef;--yellow:#f3d370;--danger:#a84337;--shadow:0 18px 50px rgba(48,59,51,.10);--radius:24px;--space:clamp(16px,2.5vw,32px);font-family:"Microsoft YaHei UI","PingFang SC",system-ui,sans-serif;color:var(--ink);background:var(--bg)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;min-width:320px;background:radial-gradient(circle at 88% -10%,#dce9df 0,transparent 30%),var(--bg)}
button,input,select,textarea{font:inherit}
button{min-height:44px;border:1px solid var(--line);background:var(--paper);color:var(--ink);padding:10px 16px;border-radius:14px;font-weight:700;cursor:pointer;transition:transform .18s cubic-bezier(.16,1,.3,1),background .18s,border-color .18s}
button:hover{border-color:var(--green);transform:translateY(-2px)}button:active{transform:scale(.98)}
button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #d49b34;outline-offset:3px}
.primary{background:var(--green);border-color:var(--green);color:#fff}.secondary{background:var(--green-soft);border-color:transparent;color:#245344}.ghost{background:transparent}.danger{color:var(--danger)}
#phonicsApp[hidden],#workbenchShell[hidden]{display:none!important}
.skip{position:fixed;top:-80px;left:16px;z-index:999;background:var(--ink);color:white;padding:12px}.skip:focus{top:12px}
.shell{max-width:1360px;margin:auto;display:grid;grid-template-columns:220px minmax(0,1fr);gap:var(--space);padding:24px var(--space) 48px}
.side{position:sticky;top:24px;height:calc(100dvh - 48px);display:flex;flex-direction:column;background:#eeeade;border:1px solid #dfdbcf;border-radius:28px;padding:20px}
.brand{display:flex;align-items:center;gap:10px;font-weight:900;font-size:18px}
.brand-mark{width:40px;height:40px;min-width:40px;flex:0 0 40px;display:grid;place-items:center;border-radius:14px;background:var(--green);color:#fff;font-size:22px}
.brand small{display:block;color:var(--muted);font-size:10px;letter-spacing:1px;margin-top:3px}
.brand-name{white-space:nowrap}
.side .nav{display:grid;gap:8px;margin-top:42px}
.side .nav button{display:flex;align-items:center;gap:12px;border:0;background:transparent;justify-content:flex-start;color:#53605a;padding:12px 14px}
.side .nav button.active{background:var(--paper);box-shadow:0 8px 24px rgba(48,59,51,.08);color:var(--green)}
.nav-icon{width:24px;text-align:center;font-size:18px}
.child-card{margin-top:auto;border-top:1px solid var(--line);padding-top:18px;display:grid;gap:4px;font-size:14px}
.child-card b{font-size:16px}.child-card span{color:var(--muted)}
.main{min-width:0}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:6px 2px 18px}
.topbar .date{color:var(--muted);font-size:13px;letter-spacing:.5px;display:block}
.topbar strong{font-size:22px}
.notice{background:var(--paper);border:1px solid var(--line);border-left:4px solid var(--green);border-radius:14px;padding:12px 16px;margin:0 0 16px;box-shadow:var(--shadow)}
.notice.hide{display:none}
.hidden{display:none!important}
.seed-link{color:#4a6b3a;font-weight:600;text-decoration:underline;cursor:pointer}
.view{display:none}.view.active{display:block}
.eyebrow{font-size:12px;letter-spacing:2px;color:var(--green);font-weight:800;text-transform:uppercase}
h1{font-size:30px;letter-spacing:-.5px;margin:6px 0 10px}h2{font-size:20px;margin:6px 0}h3{font-size:17px;margin:6px 0}
.muted{color:var(--muted);line-height:1.6}
.panel{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:22px;box-shadow:var(--shadow);margin-top:16px}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.between{justify-content:space-between}
.hero{display:grid;grid-template-columns:1.4fr 1fr;gap:30px;background:linear-gradient(135deg,#e6efe4,#dfe8ef);border-radius:28px;padding:36px;min-height:250px}
.hero h1{font-size:38px;line-height:1.3;margin:12px 0}
.hero p{max-width:520px;color:#557063;line-height:1.7}
.hero-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
.orbit{position:relative;width:220px;height:220px}
.orbit span{position:absolute;display:grid;place-items:center;width:84px;height:84px;border-radius:24px;background:var(--paper);box-shadow:var(--shadow);font-size:26px;font-weight:900;animation:floaty 6s ease-in-out infinite}
.orbit span:nth-child(1){top:6px;left:14px;animation-delay:0s}.orbit span:nth-child(2){bottom:30px;left:64px;animation-delay:1.4s;color:var(--orange)}.orbit span:nth-child(3){top:52px;right:2px;animation-delay:2.6s;color:var(--blue)}
@keyframes floaty{0%,100%{transform:translateY(0)}50%{transform:translateY(-14px)}}
.hero-art img{width:220px;height:220px;object-fit:contain;filter:drop-shadow(0 12px 24px rgba(70,90,80,.18))}
.brand-mark{overflow:hidden}
.brand-mark img{width:40px;height:40px;min-width:40px;min-height:40px;flex:0 0 40px;object-fit:contain;display:block}
.module .module-art{position:absolute;right:-8px;bottom:2px;pointer-events:none;opacity:.16}
.module .module-art img{width:110px;height:110px;object-fit:contain}
.play-mascot{width:120px;height:120px;object-fit:contain;filter:drop-shadow(0 8px 18px rgba(70,90,80,.16))}
.done-mascot{text-align:center;margin-top:8px}
.done-mascot img{width:150px;height:150px;object-fit:contain;animation:floaty 4s ease-in-out infinite}
.section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin:28px 0 14px}
#phonicsApp .home-primary{min-width:176px}
#phonicsApp .home-hint{margin:10px 0 0;color:#52625b;font-size:13px}
#phonicsApp .home-layout-clean{grid-template-columns:1.35fr 1fr;align-items:stretch}
#phonicsApp .quick-course-button{width:100%;display:grid;grid-template-columns:76px minmax(0,1fr) 32px;align-items:center;gap:16px;text-align:left;border:0;background:#f8f6ef;padding:16px;border-radius:16px;color:var(--ink)}
#phonicsApp .quick-course-button small{display:block;margin-top:5px;color:#68736d;font-size:13px;font-weight:500}
#phonicsApp .quick-course-button .mini-art{display:grid;place-items:center;min-height:76px}
#phonicsApp .quick-course-button .arrow{font-size:22px;color:var(--green)}
#phonicsApp .home-record-panel #homeRecent{min-height:70px;display:flex;flex-direction:column;justify-content:center;gap:4px}
#phonicsApp .home-groups-disclosure{margin:18px 0 0;border-top:1px solid #dfe3df;padding-top:14px}
#phonicsApp .home-groups-disclosure summary{cursor:pointer;font-weight:800;color:#43544c;list-style:none}
#phonicsApp .home-groups-disclosure summary span{margin-left:10px;font-size:13px;font-weight:500;color:#737d77}
#phonicsApp .home-groups-disclosure #homeGroups{padding-top:12px}
#phonicsApp .last-session-strip{margin:14px 0 4px;background:#fffdf8;border:1px solid #dfe6df;border-left:4px solid #2f6e59;border-radius:16px;padding:14px 18px;box-shadow:0 8px 24px rgba(48,59,51,.06)}
#phonicsApp .last-session-strip .ls-main{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
#phonicsApp .last-session-strip .ls-main>div{flex:1;min-width:180px;display:flex;flex-direction:column;gap:2px}
#phonicsApp .last-session-strip b{font-size:15px}
#phonicsApp .last-session-strip .ls-main span:not(.ls-tag){color:#68736d;font-size:13px}
#phonicsApp .ls-tag{display:inline-grid;place-items:center;padding:5px 10px;border-radius:999px;background:#2f6e59;color:#fff;font-size:12px;font-weight:800;white-space:nowrap}
#phonicsApp .ls-tag-done{background:#e7f0e6;color:#3d5c37}
.today-grid{display:grid;grid-template-columns:minmax(0,3fr) minmax(230px,.82fr);gap:20px;align-items:start}
.task-list{display:grid;gap:12px}
.task{display:grid;grid-template-columns:52px 1fr auto;gap:14px;align-items:center;background:var(--paper);border:1px solid var(--line);border-radius:20px;padding:16px;box-shadow:var(--shadow)}
.task-icon{width:52px;height:52px;border-radius:16px;display:grid;place-items:center;font-weight:900;font-size:18px;color:#fff}
.task.phonics .task-icon{background:var(--blue)}.task.english .task-icon{background:var(--green)}.task.chinese .task-icon{background:var(--orange)}
.task b{font-size:17px}.task p{margin:2px 0 0;color:var(--muted);font-size:13px}
.task .done-badge{color:var(--green);font-weight:800}
.empty{border:1px dashed var(--line);border-radius:18px;padding:26px;text-align:center;color:var(--muted);background:var(--paper)}
.progress-card{background:rgba(255,255,255,.62);border:1px solid rgba(190,181,160,.48);border-radius:16px;padding:16px;box-shadow:0 5px 18px rgba(82,75,57,.06);display:grid;gap:7px;align-content:start;color:#53605b}.progress-card h2{font-size:18px;color:#53605b;margin:0}.progress-card .eyebrow{font-size:11px;color:#7a8a82}.progress-card [data-wb="wrecords"]{font-size:13px;color:#65736c;border-color:rgba(190,181,160,.58);background:rgba(255,255,255,.5);padding:9px 12px}
.progress-card .ring{width:120px;height:120px;border-radius:50%;margin:8px auto;background:conic-gradient(var(--green) 62%,var(--green-soft) 0);display:grid;place-items:center}
.progress-card .ring::after{content:"";width:86px;height:86px;border-radius:50%;background:var(--paper)}
.module-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:18px}
.module{position:relative;overflow:hidden;background:var(--paper);border:1px solid var(--line);border-radius:26px;padding:26px;min-height:300px;display:flex;flex-direction:column;gap:10px;box-shadow:var(--shadow)}
.module .module-art{position:absolute;right:-8px;bottom:2px;font-size:74px;font-weight:900;opacity:.07;letter-spacing:-4px;pointer-events:none}
.module.module-stat,.module .module-stat{font-size:13px;color:var(--muted)}
.module-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:auto}
.module.english{background:linear-gradient(160deg,#f7fbf6,#fffdf8)}.module.chinese{background:linear-gradient(160deg,#fbf4ec,#fffdf8)}.module.phonics{background:linear-gradient(160deg,#eff5f9,#fffdf8)}
.back{margin-bottom:14px}
.workbench-head{display:grid;grid-template-columns:1fr auto;gap:16px;align-items:end}
.summary-strip{display:flex;gap:12px;margin:18px 0;flex-wrap:wrap}
.summary-strip div{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:12px 22px;text-align:center;box-shadow:var(--shadow);min-width:150px}
.summary-strip b{display:block;font-size:26px}.summary-strip span{font-size:12px;color:var(--muted)}
.library-tools{display:grid;grid-template-columns:1fr auto;gap:10px;margin-bottom:14px}
.library-tools input,.library-tools select{min-height:44px;border:1px solid var(--line);border-radius:12px;padding:8px 12px;background:var(--paper)}
.library{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:18px;box-shadow:var(--shadow)}
.library-row{display:grid;grid-template-columns:26px minmax(90px,140px) 90px 1fr auto;gap:12px;align-items:center;padding:10px 6px;border-bottom:1px dashed var(--line)}
.library-row:last-child{border-bottom:0}
.library-row .word{font-weight:800;font-size:17px;overflow-wrap:anywhere}
.library-row .muted{font-size:13px}
.library-row input{width:20px;height:20px}
.lib-bar{position:sticky;bottom:8px;background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:14px;box-shadow:var(--shadow);flex-wrap:wrap}
.play-stage{display:grid;place-items:center;gap:14px;padding:44px 22px;text-align:center}
.play-count{font-size:15px;color:var(--muted);letter-spacing:1px}
.play-status{font-size:26px;font-weight:900}
.play-timer{font-size:64px;font-weight:900;color:var(--green);min-height:80px;font-variant-numeric:tabular-nums}
.play-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
.play-actions button{flex:1;min-width:120px}
.play-note{margin-top:14px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}
.stat{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:16px;text-align:center}
.stat b{display:block;font-size:28px}.stat span{font-size:12px;color:var(--muted)}
.record-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.record-tabs button{border-radius:999px;padding:8px 18px}
.record-tabs button.active{background:var(--green);color:#fff;border-color:var(--green)}
.record-item{display:grid;grid-template-columns:150px 1fr auto;gap:14px;align-items:center;background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:16px;margin-bottom:10px;box-shadow:var(--shadow)}
.record-item>span{color:var(--muted);font-size:13px}
.record-item b{font-size:16px}.record-item p{margin:2px 0 0;color:var(--muted);font-size:13px}
.settings-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:16px}
.setting{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:22px;box-shadow:var(--shadow);display:grid;gap:8px;align-content:start}
dialog{border:0;border-radius:26px;padding:0;max-width:min(560px,94vw);box-shadow:0 30px 80px rgba(48,59,51,.25)}
dialog::backdrop{background:rgba(37,50,45,.45)}
.modal-body{padding:26px;display:grid;gap:12px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.field{display:grid;gap:6px}
.field label{font-size:13px;color:var(--muted);font-weight:700}
.field input,.field select,.field textarea{min-height:44px;border:1px solid var(--line);border-radius:12px;padding:8px 12px;background:var(--paper)}
.field textarea{min-height:120px;font-family:Consolas,monospace}
.field.full{grid-column:1/-1}
.modal-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:6px}
.import-preview{border:1px dashed var(--line);border-radius:14px;padding:12px;font-size:13px;color:var(--muted);max-height:220px;overflow:auto}
.import-preview table{width:100%;border-collapse:collapse}
.import-preview td,.import-preview th{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left}
.check-list{display:grid;grid-template-columns:1fr 1fr;gap:6px;max-height:220px;overflow:auto;padding:2px}
.check-list label{display:flex;gap:8px;align-items:center;font-size:14px;border:1px solid var(--line);border-radius:10px;padding:9px 10px;cursor:pointer;background:var(--paper)}
.check-list label:has(input:checked){border-color:var(--accent);background:color-mix(in srgb,var(--accent) 10%,var(--paper))}
.scope-actions{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 10px}
.scope-actions button{font-size:12px;padding:6px 10px}
.library-bulk{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}
.library-bulk button{font-size:12px;padding:6px 10px}
.plan-item{display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:center;border:1px solid var(--line);border-radius:14px;padding:12px;margin-bottom:8px}
.plan-item b{font-size:15px}.plan-item p{margin:2px 0 0;color:var(--muted);font-size:12px}
/* task row checkbox + module state */
.task.checkable .task-icon{width:auto;min-width:40px;flex:0 0 auto;border:0;background:none;display:grid;place-items:center}
.task-check{display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:14px}
.task-check input{width:20px;height:20px;accent-color:var(--green);cursor:pointer}
.task .title-done{text-decoration:line-through;color:var(--muted)}
.module-state{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:9px;background:var(--green-soft);color:var(--green);font-size:15px;font-weight:700}
.module-state.completed{background:var(--green);color:#fff}
.module-state.inprog{background:#fff3d6;color:#a06b00}
/* heat calendar */
.heat-calendar{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:3px;margin:5px 0 4px;min-width:0;opacity:.82}.heat-dow{display:contents}.heat-dow span{font-size:10px;color:#88948e;text-align:center;line-height:15px;min-width:0}
.heat-cell{aspect-ratio:1;border-radius:5px;background:rgba(242,239,231,.66);border:1px solid rgba(190,181,160,.42);display:grid;place-items:center;font-size:10px;color:#78857f;cursor:pointer;min-height:20px;min-width:0;width:100%;padding:0;box-sizing:border-box}.heat-cell.lv1{background:rgba(216,236,223,.72)}.heat-cell.lv2{background:rgba(168,216,187,.78)}.heat-cell.lv3{background:rgba(111,191,146,.82)}.heat-cell.lv4{background:rgba(47,110,89,.82);color:#fff}
.heat-cell.other{visibility:hidden}
.heat-cell.lv1{background:#d8ecdf}.heat-cell.lv2{background:#a8d8bb}.heat-cell.lv3{background:#6fbf92}.heat-cell.lv4{background:#2f6e59;color:#fff}
.heat-cell.today{outline:1.5px solid #7caa91;outline-offset:1px}
.heat-cell:hover{filter:brightness(.96)}
.heat-legend{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--muted);margin-bottom:10px}
.heat-legend i{width:14px;height:14px;border-radius:4px;background:#f2efe7;border:1px solid var(--line);display:inline-block}
.heat-legend i[data-lv="1"]{background:#d8ecdf}.heat-legend i[data-lv="2"]{background:#a8d8bb}.heat-legend i[data-lv="3"]{background:#6fbf92}.heat-legend i[data-lv="4"]{background:#2f6e59}
/* candidate list */
.cand-list{max-height:280px;overflow:auto;border:1px solid var(--line);border-radius:12px;padding:6px}
.cand-item{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:10px}
.cand-item:hover{background:var(--green-soft)}
.cand-item input{width:18px;height:18px;accent-color:var(--green)}
.cand-item.added{opacity:.5}
.cand-item .cand-meta{margin-left:auto;font-size:12px;color:var(--muted)}
.cand-empty{padding:14px;text-align:center;color:var(--muted);font-size:13px}
.cand-item input{width:18px;height:18px;accent-color:var(--green)}.cand-item.added{opacity:.52}.cand-item:has(input:disabled){cursor:default}.candidate-create{display:none}
.segmented{display:flex;border:1px solid var(--line);border-radius:10px;padding:3px;width:max-content;max-width:100%}
.segmented label{cursor:pointer}.segmented input{position:absolute;opacity:0;pointer-events:none}
.segmented span{display:block;padding:7px 12px;border-radius:7px;font-size:13px}
.segmented input:checked+span{background:var(--green);color:#fff}
.week-checks{display:flex;flex-wrap:wrap;gap:8px}
.week-checks label{display:inline-flex;align-items:center;gap:4px;font-size:13px}
.task-more{border:1px solid var(--line);border-radius:9px;background:#fff;padding:4px 10px;font-size:12.5px;color:var(--muted)}
.mobile-nav{display:none}
@media(max-width:980px){.shell{grid-template-columns:1fr;padding:18px 22px 92px}.side{position:static;height:auto;display:block;padding:16px}.side .brand{display:inline-flex}.side .nav{display:flex;float:right;margin:0}.side .nav button{justify-content:center;padding:10px 12px}.child-card{display:none}.today-grid{grid-template-columns:1fr}.module-grid{grid-template-columns:1fr 1fr}.summary-strip{grid-template-columns:repeat(3,1fr)}.record-item{grid-template-columns:1fr auto}.record-item>span{grid-column:1/-1}.settings-grid{grid-template-columns:1fr}}
@media(max-width:680px){body{padding-bottom:76px}.shell{padding:12px 14px 90px}.side{background:transparent;border:0;padding:5px 2px}.side .nav{display:none}.brand small{display:none}.topbar{margin:10px 2px 14px}.topbar>button{display:none}.hero{grid-template-columns:1fr;padding:28px 22px;border-radius:26px}.hero h1{font-size:29px}.orbit{display:none}.today-grid{display:block}.progress-card{margin-top:14px}.module-grid{display:block}.module{min-height:0;margin-bottom:14px}.workbench-head{grid-template-columns:1fr}.summary-strip{grid-template-columns:repeat(3,1fr)}.summary-strip div{padding:12px 8px}.summary-strip b{font-size:18px}.library-tools{grid-template-columns:1fr}.library-row{grid-template-columns:26px 1fr auto}.library-row>:nth-child(3),.library-row>:nth-child(4){display:none}.form-grid{grid-template-columns:1fr}.field.full{grid-column:auto}.check-list{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}.play-timer{font-size:52px}.record-item{grid-template-columns:1fr auto}.settings-grid{grid-template-columns:1fr}.mobile-nav{position:fixed;display:grid;grid-template-columns:repeat(4,1fr);left:10px;right:10px;bottom:max(8px,env(safe-area-inset-bottom));padding:7px;background:#fffdf8;border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow);z-index:400}.mobile-nav button{border:0;background:transparent;padding:6px;font-size:12px;min-height:52px}.mobile-nav button span{display:block;font-size:18px}.mobile-nav button.active{color:var(--green);background:var(--green-soft)}.orbit span{animation:none}#phonicsApp #detail .bar{bottom:calc(92px + env(safe-area-inset-bottom));width:calc(100% - 28px);left:14px;transform:none}#phonicsApp #detail{padding-bottom:calc(176px + env(safe-area-inset-bottom))}.lib-bar{bottom:calc(92px + env(safe-area-inset-bottom))}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
"""

# ---------- workbench body ----------
WB_BODY = """
<a class="skip" href="#content">跳到主要内容</a>
<div id="workbenchShell" class="shell">
<aside class="side"><div class="brand"><span class="brand-mark"><img id="brandMascot" src="" alt="芽宝"></span><div><span class="brand-name">家庭学习工作台</span><small>FAMILY LEARNING WORKBENCH</small></div></div><nav class="nav" aria-label="一级导航"><button data-wb="today"><span class="nav-icon">⌂</span>今日</button><button data-wb="learn"><span class="nav-icon">◇</span>学习</button><button data-wb="wrecords"><span class="nav-icon">▤</span>记录</button><button data-wb="more"><span class="nav-icon">•••</span>更多</button></nav><div class="child-card"><b id="childCard">未设置昵称</b><span>本机学习档案</span></div></aside>
<main id="content" class="main"><div class="topbar"><div><span class="date" id="todayDate"></span><strong id="greetTitle">家庭学习工作台</strong></div></div><div id="wbNotice" class="notice hide" role="status" aria-live="polite"></div>
<section id="today" class="view wb"><div class="hero"><div><span class="eyebrow" id="quoteEyebrow">每日好句</span><h1 id="dayQuote" style="font-size:26px;line-height:1.5">今天也是新的一天。</h1><p class="muted" id="quoteSource">原创</p><div class="hero-actions"><button class="primary" id="heroStart">开始今日学习</button><button class="secondary" id="addTaskBtn">添加任务</button></div></div><div class="hero-art" aria-hidden="true"><img id="heroMascot" alt="" src=""></div></div><div class="section-head"><div><span class="eyebrow">TODAY</span><h2>今日任务</h2></div></div><div class="today-grid"><div class="task-list" id="todayTasks"></div><aside class="progress-card"><span class="eyebrow">打卡日历</span><h2 id="heatMonthLabel">本月</h2><div id="heatCalendar" class="heat-calendar"></div><div class="heat-legend"><span>少</span><i data-lv="0"></i><i data-lv="1"></i><i data-lv="2"></i><i data-lv="3"></i><i data-lv="4"></i><span>多</span></div><button data-wb="wrecords">查看学习记录</button></aside></div></section>
<section id="learn" class="view wb"><div><span class="eyebrow">LEARNING</span><h1>选择学习模块</h1><p class="muted">拼读使用预设课程；英语和语文材料由家长导入，各自管理，不混在一起。</p></div><div class="module-grid"><article class="module phonics"><span class="eyebrow">预设课程</span><h2>拼读学习</h2><p>从字母音到综合短句，家长按孩子已学内容选材并带练；拼读模块保留即时反馈。</p><div class="module-stat" id="statPhonics"></div><div class="module-actions"><button class="primary" data-module="phonics">进入拼读</button></div><div class="module-art"><img alt="" src="" data-mascot="09_carry_books"></div></article><article class="module english"><span class="eyebrow">课内单词</span><h2>英语听写</h2><p>导入教材单词，按单元或自定义范围随机抽题，完整单词发音后开始计时。</p><div class="module-stat" id="statEnglish"></div><div class="module-actions"><button class="primary" data-module="english">进入英语</button></div><div class="module-art"><img alt="" src="" data-mascot="05_laptop"></div></article><article class="module chinese"><span class="eyebrow">生字与词语</span><h2>语文听写</h2><p>按课本单元管理生字词，标准普通话播报；多音字先试听确认再进入自动任务。</p><div class="module-stat" id="statChinese"></div><div class="module-actions"><button class="primary" data-module="chinese">进入语文</button></div><div class="module-art"><img alt="" src="" data-mascot="10_glasses_reading"></div></article></div></section>
<section id="moduleEnglish" class="view wb"><button class="back" data-wb="learn">← 返回学习</button><div id="englishBody"></div></section>
<section id="moduleChinese" class="view wb"><button class="back" data-wb="learn">← 返回学习</button><div id="chineseBody"></div></section>
<section id="play" class="view wb"><div class="workbench-head"><div><span class="eyebrow" id="playModuleLabel">听写任务</span><h1>播报作答</h1><p class="muted" id="playMeta"></p></div><button id="playBack">← 暂停并返回</button></div><div class="play-stage panel"><img id="playMascot" class="play-mascot" alt="" src=""><div class="play-count" id="playCount" aria-live="polite"></div><div class="play-status" id="playStatus"></div><div class="play-timer" id="playTimer" aria-hidden="true"></div></div><div class="play-actions"><button id="playReplay">↻ 重播</button><button id="playNext" class="primary">下一题 →</button><button id="playSkip">跳过本题</button><button id="playPause">暂停</button><button id="playEnd" class="danger">结束并完成</button></div><p class="muted play-note">语音确认开始播放后才开始倒计时；切到后台会自动暂停。作答内容不会显示在屏幕上。</p></section>
<section id="playDone" class="view wb"><div><span class="eyebrow">DONE</span><h1>任务完成</h1><p class="muted">只记录完成情况与客观行为，不评对错。</p></div><div id="doneBody" class="panel" aria-live="polite"></div><div class="done-mascot" aria-hidden="true"><img id="doneMascot" alt="" src=""></div><div class="row" style="margin-top:16px"><button id="doneRetry" class="primary">再次创建同类任务</button><button data-wb="today">返回今日</button><button data-wb="wrecords">查看记录</button></div></section>
<section id="wrecords" class="view wb"><div><span class="eyebrow">RECORDS</span><h1>学习记录</h1><p class="muted">三个模块统一聚合，保留任务范围、题目快照、完成进度、跳过与播放异常等客观记录。</p></div><div class="record-tabs"><button class="active" data-rfilter="all">全部</button><button data-rfilter="phonics">拼读</button><button data-rfilter="english">英语</button><button data-rfilter="chinese">语文</button></div><div id="wrecordList"></div></section>
<section id="more" class="view wb"><div><span class="eyebrow">SETTINGS</span><h1>更多</h1></div><div class="settings-grid"><article class="setting"><h2>孩子档案</h2><p class="muted" id="childProfile"></p><button id="editChild">编辑档案</button></article><article class="setting"><h2>播报与间隔</h2><p class="muted" id="audioSummary"></p><button data-open-dialog="wAudio">调整设置</button></article><article class="setting"><h2>预设任务与排期</h2><p class="muted" id="presetsSummary"></p><button data-open-dialog="wPresets">管理预设与排期</button></article><article class="setting"><h2>数据与备份</h2><p class="muted">导出本机备份或恢复数据；导入记录可追溯。</p><button id="wbExport">导出备份</button><label class="row" style="gap:8px">恢复备份 <input type="file" id="wbImport" accept="application/json"></label><div id="backupInfo" class="muted" style="font-size:13px"></div></article></div><div class="panel"><h2>导入记录</h2><div id="importLogList"></div></div></section>
</main></div>
"""

WB_DIALOGS = """
<dialog id="wAudio" class="modal"><form method="dialog" class="modal-body"><span class="eyebrow">播报设置</span><h2>语音与间隔</h2><div class="form-grid"><div class="field"><label for="audioEngine">语音引擎</label><select id="audioEngine"><option value="auto">自动（优先本地高质量）</option><option value="edge">仅本地高质量语音</option><option value="browser">仅浏览器语音</option></select></div><div class="field"><label>当前引擎状态</label><div class="muted" id="audioEngineStatus">检测中…</div></div><div class="field"><label for="zhVoice">中文音色</label><select id="zhVoice"></select></div><div class="field"><label for="zhRate">中文语速</label><select id="zhRate"><option value="0.7">慢 0.7</option><option value="0.8">较慢 0.8</option><option value="0.85">标准 0.85</option><option value="1">常速 1.0</option></select></div><div class="field"><label for="enVoice">英语音色</label><select id="enVoice"></select></div><div class="field"><label for="enRate">英语语速</label><select id="enRate"><option value="0.7">慢 0.7</option><option value="0.8">较慢 0.8</option><option value="0.9">标准 0.9</option><option value="1">常速 1.0</option></select></div><div class="field"><label for="enGap">英语听写间隔</label><select id="enGap"><option>6</option><option>8</option><option>10</option><option>12</option><option>15</option></select> 秒</div><div class="field"><label for="zhGap">语文听写间隔</label><select id="zhGap"><option>8</option><option>10</option><option>12</option><option>15</option></select> 秒</div></div><div class="row"><button type="button" id="audioTestEn">试听英语：apple</button><button type="button" id="audioTestZh">试听中文：山坡</button></div><p class="muted">本地高质量语音使用微软神经音色（晓晓/Jenny 等），自然度远高于浏览器自带语音；服务未启动时自动回退浏览器语音。启动方法：运行 outputs/tts-server-workbench.py。</p><div class="modal-actions"><button value="cancel">取消</button><button class="primary" value="default" id="audioSave" type="button">保存</button></div></form></dialog>
<dialog id="wImport" class="modal"><form method="dialog" class="modal-body"><span class="eyebrow" id="importLabel">导入材料</span><h2 id="importTitle">导入</h2><p class="muted" id="importTemplate"></p><div class="field full"><label for="importFile">选择 XLSX / CSV 文件</label><input id="importFile" type="file" accept=".xlsx,.csv,.txt,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"></div><div class="field full"><label for="importText">或粘贴表格内容（每行一条，逗号/制表符分隔）</label><textarea id="importText" placeholder=""></textarea></div><div class="modal-actions" style="justify-content:flex-start"><button id="importParse" type="button">解析预览</button><button class="primary" id="importCommit" type="button" disabled>提交导入</button></div><div id="wbImportPreview" class="import-preview">解析后会在这里显示预览。</div><div class="modal-actions"><button value="cancel">取消</button></div></form></dialog>
<dialog id="wCreate" class="modal"><form method="dialog" class="modal-body"><span class="eyebrow" id="createLabel">创建听写任务</span><h2 id="createTitle">按范围随机创建</h2><div class="field full"><label>材料范围（不选为全部单元）</label><div class="scope-actions"><button type="button" data-create-units="all">全选单元</button><button type="button" data-create-units="none">清空选择</button><button type="button" data-create-units="invert">反选</button></div><div class="check-list" id="createUnits"></div></div><div class="form-grid"><div class="field"><label for="createCount">题目数量</label><input id="createCount" type="number" min="1" value="10"></div><div class="field"><label for="createMode">推进方式</label><select id="createMode"><option value="auto">自动间隔</option><option value="manual">手动下一题</option></select></div></div><div class="field full"><label><input type="checkbox" id="createReduce" checked> 减少近期重复，优先未练材料</label></div><div class="modal-actions"><button value="cancel">取消</button><button class="primary" value="default" id="createGo" type="button">生成并开始</button></div></form></dialog>
<dialog id="wCandidate" class="modal"><form method="dialog" class="modal-body"><span class="eyebrow">添加任务</span><h2>选择今天要完成的任务</h2><p class="muted">勾选任务后加入今天；完成情况由你在今日任务中手动勾选。</p><div id="candList" class="cand-list"></div><div class="modal-actions"><button value="cancel">取消</button><button class="primary" id="candBatchAdd" type="button">加入今天</button></div></form></dialog>
<dialog id="wPresets" class="modal"><form method="dialog" class="modal-body"><span class="eyebrow">家长管理</span><h2>预设任务库与排期</h2><p class="muted">预设只定义任务名称和排期；完成状态由家长在今日任务中勾选，与学习模块互不关联。</p><div id="presetList"></div><h2 style="margin-top:14px">新增预设</h2><div class="form-grid"><div class="field full"><label for="presetName">任务名称</label><input id="presetName" type="text" maxlength="30" placeholder="如：英语听写"></div><div class="field full"><label>生效星期</label><div class="week-checks"><label><input type="checkbox" value="1"> 一</label><label><input type="checkbox" value="2"> 二</label><label><input type="checkbox" value="3"> 三</label><label><input type="checkbox" value="4"> 四</label><label><input type="checkbox" value="5"> 五</label><label><input type="checkbox" value="6"> 六</label><label><input type="checkbox" value="0"> 日</label></div></div></div><div class="modal-actions"><button value="cancel">关闭</button><button class="primary" id="presetAdd" type="button">添加预设</button></div></form></dialog>
<dialog id="dayDetail" class="modal"><form method="dialog" class="modal-body"><span class="eyebrow">日期详情</span><h2 id="dayDetailTitle">当日任务</h2><div id="dayDetailBody"></div><div class="modal-actions"><button value="cancel" data-day-close>关闭</button></div></form></dialog>
"""

MOBILE_NAV = """
<nav class="mobile-nav" aria-label="手机一级导航"><button data-wb="today"><span>⌂</span>今日</button><button data-wb="learn"><span>◇</span>学习</button><button data-wb="wrecords"><span>▤</span>记录</button><button data-wb="more"><span>•••</span>更多</button></nav>
"""

# ---------- workbench js ----------
WB_JS = r"""
(function(){
'use strict';
var WBKEY='family-learning-workbench-state-v1';
var PHKEY='phonics-parent-tool-state-v4';
var GRADE3_SEED={GRADE3_SEED_JSON};
var GRADE3_ZH_SEED={GRADE3_ZH_SEED_JSON};
function $(id){return document.getElementById(id)}
function qsa(sel){return Array.prototype.slice.call(document.querySelectorAll(sel))}
function todayKey(){var d=new Date();return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
function weekStartKey(){var d=new Date();d.setDate(d.getDate()-((d.getDay()+6)%7));return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
function uid(p){return p+'-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,7)}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function shuffle(a){for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=a[i];a[i]=a[j];a[j]=t}return a}
var WBVIEWS=['today','learn','wrecords','more','moduleEnglish','moduleChinese','play','playDone'];
var MODNAME={phonics:'拼读学习',english:'英语听写',chinese:'语文听写'};
var W=null;
var libSel={english:{},chinese:{}};
var libFilter={english:{q:'',unit:'all'},chinese:{q:'',unit:'all'}};
var P={task:null,timer:null,countdown:0,lock:false,errIdx:-1};
var lastTaskFilter='all';

function wNotice(text){var n=$('wbNotice');n.textContent=text;n.classList.remove('hide');clearTimeout(window.__wbNoticeTimer);window.__wbNoticeTimer=setTimeout(function(){n.classList.add('hide')},3200)}
function defaultState(){return{schema_version:2,child:{id:'child-main',name:'',grade:'三年级'},settings:{enGap:8,zhGap:10,enRate:0.9,zhRate:0.85,enVoice:'',zhVoice:'',engine:'auto',zhVoiceEdge:'zh-CN-XiaoxiaoNeural',enVoiceEdge:'en-US-JennyNeural'},english:{entries:[],batches:[]},chinese:{entries:[],batches:[]},plans:[],presets:[],tasks:[],importLog:[]}}
function wPersist(){try{W.updatedAt=new Date().toISOString();localStorage.setItem(WBKEY,JSON.stringify(W));return true}catch(e){wNotice('本机保存失败，请先导出备份。');return false}}
function migrateState(x){
 if(!x.presets||!Array.isArray(x.presets))x.presets=[];
 if(!x.plans||!Array.isArray(x.plans))x.plans=[];
 if(!x.settings)x.settings={};
 if(typeof x.settings.enRate!=='number')x.settings.enRate=0.9;
 if(typeof x.settings.zhRate!=='number')x.settings.zhRate=0.85;
 if(typeof x.settings.enVoice!=='string')x.settings.enVoice='';
 if(typeof x.settings.zhVoice!=='string')x.settings.zhVoice='';
 if(typeof x.settings.engine!=='string')x.settings.engine='auto';
 if(typeof x.settings.zhVoiceEdge!=='string'||!x.settings.zhVoiceEdge)x.settings.zhVoiceEdge='zh-CN-XiaoxiaoNeural';
 if(typeof x.settings.enVoiceEdge!=='string'||!x.settings.enVoiceEdge)x.settings.enVoiceEdge='en-US-JennyNeural';
 (x.tasks||[]).forEach(function(t){
  if(t.kind!=='manual'&&t.kind!=='module')t.kind='module';
  if(t.status==='done'||t.status==='finished')t.status='completed';
  if(t.status==='removed'){t.status='cancelled'}
 });
 return x;
}
function wLoad(){try{var raw=localStorage.getItem(WBKEY);if(raw){var x=JSON.parse(raw);if(x&&x.settings&&x.english&&x.chinese&&Array.isArray(x.tasks)){x.schema_version=2;return migrateState(x)}}}catch(e){}return defaultState()}

function phState(){try{if(typeof state!=='undefined'&&state)return state}catch(e){}return null}
function pauseIfPlaying(silent){if(P.task&&P.task.status==='active'){pausePlay(true)}}

function wbRoute(id){if(WBVIEWS.indexOf(id)<0)id='today';
 if($('play')&&P.task&&P.task.status==='active'&&id!=='play'&&id!=='playDone'){pausePlay(true)}
 if(typeof phLeave==='function')phLeave();
 qsa('.view.wb').forEach(function(v){v.classList.toggle('active',v.id===id)});
 qsa('[data-wb]').forEach(function(b){var act=b.getAttribute('data-wb')===id;b.classList.toggle('active',act);b.setAttribute('aria-current',act?'page':'false')});
 if(location.hash.slice(1)!==id)location.hash=id;
 if(id==='today')renderToday();
 if(id==='learn')renderLearn();
 if(id==='moduleEnglish')renderLibrary('english');
 if(id==='moduleChinese')renderLibrary('chinese');
 if(id==='wrecords')renderRecords(lastTaskFilter);
 if(id==='more')renderMore();
 if(id==='play')renderPlay();
 window.scrollTo({top:0,behavior:'smooth'});
}
function openModule(type){
 if(type==='phonics'){
   pauseIfPlaying();
   qsa('.view.wb').forEach(function(v){v.classList.remove('active')});
   qsa('[data-wb]').forEach(function(b){b.classList.toggle('active',b.getAttribute('data-wb')==='learn')});
   if(typeof phEnter==='function')phEnter('courses');
   if(location.hash.slice(1)!=='ph/courses')location.hash='ph/courses';
   window.scrollTo({top:0,behavior:'smooth'});
 }else{
   wbRoute(type==='english'?'moduleEnglish':'moduleChinese');
 }
}

/* ---------- sampling ---------- */
function lastPracticedMap(){var m={};(W.tasks||[]).forEach(function(t){var ts=t.endedAt||t.createdAt||0;(t.items||[]).forEach(function(it){if(it.id&&(m[it.id]==null||ts>m[it.id]))m[it.id]=ts})});return m}
function samplePool(pool,n,reduceRepeat){
 if(!pool.length)return[];
 var arr=pool.slice(0);
 if(!reduceRepeat){shuffle(arr);return arr.slice(0,Math.min(n,arr.length))}
 var lp=lastPracticedMap();
 var fresh=[],used=[];
 arr.forEach(function(e){if(lp[e.id]==null)fresh.push(e);else used.push(e)});
 shuffle(fresh);
 used.sort(function(a,b){return (lp[a.id]||0)-(lp[b.id]||0)});
 var out=fresh.concat(used);
 return out.slice(0,Math.min(n,out.length));
}
function entriesOf(mod){return W[mod].entries}
function unitsOf(mod){var s=[];entriesOf(mod).forEach(function(e){if(s.indexOf(e.unit)<0)s.push(e.unit)});return s.sort()}
function buildTask(mod,units,count,source,planId,reduceRepeat,mode){
 var pool=entriesOf(mod).filter(function(e){return !units||!units.length||units.indexOf(e.unit)>=0});
 if(!pool.length)return null;
 var sampled=samplePool(pool,count,reduceRepeat);
 if(!sampled.length)return null;
 var gap=mod==='english'?W.settings.enGap:W.settings.zhGap;
 var items=sampled.map(function(e){return{id:e.id,text:mod==='english'?e.word:e.text,reading:e.reading||'',meaning:e.meaning||''}});
 var label=!units||!units.length?'全部材料':units.join('、');
 return{id:uid('t'),module:mod,kind:'module',source:source||'temp',planId:planId||null,presetId:null,dateKey:todayKey(),title:MODNAME[mod]+' · '+label,rangeLabel:label,units:units||[],count:count,reduceRepeat:!!reduceRepeat,mode:mode||'auto',gap:gap,items:items,index:0,status:'pending',skips:[],audioErrors:[],startedAt:null,endedAt:null,activeMs:0,curStart:null,sortOrder:0,createdAt:Date.now()};
}
/* ---------- schedule: idempotent today-instance generation ---------- */
function presetMatchesToday(preset){
 if(!preset.enabled)return false;
 var r=preset.rule;if(!r)return false;
 var d=new Date();
 if(r.startDate&&todayKey()<r.startDate)return false;
 if(r.endDate&&todayKey()>r.endDate)return false;
 var dow=String(d.getDay());
 return(!r.weekdays||!r.weekdays.length||r.weekdays.indexOf(dow)>=0);
}
function ensureTodayInstances(){
 var changed=false;
 (W.presets||[]).forEach(function(preset){
  if(!presetMatchesToday(preset))return;
  /* idempotent key: child+date+preset, keeps cancelled placeholder from auto-revival */
  var exists=W.tasks.some(function(t){return t.presetId===preset.id&&t.dateKey===todayKey()});
  if(exists)return;
  var t={id:uid('t'),module:null,kind:'manual',source:'preset',presetId:preset.id,planId:null,dateKey:todayKey(),title:preset.name||'任务',note:preset.note||'',status:'pending',completedAt:null,createdAt:Date.now()};
  W.tasks.push(t);changed=true;
 });
 if(changed)wPersist();
 return changed;
}

/* ---------- today ---------- */
function taskStats(t){var answered=t.index||0;var skipped=(t.skips||[]).length;var total=(t.items||[]).length;var completed=Math.max(0,answered-skipped);var remaining=total-answered;return{answered:answered,skipped:skipped,completed:completed,remaining:remaining}}
function fmtDur(ms){if(!ms||ms<0)ms=0;var s=Math.round(ms/1000);var m=Math.floor(s/60);return m?(''+m+' 分 '+(s%60)+' 秒'):(''+s+' 秒')}
function taskSummary(t){var st=taskStats(t);var parts=['完成 '+st.completed+'/'+(t.items||[]).length];if(st.skipped)parts.push('跳过 '+st.skips);if((t.audioErrors||[]).length)parts.push('播放异常 '+t.audioErrors.length);if(t.status==='completed')parts.push('用时 '+fmtDur(t.activeMs));return parts.join(' · ')}
function instanceDone(t){
 if(!t||t.status==='cancelled')return false;
 return t.status==='completed';
}
function todayTasks(){return W.tasks.filter(function(t){return t.dateKey===todayKey()&&t.status!=='cancelled'&&(t.kind==='manual'||t.title&&!t.module)})}
function renderToday(){
 ensureTodayInstances();
 var tasks=todayTasks();
 tasks.sort(function(a,b){var rank=function(t){var done=t.kind==='manual'?t.status==='completed':instanceDone(t);return done?3:(t.status==='active'||t.status==='paused'?0:(t.status==='pending'?1:2))};return rank(a)-rank(b)||a.createdAt-b.createdAt});
 var html=tasks.map(function(t){
  var done=t.status==='completed';
  var left='<label class="task-check"><input type="checkbox" data-task-toggle="'+t.id+'" '+(done?'checked':'')+' aria-label="'+esc(t.title||'任务')+'：完成状态"></label>';
  var name=t.title||'未命名任务';
  var meta=(t.note||'')+(t.source==='preset'?' · 预设':'');
  var btn='<button class="task-more" data-task-more="'+t.id+'">更多</button>';
  return '<article class="task checkable manual"><div class="task-icon">'+left+'</div><div><b class="'+(done?'title-done':'')+'">'+esc(name)+'</b><p>'+esc(meta||' ')+'</p></div>'+btn+'</article>';
 }).join('');
 if(!tasks.length)html='<div class="empty">今天还没有任务。点击“添加今日任务”从候选中选择，或到“更多 → 预设任务与排期”设置排期。</div>';
 $('todayTasks').innerHTML=html;
 var hero=$('heroStart');
 hero.classList.add('hidden');
 $('greetTitle').textContent=W.child.name?W.child.name+'，出发啦！':'今天也开始学习吧！';
 $('childCard').textContent=(W.child.name||'未设置昵称')+' · '+W.child.grade;
 renderHeatCalendar();
 renderDayQuote();
}
function heatLevel(n){return n<=0?0:(n===1?1:(n===2?2:(n<=4?3:4)))}
function doneCountByDate(){
 var m={};
 (W.tasks||[]).forEach(function(t){
  if(!t.dateKey||t.status==='cancelled'||(t.module&&t.kind!=='manual'))return;
  var done=t.status==='completed';
  if(done)m[t.dateKey]=(m[t.dateKey]||0)+1;
 });
 return m;
}
var heatAnchor=null;
function renderHeatCalendar(){
 var base=heatAnchor?new Date(heatAnchor+'T00:00:00'):new Date();
 var y=base.getFullYear(),mo=base.getMonth();
 var first=new Date(y,mo,1);
 var days=new Date(y,mo+1,0).getDate();
 var startDow=(first.getDay()+6)%7;
 var counts=doneCountByDate();
 var cells='';
 var dows=['一','二','三','四','五','六','日'];
 cells+='<div class="heat-dow">'+dows.map(function(x){return'<span>'+x+'</span>'}).join('')+'</div>';
 for(var i=0;i<startDow;i++)cells+='<div class="heat-cell other" aria-hidden="true"></div>';
 for(var d=1;d<=days;d++){
  var dk=y+'-'+('0'+(mo+1)).slice(-2)+'-'+('0'+d).slice(-2);
  var lv=heatLevel(counts[dk]||0);
  var isToday=dk===todayKey();
  var isFuture=dk>todayKey();
  var title=dk+'：完成 '+(counts[dk]||0)+' 个任务';
  cells+='<button type="button" class="heat-cell lv'+lv+(isToday?' today':'')+'" data-heat-date="'+dk+'" '+(isFuture?'disabled':'')+' aria-label="'+title+'" title="'+title+'">'+d+'</button>';
 }
 $('heatCalendar').innerHTML=cells;
 $('heatMonthLabel').textContent=y+' 年 '+(mo+1)+' 月';
}
function renderDayQuote(){
 var qs=['每天进步一点点，慢慢就会走得很远。','认真做完一件事，比匆忙做完三件事更棒。','不怕慢，就怕站。今天继续出发。','把今天的任务一件件画上勾，就是最好的收尾。','学习像种小树，天天浇一点水，就会长高。','今天多认识一个词，明天就多一分底气。','安静的十分钟，也能带来大大的收获。'];
 var d=new Date();
 var idx=(d.getFullYear()*372+(d.getMonth()+1)*31+d.getDate())%qs.length;
 $('dayQuote').textContent=qs[idx];
 $('quoteSource').textContent='原创短句 · 离线可用';
}

/* ---------- learn ---------- */
function renderLearn(){
 var ph=phState();
 var phReview=0;
 try{if(ph&&typeof latestByItem==='function'){var m=latestByItem();phReview=Array.from(m.values()).filter(function(a){return a.judgement==='prompted'||a.judgement==='needs_help'}).length}}catch(e){}
 $('statPhonics').textContent='7 门课程 · '+(ph?ph.materials.length:107)+' 项材料 · 待复习 '+phReview;
 $('statEnglish').textContent=W.english.entries.length+' 个单词 · '+unitsOf('english').length+' 个单元';
 $('statChinese').textContent=W.chinese.entries.length+' 个字词 · '+unitsOf('chinese').length+' 个单元';
}

/* ---------- built-in grade-3 seed ---------- */
function seedInstalled(){
 var g3=GRADE3_SEED;
 for(var i=0;i<g3.length;i++){
   var exists=W.english.entries.some(function(e){return e.word.toLowerCase()===g3[i].word.toLowerCase()&&e.unit===g3[i].unit});
   if(!exists)return false;
 }
 return g3.length>0;
}
function installGrade3Seed(silent){
 if(!W.english.entries.length){
   var batch={id:uid('b'),name:'沪教牛津版三年级上册（内置）',importedAt:Date.now(),added:GRADE3_SEED.length,skipped:0,invalid:0};
   W.english.entries=GRADE3_SEED.map(function(m,i){return{id:'en-g3-'+i,word:m.word,meaning:m.meaning,unit:m.unit,batchId:batch.id}});
   W.english.batches.push(batch);
   W.importLog.unshift({module:'english',at:Date.now(),added:batch.added,skipped:0,invalid:0});
   wPersist();
   renderLearn();renderMore();
   if(!silent)wNotice('已初始化三年级上册词表：'+GRADE3_SEED.length+' 个单词/短语，共 10 个单元。');
   return true;
 }
 // merge mode: only add entries not present (idempotent by word+unit)
 var added=0;
 var existKeys={};
 W.english.entries.forEach(function(e){existKeys[e.word.toLowerCase()+'|'+e.unit]=true});
 GRADE3_SEED.forEach(function(m,i){
   var k=m.word.toLowerCase()+'|'+m.unit;
   if(existKeys[k])return;
   W.english.entries.push({id:'en-g3-'+i,word:m.word,meaning:m.meaning,unit:m.unit,batchId:W.english.batches.length?W.english.batches[W.english.batches.length-1].id:null});
   existKeys[k]=true;added++;
 });
 if(added){
   var batch={id:uid('b'),name:'沪教牛津版三年级上册（内置）',importedAt:Date.now(),added:added,skipped:GRADE3_SEED.length-added,invalid:0};
   W.english.batches.push(batch);
   W.importLog.unshift({module:'english',at:Date.now(),added:added,skipped:GRADE3_SEED.length-added,invalid:0});
 }else{
   if(!silent)wNotice('三年级词表已存在，无需重复初始化。');
   return false;
 }
 wPersist();renderLearn();renderMore();
 if(!silent)wNotice('已补充三年级词表：新增 '+added+' 条，跳过已存在 '+(GRADE3_SEED.length-added)+' 条。');
 return true;
}
/* ---------- built-in grade-3 chinese seed: auto-installed once on boot, logged as an import batch ---------- */
function zhSeedInstalled(){
 var g=GRADE3_ZH_SEED;
 if(!g||!g.length)return false;
 for(var i=0;i<g.length;i++){
   var hit=g[i];
   var exists=W.chinese.entries.some(function(e){return e.text===hit.text&&e.unit===hit.unit});
   if(!exists)return false;
 }
 return true;
}
function installGrade3ZhSeed(){
 if(zhSeedInstalled())return false;
 var existKeys={};
 W.chinese.entries.forEach(function(e){existKeys[e.text+'|'+e.unit]=true});
 var fresh=GRADE3_ZH_SEED.filter(function(m){return !existKeys[m.text+'|'+m.unit]});
 if(!fresh.length)return false;
 var batch={id:uid('b'),name:'统编版三年级上册语文词语表（内置）',importedAt:Date.now(),added:fresh.length,skipped:GRADE3_ZH_SEED.length-fresh.length,invalid:0};
 var entries=fresh.map(function(m,i){return{id:'zh-g3-'+i,text:m.text,type:m.type||'词语',unit:m.unit,reading:m.reading||'',batchId:batch.id}});
 W.chinese.entries=W.chinese.entries.concat(entries);
 W.chinese.batches.push(batch);
 W.importLog.unshift({module:'chinese',at:Date.now(),added:batch.added,skipped:batch.skipped,invalid:0});
 wPersist();
 return true;
}

/* ---------- xlsx parser (zip + raw deflate, no deps) ---------- */
function inflateRaw(data){
 var CRC=inflateRaw._crc||(inflateRaw._crc=(function(){var t=[],c,n,k;for(n=0;n<256;n++){c=n;for(k=0;k<8;k++)c=(c&1)?(0xEDB88320^(c>>>1)):(c>>>1);t[n]=c>>>0}return t})());
 /* build fixed huffman tables */
 var lenBase=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258];
 var lenExtra=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0];
 var distBase=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577];
 var distExtra=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13];
 var clOrder=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15];
 var pos=0;
 function bit(){var b=(data[pos>>3]|(data[(pos>>3)+1]<<8))>>(pos&7);pos++;return b&1}
 function bits(n){var v=0;for(var i=0;i<n;i++)v|=bit()<<i;return v}
 function buildTree(lengths){
  var counts=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];var i;
  for(i=0;i<lengths.length;i++)counts[lengths[i]]++;
  counts[0]=0;
  var offs=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
  for(i=1;i<16;i++)offs[i]=offs[i-1]+counts[i-1];
  var symbols=[];for(i=0;i<lengths.length;i++)if(lengths[i])symbols[offs[lengths[i]]++]=i;
  return{counts:counts,offs:offs,symbols:symbols}
 }
 function decode(tree){
  var code=0,first=0,index=0;
  for(var len=1;len<=15;len++){
   code|=bit();
   var count=tree.counts[len];
   if(code-first<count)return tree.symbols[index+(code-first)];
   index+=count;first+=count;first<<=1;code<<=1;
  }
  return -1
 }
 var out=new Uint8Array(data.length*12+1024);var outPos=0;
 var litTree,distTree;
 var litLen=new Array(288),i;
 for(i=0;i<144;i++)litLen[i]=8;for(i=144;i<256;i++)litLen[i]=9;for(i=256;i<280;i++)litLen[i]=7;for(i=280;i<288;i++)litLen[i]=8;
 var distLen=new Array(30);for(i=0;i<30;i++)distLen[i]=5;
 litTree=buildTree(litLen);distTree=buildTree(distLen);
 function emit(b){if(outPos>=out.length){var n=new Uint8Array(out.length*2);n.set(out);out=n}out[outPos++]=b}
 function block(){
  var last=bit(),type=bits(2);
  if(type===0){
   pos=(pos+7)&~7;
   var p=pos>>3;
   var len=(data[p]|(data[p+1]<<8));p+=4;
   for(var k=0;k<len;k++)emit(data[p+k]);
   pos=(p+len)<<3;
   return
  }
  if(type===1){/* static trees already built */}
  else if(type===2){
   var hlit=bits(5)+257,hdist=bits(5)+1,hclen=bits(4)+4;
   var cl=new Array(19);for(i=0;i<19;i++)cl[i]=0;
   for(i=0;i<hclen;i++)cl[clOrder[i]]=bits(3);
   var clTree=buildTree(cl);
   var lengths=[];var prev=0;
   while(lengths.length<hlit+hdist){
    var sym=decode(clTree);
    if(sym<0)return false;
    if(sym<16)lengths.push(sym);
    else if(sym===16){var n=3+bits(2);for(var r=0;r<n;r++)lengths.push(prev)}
    else if(sym===17){var n=3+bits(3);for(var r=0;r<n;r++)lengths.push(0)}
    else{var n=11+bits(7);for(var r=0;r<n;r++)lengths.push(0)}
    prev=lengths[lengths.length-1];
   }
   litTree=buildTree(lengths.slice(0,hlit));
   distTree=buildTree(lengths.slice(hlit,hlit+hdist).concat(new Array(30-(hdist)).fill(0)).slice(0,30));
  }
  while(true){
   var sym=decode(litTree);
   if(sym<0)return false;
   if(sym<256)emit(sym);
   else if(sym===256)break;
   else{
    var li=sym-257;
    var len=lenBase[li]+bits(lenExtra[li]);
    var ds=decode(distTree);
    if(ds<0)return false;
    var dist=distBase[ds]+bits(distExtra[ds]);
    for(var k=0;k<len;k++)emit(out[outPos-dist]);
   }
  }
  return true
 }
 var ok=true;
 while(ok){ok=block();if(pos>=(data.length<<3))break}
 return out.subarray(0,outPos)
}
function zipFind(u8,name){
 /* u8: Uint8Array view of the file; all offsets relative to the view */
 var dv=new DataView(u8.buffer,u8.byteOffset,u8.byteLength);
 var len=u8.byteLength;
 var eocd=-1;
 for(var i=len-22;i>=0;i--){
  if(dv.getUint32(i,true)===0x06054b50){eocd=i;break}
 }
 if(eocd<0)return null;
 var count=dv.getUint16(eocd+10,true);
 var off=dv.getUint32(eocd+16,true);
 for(var k=0;k<count;k++){
  if(off+46>len||dv.getUint32(off,true)!==0x02014b50)return null;
  var method=dv.getUint16(off+10,true);
  var csize=dv.getUint32(off+20,true);
  var nl=dv.getUint16(off+28,true);
  var el=dv.getUint16(off+30,true);
  var cl=dv.getUint16(off+32,true);
  var lho=dv.getUint32(off+42,true);
  var fname='';
  for(var j=0;j<nl;j++)fname+=String.fromCharCode(dv.getUint8(off+46+j));
  if(fname===name){
   var ln=dv.getUint16(lho+26,true);
   var le=dv.getUint16(lho+28,true);
   return{method:method,csize:csize,start:lho+30+ln+le}
  }
  off+=46+nl+el+cl;
 }
 return null
}
function zipRead(u8,entry){
 if(!entry)return null;
 var raw=u8.subarray(entry.start,entry.start+entry.csize);
 if(entry.method===8)return inflateRaw(raw);
 return raw
}
function xmlUnescape(s){
 return s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&apos;/g,"'").replace(/&#(\d+);/g,function(_,d){return String.fromCharCode(+d)}).replace(/&amp;/g,'&')
}
function parseXlsx(arrayBuffer){
 try{
  var u8=new Uint8Array(arrayBuffer);
  var ssBytes=zipRead(u8,zipFind(u8,'xl/sharedStrings.xml'));
  var shared=[];
  if(ssBytes){
   var ssXml=new TextDecoder('utf-8').decode(ssBytes);
   var re=/<si>([\s\S]*?)<\/si>/g,m;
   while((m=re.exec(ssXml))){
    var pieces=[],tr=/<t[^>]*>([\s\S]*?)<\/t>/g,t;
    while((t=tr.exec(m[1])))pieces.push(t[1]);
    shared.push(xmlUnescape(pieces.join('')));
   }
  }
  var shBytes=zipRead(u8,zipFind(u8,'xl/worksheets/sheet1.xml'));
  if(!shBytes)return{error:'未找到工作表（请确认是标准 .xlsx 文件）'};
  var xml=new TextDecoder('utf-8').decode(shBytes);
  var rowRe=/<row[^>]*>([\s\S]*?)<\/row>/g,rm;
  var lines=[];
  while((rm=rowRe.exec(xml))){
   var cells=[];
   var cRe=/<c([^>]*?)\/>|<c([^>]*?)>([\s\S]*?)<\/c>/g,cm;
   while((cm=cRe.exec(rm[1]))){
    var attrs=(cm[1]||cm[2]||'');
    var body=cm[3]||'';
    var refM=attrs.match(/r="([A-Z]+)\d+"/);
    var colIdx=refM?colToIdx(refM[1]):cells.length;
    var isInline=attrs.indexOf('t="inlineStr"')>=0;
    var value='';
    if(isInline){
      var tm=body.match(/<t[^>]*>([\s\S]*?)<\/t>/);
      value=tm?tm[1]:'';
    }else{
      var vm=body.match(/<v>([\s\S]*?)<\/v>/);
      value=vm?vm[1]:'';
      if(vm&&attrs.indexOf('t="s"')>=0)value=shared[+value]||'';
    }
    value=xmlUnescape(String(value)).trim();
    while(cells.length<colIdx)cells.push('');
    cells[colIdx]=value;
   }
   var line=cells.join(',');
   if(line.replace(/,/g,'').trim())lines.push(line);
  }
  if(!lines.length)return{error:'工作表没有内容'};
  return lines.join('\n');
 }catch(e){return{error:e.message}}
}
function colToIdx(col){
 var n=0;
 for(var i=0;i<col.length;i++)n=n*26+(col.charCodeAt(i)-64);
 return n-1
}

/* ---------- import ---------- */
var importCtx={module:'english',parsed:null};
function openImport(mod){
 importCtx.module=mod;importCtx.parsed=null;
 $('importLabel').textContent=mod==='english'?'导入英语单词':'导入语文字词';
 $('importTitle').textContent=mod==='english'?'导入英语单词（XLSX / CSV / 粘贴）':'导入语文字词（XLSX / CSV / 粘贴）';
 $('importTemplate').innerHTML=mod==='english'
   ?'每行一条：<b>单词, 中文释义, 单元</b>（表头可省略；释义与单元可留空）。示例：apple,苹果,第1单元'
   :'每行一条：<b>字词, 类型, 单元, 读音</b>（表头可省略；类型默认词语，多音字请填读音）。示例：春风,词语,第1单元';
 $('importText').value='';$('importFile').value='';
 $('wbImportPreview').textContent='解析后会在这里显示预览。';
 $('importCommit').disabled=true;
 $('wImport').showModal();
}
function splitLine(line){
 var delim=line.indexOf('\t')>=0?'\t':(line.indexOf(',')>=0?',':(line.indexOf('，')>=0?'，':null));
 if(!delim)return[line.trim()];
 return line.split(delim).map(function(c){return c.trim()});
}
function parseImportText(text,mod){
 text=String(text||'').replace(/^\uFEFF/,'');
 var lines=text.split(/\r?\n/).map(function(l){return l.trim()}).filter(Boolean);
 if(!lines.length)return{rows:[],header:null};
 var first=splitLine(lines[0]).map(function(c){return c.toLowerCase()});
 var isHeader=first.some(function(c){return ['word','单词','text','词语','内容','content'].indexOf(c)>=0});
 var header=isHeader?first:null;
 var dataLines=isHeader?lines.slice(1):lines;
 var rows=dataLines.map(function(l,i){return{lineNo:i+(isHeader?2:1),cells:splitLine(l)}});
 return{rows:rows,header:header};
}
function mapRow(cells,header,mod){
 var get=function(names,defIdx){
   if(header){for(var i=0;i<header.length;i++){if(names.indexOf(header[i])>=0&&cells[i]!=null)return cells[i]}}
   return cells[defIdx]!=null?cells[defIdx]:'';
 };
 if(mod==='english'){
   return{word:get(['word','单词','内容'],'0'),meaning:get(['meaning','释义','中文','意思'],'1'),unit:get(['unit','单元'],'2')||'未分单元'};
 }
 return{text:get(['text','词语','内容','字词'],'0'),type:get(['type','类型'],'1')||'词语',unit:get(['unit','单元'],'2')||'未分单元',reading:get(['reading','读音','拼音'],'3')||''};
}
function parseImport(){
 var mod=importCtx.module;
 var text=$('importText').value;
 if(!text.trim()){wNotice('请先粘贴内容或选择文件。');return}
 var parsed=parseImportText(text,mod);
 var valid=[],invalid=[],dups=[];
 var existKeys={};
 W[mod].entries.forEach(function(e){existKeys[(mod==='english'?e.word:e.text).toLowerCase()+'|'+e.unit]=true});
 parsed.rows.forEach(function(r){
   var m=mapRow(r.cells,parsed.header,mod);
   if(mod==='english'){
     if(!/^[A-Za-z'’\- ]{1,40}$/.test(m.word)){invalid.push('第'+r.lineNo+'行：单词无效');return}
   }else{
     if(!/^[\u4e00-\u9fff]{1,12}$/.test(m.text)){invalid.push('第'+r.lineNo+'行：字词无效');return}
   }
   var key=(mod==='english'?m.word:m.text).toLowerCase()+'|'+m.unit;
   if(existKeys[key]){dups.push('第'+r.lineNo+'行：'+(mod==='english'?m.word:m.text)+' 已存在');return}
   existKeys[key]=true;
   valid.push(m);
 });
 importCtx.parsed={valid:valid,invalid:invalid,dups:dups};
 var html='<b>解析结果：新增 '+valid.length+' 条'+(dups.length?(' · 跳过重复 '+dups.length+' 条'):'')+(invalid.length?(' · 无效 '+invalid.length+' 条'):'')+'</b>';
 if(valid.length){html+='<table><tr><th>'+(mod==='english'?'单词':'字词')+'</th><th>'+(mod==='english'?'释义':'类型')+'</th><th>单元</th></tr>'+valid.slice(0,30).map(function(m){return'<tr><td>'+esc(mod==='english'?m.word:m.text)+'</td><td>'+esc(mod==='english'?m.meaning:m.type)+'</td><td>'+esc(m.unit)+'</td></tr>'}).join('')+'</table>'}
 if(invalid.length||dups.length){html+='<div style="margin-top:8px">'+invalid.concat(dups).slice(0,20).map(function(s){return esc(s)}).join('<br>')+'</div>'}
 $('wbImportPreview').innerHTML=html;
 $('importCommit').disabled=!valid.length;
}
function commitImport(){
 var mod=importCtx.module,pp=importCtx.parsed;
 if(!pp||!pp.valid.length)return;
 var batch={id:uid('b'),name:'导入 '+todayKey(),importedAt:Date.now(),added:pp.valid.length,skipped:pp.dups.length,invalid:pp.invalid.length};
 var entries=pp.valid.map(function(m,i){
   var id=(mod==='english'?'en-':'zh-')+batch.id.slice(2)+'-'+i;
   return mod==='english'?{id:id,word:m.word,meaning:m.meaning,unit:m.unit,batchId:batch.id}:{id:id,text:m.text,type:m.type,unit:m.unit,reading:m.reading,batchId:batch.id};
 });
 W[mod].entries=W[mod].entries.concat(entries);
 W[mod].batches.push(batch);
 W.importLog.unshift({module:mod,at:Date.now(),added:batch.added,skipped:batch.skipped,invalid:batch.invalid});
 wPersist();
 renderMore();
 wNotice('导入成功：新增 '+batch.added+' 条，重复跳过 '+batch.skipped+' 条。');
 $('wImport').close();
 renderLearn();
 if($('moduleEnglish').classList.contains('active'))renderLibrary('english');
 if($('moduleChinese').classList.contains('active'))renderLibrary('chinese');
}

/* ---------- library ---------- */
function renderLibrary(mod){
 var lib=W[mod];var noun=mod==='english'?'单词':'字词';
 var units=unitsOf(mod);
 var f=libFilter[mod];
 var rows=lib.entries.filter(function(e){
   if(f.unit!=='all'&&e.unit!==f.unit)return false;
   if(f.q){var q=f.q.toLowerCase();var hay=(mod==='english'?e.word+' '+(e.meaning||''):e.text+' '+(e.reading||'')+' '+(e.meaning||'')).toLowerCase();if(hay.indexOf(q)<0)return false}
   return true;
 });
 var html='<div class="workbench-head"><div><span class="eyebrow">'+(mod==='english'?'英语听写':'语文听写')+'</span><h1>'+(mod==='english'?'单词库与任务':'字词库与任务')+'</h1><p class="muted">'+(mod==='english'?'播放完整英文单词，语音确认开始后开始作答计时。':'播放标准普通话；多音字需填读音并试听确认。')+'</p></div><button class="primary" data-module-import="'+mod+'">导入'+noun+'</button></div>';
 html+='<div class="summary-strip"><div><b>'+lib.entries.length+'</b><span>可用'+noun+'</span></div></div>';
 if(!lib.entries.length){
   html+='<div class="empty">还没有'+noun+'。点击右上角"导入'+noun+'"粘贴或上传 CSV 即可。<br>Excel 文件请先另存为 CSV 再导入。</div>';
 }else{
   html+='<div class="library"><div class="library-tools"><input data-lib-search="'+mod+'" aria-label="搜索'+noun+'" placeholder="搜索'+noun+'" value="'+esc(f.q)+'"><select data-lib-unit="'+mod+'" aria-label="筛选单元"><option value="all">全部单元</option>'+units.map(function(u){return'<option value="'+esc(u)+'"'+(f.unit===u?' selected':'')+'>'+esc(u)+'</option>'}).join('')+'</select></div><div class="library-bulk"><button data-lib-bulk="all" data-lib-mod="'+mod+'">选择当前筛选</button><button data-lib-bulk="none" data-lib-mod="'+mod+'">清空当前筛选</button><button data-lib-bulk="clear" data-lib-mod="'+mod+'">清空全部选择</button><span class="muted">当前显示 '+rows.length+' 项</span></div>';
   html+=rows.map(function(e,i){
     var checked=libSel[mod][e.id]?'checked':'';
     var main=mod==='english'?esc(e.word):esc(e.text);
     var sub=mod==='english'?esc(e.meaning||''):esc((e.type||'词语')+(e.reading?(' · 读音：'+e.reading):''));
     return'<div class="library-row"><input type="checkbox" data-lib-item="'+mod+'" data-id="'+esc(e.id)+'" '+checked+' aria-label="选择'+main+'"><span class="word">'+main+'</span><span class="muted">'+esc(e.unit)+'</span><span class="muted">'+sub+'</span><button data-lib-preview="'+mod+'" data-id="'+esc(e.id)+'">试听</button></div>';
   }).join('');
   html+='</div>';
   var selCount=Object.keys(libSel[mod]).filter(function(k){return libSel[mod][k]}).length;
   html+='<div class="lib-bar"><b id="libSelCount_'+mod+'">已选 '+selCount+' 项</b><div class="row"><button data-lib-clear="'+mod+'">清空选择</button><button data-lib-create="'+mod+'">自动选择听写</button><button class="primary" data-lib-start="'+mod+'"'+(selCount?'':' disabled')+'>用所选开始听写</button></div></div>';
 }
 $(mod==='english'?'englishBody':'chineseBody').innerHTML=html;
 var searchEl=$('englishBody').querySelector('[data-lib-search]')||$('chineseBody').querySelector('[data-lib-search]');
}
function previewEntry(mod,id){
 var e=W[mod].entries.filter(function(x){return x.id===id})[0];
 if(!e)return;
 stopWbSpeech();
 var text=mod==='english'?e.word:(e.reading||e.text);
 speakWb(text,mod,function(ok){wNotice(ok?(mod==='english'?'正在试听英语发音。':'正在试听中文发音。'):'试听失败，当前浏览器语音不可用。')});
}
function stopWbSpeech(){try{if(window.speechSynthesis)window.speechSynthesis.cancel()}catch(e){}
 if(WB_AUDIO){try{WB_AUDIO.pause()}catch(e){}WB_AUDIO=null}
}
/* ---------- speech: local neural TTS (edge-tts) first, browser voices as fallback ---------- */
var EDGE_TTS='http://127.0.0.1:8766';
var WB_TTS={status:'unknown'};
var WB_AUDIO=null;
var EDGE_VOICES={zh:[{id:'zh-CN-XiaoxiaoNeural',label:'晓晓 · 女 · 温柔自然'},{id:'zh-CN-YunxiNeural',label:'云希 · 男 · 活泼少年'},{id:'zh-CN-XiaoyiNeural',label:'晓伊 · 女 · 活泼可爱'},{id:'zh-CN-YunyangNeural',label:'云扬 · 男 · 新闻风格'}],en:[{id:'en-US-JennyNeural',label:'Jenny · 女 · 自然对话'},{id:'en-US-GuyNeural',label:'Guy · 男 · 沉稳'},{id:'en-US-AriaNeural',label:'Aria · 女 · 活泼'},{id:'en-GB-SoniaNeural',label:'Sonia · 女 · 英式'}]};
function probeWbTts(){
 if(WB_TTS.status!=='unknown')return Promise.resolve(WB_TTS.status);
 return fetch(EDGE_TTS+'/health',{cache:'no-store'}).then(function(r){WB_TTS.status=r.ok?'online':'offline';return WB_TTS.status}).catch(function(){WB_TTS.status='offline';return WB_TTS.status});
}
function rateToPct(rate){var p=Math.round((Number(rate||1)-1)*100);if(p>100)p=100;if(p<-50)p=-50;return (p>=0?'+':'')+p+'%'}
function wbVoices(){try{return (window.speechSynthesis&&window.speechSynthesis.getVoices)?window.speechSynthesis.getVoices():[]}catch(e){return[]}}
function pickWbVoice(mod){
 var vs=wbVoices();if(!vs.length)return null;
 var lang=mod==='english'?'en':'zh';
 var pref=mod==='english'?['en-US','en-GB','en']:['zh-CN','zh-TW','zh'];
 for(var i=0;i<pref.length;i++){
   var exact=vs.filter(function(v){return v.lang&&v.lang.toLowerCase().indexOf(pref[i].toLowerCase())===0});
   if(exact.length)return exact[0];
 }
 var loose=vs.filter(function(v){return v.lang&&v.lang.toLowerCase().indexOf(lang)===0});
 return loose.length?loose[0]:null;
}
function makeWbUtterance(text,mod,ov){
 ov=ov||{};
 var u=new SpeechSynthesisUtterance(text);
 u.lang=mod==='english'?'en-US':'zh-CN';
 u.rate=Number(ov.rate||(mod==='english'?(W.settings.enRate||0.9):(W.settings.zhRate||0.85)))||0.9;
 var pref=ov.voiceURI!==undefined?ov.voiceURI:(mod==='english'?W.settings.enVoice:W.settings.zhVoice);
 var v=null;
 if(pref&&pref.indexOf('web:')===0){var id=pref.slice(4);v=wbVoices().filter(function(x){return x.voiceURI===id})[0]||null}
 if(!v)v=pickWbVoice(mod);
 if(v){u.voice=v;u.lang=v.lang}
 return u;
}
function speakBrowser(text,mod,ov,cb){
 if(!window.speechSynthesis||!window.SpeechSynthesisUtterance){if(cb)cb(false);return}
 var u=makeWbUtterance(text,mod,ov);
 var done=false;var t=setTimeout(function(){if(!done){done=true;if(cb)cb(false)}},4000);
 u.onstart=function(){done=true;clearTimeout(t);if(cb)cb(true)};
 u.onerror=function(){if(!done){done=true;clearTimeout(t);if(cb)cb(false)}};
 try{window.speechSynthesis.speak(u)}catch(e){clearTimeout(t);if(cb)cb(false)}
}
function playEdge(text,mod,ov,voiceId,cb){
 var rate=rateToPct(Number(ov&&ov.rate)||(mod==='english'?(W.settings.enRate||0.9):(W.settings.zhRate||0.85)));
 var url=EDGE_TTS+'/tts?text='+encodeURIComponent(text)+'&lang='+(mod==='english'?'en':'zh')+'&rate='+encodeURIComponent(rate)+'&voice='+encodeURIComponent(voiceId||'');
 stopWbSpeech();
 var a=new Audio(url);WB_AUDIO=a;
 var done=false;
 var to=setTimeout(function(){if(!done){done=true;if(cb)cb(false)}},7000);
 a.addEventListener('playing',function(){if(done)return;done=true;clearTimeout(to);if(cb)cb(true)});
 a.addEventListener('error',function(){if(done)return;done=true;clearTimeout(to);if(cb)cb(false)});
 var p=a.play();if(p&&p.catch)p.catch(function(){if(done)return;done=true;clearTimeout(to);if(cb)cb(false)});
}
function speakWb(text,mod,cb,ov){
 ov=ov||{};
 var pref=ov.voiceURI!==undefined?ov.voiceURI:(mod==='english'?W.settings.enVoice:W.settings.zhVoice);
 var engine=W.settings.engine||'auto';
 var forceWeb=pref&&pref.indexOf('web:')===0;
 if(!forceWeb&&engine!=='browser'){
   var voiceId=pref&&pref.indexOf('edge:')===0?pref.slice(5):(mod==='english'?W.settings.enVoiceEdge:W.settings.zhVoiceEdge);
   var go=function(){
     if(WB_TTS.status==='online'){
       playEdge(text,mod,ov,voiceId,function(ok){
         if(ok){if(cb)cb(true);return}
         if(engine==='auto')speakBrowser(text,mod,ov,cb);else if(cb)cb(false);
       });
     }else if(engine==='auto')speakBrowser(text,mod,ov,cb);
     else if(cb)cb(false);
   };
   if(WB_TTS.status==='unknown')probeWbTts().then(go);else go();
   return;
 }
 speakBrowser(text,mod,ov,cb);
}
function fillVoiceSelect(selId,mod){
 var sel=$(selId);if(!sel)return;
 var saved=mod==='english'?W.settings.enVoice:W.settings.zhVoice;
 var html='<option value="">自动</option>';
 html+='<optgroup label="本地高质量语音（神经音色）">'+EDGE_VOICES[mod==='english'?'en':'zh'].map(function(v){return '<option value="edge:'+v.id+'"'+(saved==='edge:'+v.id?' selected':'')+'>'+esc(v.label)+'</option>'}).join('')+'</optgroup>';
 var vs=wbVoices();
 var lang=mod==='english'?'en':'zh';
 var list=vs.filter(function(v){return v.lang&&v.lang.toLowerCase().indexOf(lang)===0});
 if(list.length)html+='<optgroup label="浏览器语音（备用）">'+list.map(function(v){return '<option value="web:'+esc(v.voiceURI)+'"'+(saved==='web:'+v.voiceURI?' selected':'')+'>'+esc(v.name+' · '+v.lang)+'</option>'}).join('')+'</optgroup>';
 sel.innerHTML=html;
}
function audioEngineLabel(){
 var e=W.settings.engine||'auto';
 if(e==='browser')return '浏览器语音';
 if(WB_TTS.status==='online')return '本地高质量语音';
 if(WB_TTS.status==='offline')return e==='auto'?'浏览器语音（未检测到本地语音服务）':'本地语音服务未启动';
 return '检测中…';
}

/* ---------- create task dialog ---------- */
var createCtx={module:'english'};
function unitChecks(id,mod){
 var us=unitsOf(mod);
 $(id).innerHTML=us.length?us.map(function(u){return'<label><input type="checkbox" value="'+esc(u)+'"> '+esc(u)+'</label>'}).join(''):'<span class="muted">还没有可选单元，请先导入材料。</span>';
}
function setUnitChecks(id,action){
 var boxes=qsa('#'+id+' input[type="checkbox"]');
 boxes.forEach(function(c,i){if(action==='all')c.checked=true;else if(action==='none')c.checked=false;else if(action==='invert')c.checked=!c.checked});
}
function openCreate(mod){
 createCtx.module=mod;
 if(!W[mod].entries.length){wNotice('请先导入材料，再创建任务。');return}
 $('createLabel').textContent=mod==='english'?'英语听写':'语文听写';
 $('createTitle').textContent='按范围随机创建'+(mod==='english'?'英语听写':'语文默写');
 unitChecks('createUnits',mod);
 $('createCount').value=Math.min(10,W[mod].entries.length);
 $('createReduce').checked=true;
 $('wCreate').showModal();
}
function goCreate(){
 var mod=createCtx.module;
 var units=qsa('#createUnits input:checked').map(function(c){return c.value});
 var count=Math.max(1,Number($('createCount').value)||10);
 var reduce=$('createReduce').checked;
 var mode=$('createMode').value;
 var t=buildTask(mod,units,count,'temp',null,reduce,mode);
 if(!t){wNotice('范围内没有可用材料。');return}
 W.tasks.push(t);wPersist();
 $('wCreate').close();
 startTask(t);
}

/* ---------- play engine ---------- */
function resumeTask(id){
 var t=W.tasks.filter(function(x){return x.id===id})[0];
 if(!t)return;
 if(t.status==='completed'){P.task=t;wbRoute('playDone');renderDone();return}
 startTask(t);
}
function startTask(t){
 t.status='active';
 if(!t.startedAt)t.startedAt=Date.now();
 t.curStart=Date.now();
 wPersist();
 P.task=t;P.errIdx=-1;
 wbRoute('play');
 playCurrent();
}
function renderPlay(){
 var t=P.task;
 if(!t){$('playMeta').textContent='';$('playCount').textContent='';$('playStatus').textContent='没有进行中的任务';$('playTimer').textContent='';return}
 $('playModuleLabel').textContent=MODNAME[t.module]+' · '+t.rangeLabel;
 $('playMeta').textContent=(t.mode==='auto'?(t.module==='english'?'英语':'语文')+'默认间隔 '+t.gap+' 秒':'手动下一题')+' · '+(t.source==='daily'?'每日计划':'临时任务');
 updatePlayTexts();
}
function updatePlayTexts(){
 var t=P.task;if(!t)return;
 $('playCount').textContent='第 '+(t.index+1)+' / '+t.items.length+' 题';
 if(t.status==='paused'){$('playStatus').textContent='已暂停';$('playTimer').textContent='⏸';$('playPause').textContent='继续';return}
 $('playPause').textContent='暂停';
 if(P.countdown>0){$('playStatus').textContent='作答中（可手动下一题）';$('playTimer').textContent=String(P.countdown)}
 else if(P.speaking){$('playStatus').textContent='正在播报…';$('playTimer').textContent='🔊'}
 else{$('playStatus').textContent=P.statusText||'准备播报';$('playTimer').textContent=P.statusText?'':'…'}
}
function playCurrent(){
 var t=P.task;if(!t)return;
 clearInterval(P.timer);P.timer=null;P.countdown=0;P.speaking=true;P.statusText='';
 stopWbSpeech();updatePlayTexts();
 var item=t.items[t.index];
 var text=t.module==='english'?item.text:(item.reading||item.text);
 var idx=t.index;
 var settled=false;
 var to=setTimeout(function(){if(!settled){settled=true;recordAudioError('未确认开始播放');P.speaking=false;P.statusText='播放失败，请家长读题';updatePlayTexts()}},7000);
 speakWb(text,t.module,function(ok){
   if(settled)return;settled=true;clearTimeout(to);
   if(!P.task||P.task!==t||t.index!==idx)return;
   if(ok){
     P.speaking=false;
     if(t.mode==='auto'){startCountdown(t.gap)}else{P.statusText='手动模式：完成后点“下一题”'}
     updatePlayTexts();
   }else{
     recordAudioError('播放失败');P.speaking=false;P.statusText='播放失败，请家长读题';updatePlayTexts();
   }
 });
}
function recordAudioError(reason){
 var t=P.task;if(!t)return;
 if(P.errIdx===t.index)return;
 P.errIdx=t.index;
 t.audioErrors.push({index:t.index,reason:reason,at:Date.now()});
 wPersist();
}
function startCountdown(sec){
 var t=P.task;if(!t)return;
 clearInterval(P.timer);
 P.countdown=sec;
 updatePlayTexts();
 P.timer=setInterval(function(){
   P.countdown--;
   if(P.countdown<=0){clearInterval(P.timer);P.timer=null;P.countdown=0;advance('auto')}
   else updatePlayTexts();
 },1000);
}
function advance(source){
 var t=P.task;if(!t)return;
 if(P.lock)return;
 P.lock=true;setTimeout(function(){P.lock=false},600);
 clearInterval(P.timer);P.timer=null;P.countdown=0;
 stopWbSpeech();
 t.index++;
 wPersist();
 if(t.index>=t.items.length){finishTask()}
 else{playCurrent()}
}
function skipCurrent(){
 var t=P.task;if(!t)return;
 if(t.skips.indexOf(t.index)<0)t.skips.push(t.index);
 advance('skip');
}
function pausePlay(silent){
 var t=P.task;if(!t)return;
 clearInterval(P.timer);P.timer=null;P.countdown=0;
 stopWbSpeech();
 if(t.status==='active'&&t.curStart){t.activeMs+=Date.now()-t.curStart;t.curStart=null}
 t.status='paused';wPersist();
 P.speaking=false;P.statusText='已暂停';
 updatePlayTexts();
 if(!silent)wNotice('已暂停，语音与倒计时已停止。');
}
function resumePlay(){
 var t=P.task;if(!t)return;
 t.status='active';t.curStart=Date.now();wPersist();
 playCurrent();
}
function finishTask(){
 var t=P.task;if(!t)return;
 clearInterval(P.timer);P.timer=null;P.countdown=0;stopWbSpeech();
 if(t.curStart){t.activeMs+=Date.now()-t.curStart;t.curStart=null}
 t.status='completed';t.endedAt=Date.now();wPersist();
 P.task=t;
 wbRoute('playDone');renderDone();
}
function renderDone(){
 var t=P.task;if(!t){$('doneBody').innerHTML='<p class="muted">没有可显示的任务。</p>';return}
 var st=taskStats(t);
 $('doneBody').innerHTML=
  '<p>'+esc(MODNAME[t.module])+' · '+esc(t.rangeLabel)+' · '+t.dateKey+'</p>'+
  '<div class="stats">'+
  '<div class="stat"><b>'+st.completed+'/'+t.items.length+'</b><span>完成</span></div>'+
  '<div class="stat"><b>'+st.skipped+'</b><span>跳过</span></div>'+
  '<div class="stat"><b>'+t.audioErrors.length+'</b><span>播放异常</span></div>'+
  '<div class="stat"><b>'+fmtDur(t.activeMs)+'</b><span>用时</span></div>'+
  '</div>'+
  (st.remaining>0?'<p class="muted">有 '+st.remaining+' 题未播报即结束，未计入完成数。</p>':'')+
  '<p class="muted">本任务只记录完成情况与客观行为，不评对错；如需再练，可点击下方按钮用同一范围重新生成。</p>';
 $('doneRetry').onclick=function(){
   var nt=buildTask(t.module,t.units,t.count,'retry',null,t.reduceRepeat,t.mode);
   if(!nt){wNotice('原范围已无可用材料。');return}
   W.tasks.push(nt);wPersist();startTask(nt);
 };
}

/* ---------- records ---------- */
function renderRecords(filter){
 lastTaskFilter=filter||'all';
 qsa('[data-rfilter]').forEach(function(b){b.classList.toggle('active',b.getAttribute('data-rfilter')===lastTaskFilter)});
 var html='';
 var tasks=W.tasks.slice().reverse();
 if(lastTaskFilter==='all'||lastTaskFilter==='english'||lastTaskFilter==='chinese'){
   var ft=tasks.filter(function(t){return t.kind!=='manual'&&(lastTaskFilter==='all'||t.module===lastTaskFilter)});
   html+=ft.map(function(t){
     var btn=t.status==='completed'
       ?'<button data-task-view="'+t.id+'">查看结果</button>'
       :'<button class="primary" data-task-resume="'+t.id+'">继续作答</button>';
     return'<article class="record-item"><span>'+esc(fmtDate(t.createdAt))+'</span><div><b>'+esc(MODNAME[t.module])+' · '+esc(t.rangeLabel)+'</b><p>'+esc(taskSummary(t))+'</p></div>'+btn+'</article>';
   }).join('');
   if(!ft.length)html+='<div class="empty">这个分类暂时没有听写记录。</div>';
 }
 if(lastTaskFilter==='all'||lastTaskFilter==='phonics'){
   var ph=phState();var phHtml='';
   try{
     if(ph&&ph.sessions&&ph.sessions.length){
       phHtml=ph.sessions.slice(-8).reverse().map(function(s){
         var submitted=0;try{submitted=Object.keys(s.attempts||{}).length}catch(e){}
         return'<article class="record-item"><span>'+esc(fmtDate(s.createdAt||s.created_at||Date.now()))+'</span><div><b>拼读 · '+esc((s.itemSnapshot||[]).length+' 题')+'</b><p>已提交 '+submitted+'/'+((s.itemSnapshot||[]).length)+' · 家长判定与即时反馈</p></div><button data-module="phonics">进入拼读</button></article>';
       }).join('');
     }
     var review=0;
     if(typeof latestByItem==='function'){var m=latestByItem();review=Array.from(m.values()).filter(function(a){return a.judgement==='prompted'||a.judgement==='needs_help'}).length}
     if(review)phHtml+='<article class="record-item"><span>拼读待复习</span><div><b>'+review+' 个材料待复习</b><p>来自拼读训练的家长判定</p></div><button data-module="phonics">去重练</button></article>';
   }catch(e){}
   if(phHtml)html+=phHtml;
   else if(lastTaskFilter==='phonics')html+='<div class="empty">拼读模块还没有训练记录。</div>';
   else html+='<div class="empty">拼读模块还没有训练记录；进入学习 → 拼读学习即可开始。</div>';
 }
 $('wrecordList').innerHTML=html;
}
function fmtDate(ts){try{var d=new Date(ts);return ('0'+d.getMonth()).slice(2)+'-'+('0'+d.getDate()).slice(-2)+' '+('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2)}catch(e){return''}}

/* ---------- more ---------- */
function renderMore(){
 $('childProfile').textContent=(W.child.name?('昵称「'+W.child.name+'」'):'昵称未设置，界面使用中性问候')+' · '+W.child.grade+' · 修改昵称不影响历史记录';
 $('audioSummary').textContent='引擎：'+audioEngineLabel()+' · 英语 '+W.settings.enGap+' 秒 · 语文 '+W.settings.zhGap+' 秒 · 中英文音色语速独立';
 $('presetsSummary').textContent=((W.presets||[]).filter(function(p){return p.enabled}).length)+' 个启用预设 · '+((W.plans||[]).length)+' 个每日计划。生效当天自动生成任务，不补历史。';
 $('enGap').value=String(W.settings.enGap);
 $('zhGap').value=String(W.settings.zhGap);
 $('enRate').value=String(W.settings.enRate||0.9);
 $('zhRate').value=String(W.settings.zhRate||0.85);
 $('audioEngine').value=W.settings.engine||'auto';
 $('audioEngineStatus').textContent=audioEngineLabel();
 fillVoiceSelect('enVoice','english');
 fillVoiceSelect('zhVoice','chinese');
 $('backupInfo').textContent='英语 '+W.english.entries.length+' 条 · 语文 '+W.chinese.entries.length+' 条 · 任务 '+W.tasks.length+' 个';
 $('importLogList').innerHTML=W.importLog.length?W.importLog.slice(0,10).map(function(l){return'<div class="record-item" style="grid-template-columns:120px 1fr"><span>'+esc(fmtDate(l.at))+'</span><div><b>'+MODNAME[l.module]+'导入</b><p>新增 '+l.added+' · 跳过 '+l.skipped+' · 无效 '+l.invalid+'</p></div></div>'}).join(''):'<p class="muted">暂无导入记录。</p>';
 renderPlansList();
 renderPresetList();
}
function renderPlansList(){
 var pl=$('plansList');if(!pl)return;
 pl.innerHTML=W.plans.length?W.plans.map(function(p){
   return'<div class="plan-item"><div><b>'+esc(MODNAME[p.module])+' · '+(p.units&&p.units.length?esc(p.units.join('、')):'全部材料')+'</b><p>每题 '+p.count+' 题 · '+(p.mode==='auto'?'自动间隔':'手动')+(p.reduceRepeat?' · 减少重复':'')+'</p></div><button data-plan-gen="'+p.id+'">添加到今日</button><button data-plan-del="'+p.id+'">删除</button></div>';
 }).join(''):'<p class="muted">还没有计划模板。添加后，每天在“今日”页一键生成固定题目的任务。</p>';
}

/* ---------- backup ---------- */
function wbExport(){
 var payload={app:'family-learning-workbench',version:1,exportedAt:new Date().toISOString(),workbench:W};
 var ph=phState();if(ph)payload.phonics=ph;
 var text=JSON.stringify(payload,null,2);
 var a=document.createElement('a');var u=URL.createObjectURL(new Blob([text],{type:'application/json'}));
 a.href=u;a.download='family-learning-workbench-backup.json';a.click();
 setTimeout(function(){URL.revokeObjectURL(u)},1000);
 wNotice('备份已导出。');
}
function wbImportFile(file){
 if(!file)return;
 if(file.size>5*1024*1024){wNotice('备份文件超过5MB，未导入。');return}
 var r=new FileReader();
 r.onload=function(){
   try{
     var x=JSON.parse(r.result);
     if(x.app!=='family-learning-workbench'||!x.workbench)throw new Error('不是有效的备份文件');
     if(!Array.isArray(x.workbench.tasks)||!x.workbench.settings||!x.workbench.english||!x.workbench.chinese)throw new Error('备份数据结构不完整');
     if(!confirm('导入将覆盖当前英语/语文材料、任务与设置。建议先导出现有备份。确认继续？'))return;
     localStorage.setItem(WBKEY,JSON.stringify(x.workbench));
     if(x.phonics)localStorage.setItem(PHKEY,JSON.stringify(x.phonics));
     wNotice('备份已恢复，即将刷新页面。');
     setTimeout(function(){location.reload()},800);
   }catch(err){wNotice('导入失败，原数据未更改：'+err.message)}
 };
 r.readAsText(file);
}

/* ---------- events ---------- */
document.addEventListener('click',function(e){
 var b;
 b=e.target.closest('[data-wb]');if(b){wbRoute(b.getAttribute('data-wb'));return}
 b=e.target.closest('[data-module]');if(b){openModule(b.getAttribute('data-module'));return}
 b=e.target.closest('[data-open-dialog]');if(b){var d=$(b.getAttribute('data-open-dialog'));if(d)d.showModal();return}
 b=e.target.closest('[data-module-import]');if(b){openImport(b.getAttribute('data-module-import'));return}
 b=e.target.closest('[data-rfilter]');if(b){renderRecords(b.getAttribute('data-rfilter'));return}
 b=e.target.closest('[data-lib-create]');if(b){openCreate(b.getAttribute('data-lib-create'));return}
 b=e.target.closest('[data-create-units]');if(b){setUnitChecks('createUnits',b.getAttribute('data-create-units'));return}
 b=e.target.closest('[data-lib-preview]');if(b){previewEntry(b.getAttribute('data-lib-preview'),b.getAttribute('data-id'));return}
 b=e.target.closest('[data-lib-bulk]');if(b){var bm=b.getAttribute('data-lib-mod');var action=b.getAttribute('data-lib-bulk');if(action==='clear'){libSel[bm]={}}else{var visible=W[bm].entries.filter(function(x){var f=libFilter[bm];if(f.unit!=='all'&&x.unit!==f.unit)return false;if(f.q){var q=f.q.toLowerCase();var hay=(bm==='english'?x.word+' '+(x.meaning||''):x.text+' '+(x.reading||'')+' '+(x.meaning||'')).toLowerCase();if(hay.indexOf(q)<0)return false}return true});visible.forEach(function(x){libSel[bm][x.id]=action==='all'});}renderLibrary(bm);return}
 b=e.target.closest('[data-lib-clear]');if(b){var m=b.getAttribute('data-lib-clear');libSel[m]={};renderLibrary(m);return}
 b=e.target.closest('[data-lib-start]');if(b){startFromSelection(b.getAttribute('data-lib-start'));return}
 b=e.target.closest('[data-task-resume]');if(b){resumeTask(b.getAttribute('data-task-resume'));return}
 b=e.target.closest('[data-task-view]');if(b){P.task=W.tasks.filter(function(t){return t.id===b.getAttribute('data-task-view')})[0]||P.task;wbRoute('playDone');renderDone();return}
 b=e.target.closest('[data-task-more]');if(b){taskMore(b.getAttribute('data-task-more'));return}
 b=e.target.closest('[data-heat-date]');if(b){openDayDetail(b.getAttribute('data-heat-date'));return}
 b=e.target.closest('[data-day-remove]');if(b){removeTask(b.getAttribute('data-day-remove'));return}
 b=e.target.closest('[data-day-readd]');if(b){readdTask(b.getAttribute('data-day-readd'));return}
 b=e.target.closest('[data-day-close]');if(b){var dd=$('dayDetail');if(dd)dd.close();return}
 b=e.target.closest('[data-cand-remove]');if(b){removeTask(b.getAttribute('data-cand-remove'));$('wCandidate').close();renderCandidate();return}
 b=e.target.closest('[data-preset-toggle]');if(b){var pt=W.presets.filter(function(p){return p.id===b.getAttribute('data-preset-toggle')})[0];if(pt){pt.enabled=!pt.enabled;wPersist();renderPresetList();renderMore()}return}
 b=e.target.closest('[data-preset-del]');if(b){W.presets=W.presets.filter(function(p){return p.id!==b.getAttribute('data-preset-del')});wPersist();renderPresetList();renderMore();return}
 b=e.target.closest('[data-plan-gen]');if(b){var gp=W.plans.filter(function(p){return p.id===b.getAttribute('data-plan-gen')})[0];if(gp){if(W.tasks.some(function(t){return t.source==='daily'&&t.planId===gp.id&&t.dateKey===todayKey()&&t.status!=='cancelled'})){wNotice('该计划今日任务已存在，不重复生成。');return}var gt=buildTask(gp.module,gp.units&&gp.units.length?gp.units:[],gp.count,'daily',gp.id,gp.reduceRepeat,gp.mode);if(!gt){wNotice('该范围内没有可用材料。');return}W.tasks.push(gt);wPersist();renderToday();wNotice('已添加今日任务：'+MODNAME[gp.module]+' · '+gt.items.length+' 题。')}return}
 b=e.target.closest('[data-plan-del]');if(b){W.plans=W.plans.filter(function(p){return p.id!==b.getAttribute('data-plan-del')});wPersist();renderPlansList();renderMore();return}
});
document.addEventListener('change',function(e){
 var el=e.target;
 if(el.hasAttribute&&el.hasAttribute('data-lib-item')){
   var mod=el.getAttribute('data-lib-item');
   var id=el.getAttribute('data-id');
   libSel[mod][id]=el.checked;
   var cnt=Object.keys(libSel[mod]).filter(function(k){return libSel[mod][k]}).length;
   var c=$('libSelCount_'+mod);if(c)c.textContent='已选 '+cnt+' 项';
   var start=document.querySelector('[data-lib-start="'+mod+'"]');if(start)start.disabled=!cnt;
   return;
 }
 if(el.hasAttribute&&el.hasAttribute('data-lib-unit')){
   var m2=el.getAttribute('data-lib-unit');
   libFilter[m2].unit=el.value;
   renderLibrary(m2);
   return;
 }
 if(el.hasAttribute&&el.hasAttribute('data-task-toggle')){
   var tid=el.getAttribute('data-task-toggle');
   var t=W.tasks.filter(function(x){return x.id===tid})[0];
   if(t){
     t.status=el.checked?'completed':'pending';
     if(el.checked)t.completedAt=Date.now();else t.completedAt=null;
     wPersist();
     renderToday();
   }
   return;
 }
});
document.addEventListener('input',function(e){
 var el=e.target;
 if(el.hasAttribute&&el.hasAttribute('data-lib-search')){
   var mod=el.getAttribute('data-lib-search');
   libFilter[mod].q=el.value;
   var body=$(mod==='english'?'englishBody':'chineseBody');
   var scroll=window.scrollY;
   renderLibrary(mod);
   var again=body.querySelector('[data-lib-search="'+mod+'"]');
   if(again){again.focus();again.setSelectionRange(again.value.length,again.value.length)}
   window.scrollTo(0,scroll);
 }
});
function startFromSelection(mod){
 var ids=Object.keys(libSel[mod]).filter(function(k){return libSel[mod][k]});
 if(!ids.length){wNotice('请先勾选材料。');return}
 var entries=W[mod].entries.filter(function(e){return ids.indexOf(e.id)>=0});
 var shuffled=shuffle(entries.slice(0));
 var items=shuffled.map(function(e){return{id:e.id,text:mod==='english'?e.word:e.text,reading:e.reading||'',meaning:e.meaning||''}});
 var gap=mod==='english'?W.settings.enGap:W.settings.zhGap;
 var t={id:uid('t'),module:mod,kind:'module',source:'temp',planId:null,presetId:null,dateKey:todayKey(),title:MODNAME[mod]+' · 自选 '+items.length+' 项',rangeLabel:'自选 '+items.length+' 项',units:[],count:items.length,reduceRepeat:false,mode:'auto',gap:gap,items:items,index:0,status:'pending',skips:[],audioErrors:[],startedAt:null,endedAt:null,activeMs:0,curStart:null,createdAt:Date.now()};
 W.tasks.push(t);wPersist();
 startTask(t);
}

/* play buttons */
function bindPlay(){
 $('playNext').onclick=function(){advance('manual')};
 $('playReplay').onclick=function(){var t=P.task;if(t&&t.status==='active'){playCurrent()}};
 $('playSkip').onclick=function(){skipCurrent()};
 $('playPause').onclick=function(){var t=P.task;if(!t)return;if(t.status==='active')pausePlay();else resumePlay()};
 $('playEnd').onclick=function(){finishTask()};
 $('playBack').onclick=function(){pausePlay(true);wbRoute('today')};
}
$('addTaskBtn').onclick=function(){renderCandidate();$('wCandidate').showModal()};
$('candBatchAdd').onclick=function(){commitCandidateAdds()};
$('presetAdd').onclick=function(){
 var name=$('presetName').value.trim();
 if(!name){wNotice('请先填写任务名称。');return}
 var weekdays=qsa('#wPresets .week-checks input:checked').map(function(c){return c.value});
 var preset={id:uid('ps'),name:name,kind:'manual',enabled:true,rule:{weekdays:weekdays,startDate:null,endDate:null}};
 W.presets.push(preset);
 wPersist();
 $('presetName').value='';
 renderPresetList();renderMore();
 wNotice('预设已添加：'+name+'。生效当天会自动生成任务。');
 renderToday();
};
function createManualTask(name,source,presetId){
 var t={id:uid('m'),module:null,kind:'manual',source:source||'candidate',presetId:presetId||null,planId:null,dateKey:todayKey(),title:name,note:'',status:'pending',completedAt:null,createdAt:Date.now()};
 W.tasks.push(t);wPersist();
 renderToday();
 return t;
}
function removeTask(id){
 var t=W.tasks.filter(function(x){return x.id===id})[0];
 if(!t)return;
 if(!confirm('移除“'+(t.kind==='manual'?t.title:(MODNAME[t.module]+' · '+t.rangeLabel))+'”？已产生的记录会保留。'))return;
 t.status='cancelled';
 wPersist();
 renderToday();renderRecords(lastTaskFilter);
 wNotice('任务已移除，历史记录保留。');
}
function readdTask(id){
 var t=W.tasks.filter(function(x){return x.id===id})[0];
 if(!t||t.status!=='cancelled')return;
 t.status=(t.kind==='manual')?'pending':(instanceDoneRaw(t)?'completed':'pending');
 wPersist();
 renderToday();renderRecords(lastTaskFilter);
 var dd=$('dayDetail');if(dd&&dd.open)openDayDetail(t.dateKey);
 wNotice('已重新添加原任务，不创建新实例。');
}
function instanceDoneRaw(t){
 if(t.status!=='completed')return false;
 var st=taskStats(t);
 return st.completed>=1;
}
function taskMore(id){
 var t=W.tasks.filter(function(x){return x.id===id})[0];
 if(!t)return;
 var note=prompt('备注（可选）：',t.note||'');
 if(note==null)return;
 t.note=note.trim();
 wPersist();renderToday();
}
/* ---------- candidate selector ---------- */
function candidateItems(){
 return (W.presets||[]).filter(function(p){return p.enabled}).map(function(p){return{type:'preset',presetId:p.id,name:p.name,meta:'预制任务'}});
}
function renderCandidate(){
 var items=candidateItems();
 var todayAdded=W.tasks.filter(function(t){return t.dateKey===todayKey()});
 var html=items.map(function(it){
  var added;
  added=todayAdded.some(function(t){return t.presetId===it.presetId&&t.status!=='cancelled'});
  var cb=added?'disabled':'';
  var itemId=it.type+':'+it.presetId;
  return '<label class="cand-item'+(added?' added':'')+'"><input type="checkbox" value="'+esc(itemId)+'" '+cb+'><span>'+esc(it.name)+'</span><span class="cand-meta">'+(added?'已添加':'预制任务')+'</span></label>';
 }).join('');
 if(!items.length)html='<div class="cand-empty">任务库为空，请先到“更多 → 预设任务与排期”添加任务。</div>';
 var cancelledToday=W.tasks.filter(function(t){return t.dateKey===todayKey()&&t.status==='cancelled'&&(t.kind==='manual'||!t.module)});
 if(cancelledToday.length)html+=cancelledToday.map(function(t){
  var name=t.title||'未命名任务';
  return '<div class="cand-item added"><span>—</span><span>'+esc(name)+'</span><span class="cand-meta">已取消</span><button data-day-readd="'+t.id+'">重新添加</button></div>';
 }).join('');
 $('candList').innerHTML=html;
}
function commitCandidateAdds(){
 var picked=qsa('#candList input:checked');
 var n=0;
 picked.forEach(function(cb){
  var v=cb.value.split(':');var type=v[0];var key=v.slice(1).join(':');
  if(type==='preset'){
    var p=W.presets.filter(function(x){return x.id===key})[0];
    if(!p)return;
    if(W.tasks.some(function(t){return t.presetId===p.id&&t.dateKey===todayKey()}))return;
    W.tasks.push({id:uid('t'),module:null,kind:'manual',source:'preset',presetId:p.id,planId:null,dateKey:todayKey(),title:p.name||'任务',note:p.note||'',status:'pending',completedAt:null,createdAt:Date.now()});n++;
  }
 });
 wPersist();renderToday();renderCandidate();
 wNotice(n?('已添加 '+n+' 个今日任务。'):'请先勾选候选任务。');
 return n;
}
/* ---------- presets management ---------- */
function renderPresetList(){
 var html=(W.presets||[]).map(function(p){
  var wd=(p.rule&&p.rule.weekdays&&p.rule.weekdays.length)?p.rule.weekdays.map(function(d){return'周'+'日一二三四五六'[+d]}).join('、'):'每天';
  return '<div class="plan-item"><div><b>'+esc(p.name)+'</b><p>手动完成 · '+esc(wd)+'</p></div><button data-preset-toggle="'+p.id+'">'+(p.enabled?'停用':'启用')+'</button><button data-preset-del="'+p.id+'">删除</button></div>';
 }).join('');
 if(!html)html='<p class="muted">还没有预设。添加后，生效当天会自动生成任务。</p>';
 $('presetList').innerHTML=html;
}
/* ---------- day detail ---------- */
function openDayDetail(dk){
 var counts=doneCountByDate();
 var ts=W.tasks.filter(function(t){return t.dateKey===dk&&(t.kind==='manual'||!t.module)});
 var html='<p class="muted">'+dk+' · 完成 '+(counts[dk]||0)+' 个任务</p>';
 if(!ts.length)html+='<p class="muted">这一天没有任务记录。</p>';
 html+=ts.map(function(t){
  var done=t.status==='completed';
  var name=t.title||'未命名任务';
  var state=t.status==='cancelled'?'已取消':(done?'已完成':(t.status==='active'||t.status==='paused'?'进行中':'未完成'));
  var right;
  if(t.status==='cancelled')right=(dk===todayKey())?('<button data-day-readd="'+t.id+'">重新添加</button>'):'';
  else if(dk===todayKey())right=('<button data-day-remove="'+t.id+'">移除</button>');
  else right='';
  return '<div class="cand-item"><span>'+(done?'✅':(t.status==='cancelled'?'—':'⬜'))+'</span><span class="'+(done?'title-done':'')+'">'+esc(name)+'</span><span class="cand-meta">'+state+'</span>'+right+'</div>';
 }).join('');
 $('dayDetailBody').innerHTML=html;
 var dlg=$('dayDetail');
 if(dlg)dlg.showModal();
}
$('audioSave').onclick=function(){
 W.settings.enGap=Number($('enGap').value)||8;
 W.settings.zhGap=Number($('zhGap').value)||10;
 W.settings.enRate=Number($('enRate').value)||0.9;
 W.settings.zhRate=Number($('zhRate').value)||0.85;
 W.settings.engine=$('audioEngine').value||'auto';
 var ev=$('enVoice').value||'',zv=$('zhVoice').value||'';
 W.settings.enVoice=ev;W.settings.zhVoice=zv;
 if(ev.indexOf('edge:')===0)W.settings.enVoiceEdge=ev.slice(5);
 if(zv.indexOf('edge:')===0)W.settings.zhVoiceEdge=zv.slice(5);
 wPersist();renderMore();
 wNotice('播报设置已保存：'+audioEngineLabel()+'。');
 $('wAudio').close();
};
function audioTestCurrent(mod){
 stopWbSpeech();
 var ov={rate:Number($(mod==='english'?'enRate':'zhRate').value)||0.9};
 var selVal=$(mod==='english'?'enVoice':'zhVoice').value||'';
 if(selVal)ov.voiceURI=selVal;
 speakWb(mod==='english'?'apple':'山坡',mod,function(ok){wNotice(ok?'试听中。':'试听失败：本地服务未启动且浏览器语音不可用。')},ov);
}
$('audioTestEn').onclick=function(){audioTestCurrent('english')};
$('audioTestZh').onclick=function(){audioTestCurrent('chinese')};
try{if(window.speechSynthesis&&speechSynthesis.addEventListener)speechSynthesis.addEventListener('voiceschanged',function(){var d=$('wAudio');if(d&&d.open){fillVoiceSelect('enVoice','english');fillVoiceSelect('zhVoice','chinese')}})}catch(e){}
$('editChild').onclick=function(){
 var name=prompt('孩子昵称（1—12 个字符，留空则不显示昵称）',W.child.name||'');
 if(name==null)return;
 name=name.trim();
 var ar=Array.from(name);
 if(ar.length>12){wNotice('昵称最多 12 个字符，未保存。');return}
 var grade=prompt('年级',W.child.grade);
 if(grade==null)return;
 if(name)W.child.name=name;else W.child.name='';
 W.child.grade=grade.trim()||W.child.grade;
 wPersist();renderMore();renderToday();
 wNotice(name?('昵称已更新为「'+name+'」，历史记录不受影响。'):'已清除昵称，界面将使用中性问候。');
};
$('importParse').onclick=parseImport;
$('importCommit').onclick=commitImport;
$('importFile').onchange=function(e){
 var file=e.target.files[0];if(!file)return;
 if(file.size>2*1024*1024){wNotice('文件超过2MB，请分批导入。');e.target.value='';return}
 var isXlsx=/\.xlsx$/i.test(file.name)||/spreadsheetml/.test(file.type);
 var r=new FileReader();
 r.onload=function(){
  if(isXlsx){
   var text=parseXlsx(r.result);
   if(typeof text==='string'&&text.error){wNotice('XLSX 解析失败：'+text.error);e.target.value='';return}
   $('importText').value=text;wNotice('XLSX 已解析，点击“解析预览”。');
  }else{
   $('importText').value=r.result;wNotice('文件已载入，点击“解析预览”。');
  }
 };
 if(isXlsx)r.readAsArrayBuffer(file);else r.readAsText(file);
};
$('createGo').onclick=goCreate;
$('wbExport').onclick=wbExport;
$('wbImport').onchange=function(e){wbImportFile(e.target.files[0]);e.target.value=''};
document.addEventListener('visibilitychange',function(){
 if(document.hidden&&P.task&&P.task.status==='active'){pausePlay(true)}
});
window.addEventListener('hashchange',function(){
 var h=location.hash.slice(1);
 if(!h||h.indexOf('ph/')===0)return;
 if(WBVIEWS.indexOf(h)>=0){
   var cur=qsa('.view.wb').filter(function(v){return v.classList.contains('active')})[0];
   if(!cur||cur.id!==h)wbRoute(h);
 }
});

/* ---------- init ---------- */
W=wLoad();
/* built-in word banks install silently on first run, recorded as import batches; no UI entry by design */
installGrade3Seed(true);
installGrade3ZhSeed();
probeWbTts();
/* migrate: legacy default example name is treated as unset */
if(W.child&&W.child.name==='小宇'){W.child.name=''}
if(W.child&&!W.child.id){W.child.id='child-main'}
if(W.child&&!Object.prototype.hasOwnProperty.call(W.child,'name')){W.child.name=''}
/* mascot assets */
(function(){
 var m=window.MASCOT||{};
 function set(id,key){var el=document.getElementById(id);if(el&&m[key])el.src=m[key]}
 set('brandMascot','01_wave');
 set('heroMascot','11_backpack_walk');
 set('playMascot','02_reading_book');
 set('doneMascot','06_celebrate');
 qsa('[data-mascot]').forEach(function(el){var k=el.getAttribute('data-mascot');if(m[k])el.src=m[k]});
})();
$('todayDate').textContent=new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',weekday:'long'}).format(new Date());
bindPlay();
renderToday();renderLearn();
var initialHash=location.hash.slice(1);
if(initialHash&&initialHash.indexOf('ph/')!==0&&WBVIEWS.indexOf(initialHash)>=0){wbRoute(initialHash)}
else{wbRoute('today')}

/* debug/test hook */
window.__WB={
 get state(){return W},
 get play(){return P},
 route:wbRoute,
 todayKey:todayKey,
 doneCountByDate:doneCountByDate,
 setGap:function(en,zh){W.settings.enGap=en;W.settings.zhGap=zh;wPersist()},
 makeUtterance:function(text,mod){return makeWbUtterance(text,mod)},
 createTask:buildTask,
 startTaskById:function(id){var t=W.tasks.filter(function(x){return x.id===id})[0];if(t)startTask(t)},
 openImport:openImport,
 setImportText:function(t){$('importText').value=t},
 installSeed:installGrade3Seed,
 seedInstalled:seedInstalled,
 installZhSeed:installGrade3ZhSeed,
 zhSeedInstalled:zhSeedInstalled,
 notify:wNotice,
 parseXlsx:parseXlsx
};
})();
"""

html_parts = []
# inject grade-3 seed data into WB_JS
import json
grade3_seed = json.loads((ROOT / "outputs" / "grade3-seed.json").read_text(encoding="utf-8"))
grade3_js = json.dumps(grade3_seed, ensure_ascii=False, separators=(",", ":"))
grade3_zh_seed = json.loads((ROOT / "outputs" / "grade3-chinese-seed.json").read_text(encoding="utf-8"))
grade3_zh_js = json.dumps(grade3_zh_seed, ensure_ascii=False, separators=(",", ":"))
mascot_embed = json.loads((ROOT / "outputs" / "mascot-embed.json").read_text(encoding="utf-8"))
mascot_json = json.dumps(mascot_embed, ensure_ascii=False, separators=(",", ":"))
WB_JS = WB_JS.replace("{GRADE3_SEED_JSON}", grade3_js)
WB_JS = WB_JS.replace("{GRADE3_ZH_SEED_JSON}", grade3_zh_js)
html_parts.append("""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#f3f0e8">
<title>家庭学习工作台 V2.1</title>
<link rel="icon" href="data:,">
<style>
""")
html_parts.append(WB_CSS)
html_parts.append("\n</style>\n<style>\n")
html_parts.append(scoped_css)
html_parts.append("\n</style>\n</head>\n<body>\n")
html_parts.append(WB_BODY)
html_parts.append(phonics_body)
html_parts.append(MOBILE_NAV)
html_parts.append(WB_DIALOGS)
html_parts.append("<script>\n")
html_parts.append(js)
html_parts.append("</script>\n<script>\n")
html_parts.append("var MASCOT=" + mascot_json + ";\n")
html_parts.append(WB_JS)
html_parts.append("</script>\n</body>\n</html>\n")

final_html = "".join(html_parts)
out = ROOT / "outputs" / "family-learning-workbench-v2.html"
out.write_text(final_html, encoding="utf-8")
print("written:", out, len(final_html), "chars")
