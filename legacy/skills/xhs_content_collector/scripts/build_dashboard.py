#!/usr/bin/env python3
"""
聚合 data/xhs_collected 的实际采集结果，生成自包含的「采集系统全景图.html」。

可独立运行：python scripts/build_dashboard.py
也被采集脚本在每次采集结束时自动调用（见 xhs_full_note_collect.py）。
所有数据来自本地实际采集结果，不联网。
"""
from __future__ import annotations
import glob, json, os, re
from collections import defaultdict
from pathlib import Path

ROOT = "data/xhs_collected"
ROSTER = "hermes/tasks/xhs_designers_daily.json"
DISCOVERED = "data/xhs/discovered_candidates.json"
OUT = "data/xhs_collected/采集系统全景图.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>小红书家居素材采集系统 · 全景图</title>
<style>
  :root{--bg:#0f1117;--panel:#1a1d27;--panel2:#222633;--line:#2e3340;--txt:#e8eaf0;--sub:#9aa3b5;--accent:#ff4d6d;--accent2:#4d9fff;--green:#36d399;--amber:#fbbd23;--purple:#a78bfa;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--txt);font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;padding:32px 24px;line-height:1.5}
  .wrap{max-width:1240px;margin:0 auto}
  h1{font-size:26px;font-weight:700;letter-spacing:.5px} h1 .em{color:var(--accent)}
  .meta{color:var(--sub);font-size:13px;margin-top:6px}
  .section-t{font-size:15px;font-weight:600;color:var(--sub);margin:34px 0 14px;text-transform:uppercase;letter-spacing:1px;border-left:3px solid var(--accent);padding-left:10px}
  .kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-top:22px}
  .kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 14px;text-align:center}
  .kpi .v{font-size:28px;font-weight:800;color:var(--accent2)} .kpi .l{font-size:12px;color:var(--sub);margin-top:4px}
  .pipe{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;align-items:stretch}
  .step{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 12px;position:relative;display:flex;flex-direction:column}
  .step .n{position:absolute;top:-10px;left:12px;background:var(--accent);color:#fff;font-size:11px;font-weight:700;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center}
  .step h3{font-size:14px;margin:6px 0 8px} .step p{font-size:11.5px;color:var(--sub);margin-bottom:4px}
  .step .tag{display:inline-block;font-size:10px;background:var(--panel2);color:var(--accent2);border-radius:5px;padding:2px 6px;margin-top:6px;font-family:monospace}
  @media(max-width:1000px){.pipe{grid-template-columns:repeat(2,1fr)}.kpis{grid-template-columns:repeat(3,1fr)}}
  .grid2{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;margin-top:6px}
  @media(max-width:900px){.grid2{grid-template-columns:1fr}}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px} .card h2{font-size:16px;margin-bottom:14px}
  .funnel .bar{margin:10px 0} .funnel .lab{font-size:13px;display:flex;justify-content:space-between;margin-bottom:4px}
  .funnel .track{height:26px;background:var(--panel2);border-radius:6px;overflow:hidden}
  .funnel .fill{height:100%;border-radius:6px;display:flex;align-items:center;padding-left:10px;font-size:12px;font-weight:700;color:#0f1117}
  .top .row{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--line)} .top .row:last-child{border:0}
  .top .rk{width:22px;height:22px;border-radius:50%;background:var(--panel2);color:var(--sub);font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}
  .top .rk.g1{background:var(--accent);color:#fff}.top .rk.g2{background:var(--amber);color:#0f1117}.top .rk.g3{background:var(--purple);color:#fff}
  .top .ti{flex:1;min-width:0} .top .ti .t{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis} .top .ti .b{font-size:11px;color:var(--sub)}
  .top .mx{font-size:12px;color:var(--green);font-weight:700;white-space:nowrap}
  .bl .row{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:12px}
  .bl .nm{width:120px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--sub)}
  .bl .tr{flex:1;height:14px;background:var(--panel2);border-radius:4px;overflow:hidden} .bl .fl{height:100%;background:linear-gradient(90deg,var(--accent2),var(--purple))}
  .bl .vv{width:48px;text-align:right;color:var(--txt);font-weight:600}
  .rules{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:6px}
  .rule{background:var(--panel2);border-radius:8px;padding:10px 12px;font-size:12.5px} .rule b{color:var(--accent)}
  .foot{color:var(--sub);font-size:12px;margin-top:30px;text-align:center;border-top:1px solid var(--line);padding-top:16px}
  .chip{display:inline-block;background:var(--panel2);border-radius:6px;padding:3px 9px;font-size:11px;color:var(--accent2);margin:2px;font-family:monospace}
</style></head>
<body><div class="wrap">
  <h1>小红书 · 家居定制设计 <span class="em">素材采集系统</span> 全景图</h1>
  <div class="meta">登录 → 搜索发现 → 质量判定 → 自动入池 → 反爬采集 → 清洗评分 → 交付　|　数据截至 __DATE__</div>
  <div class="kpis">
    <div class="kpi"><div class="v" id="k1"></div><div class="l">博主数</div></div>
    <div class="kpi"><div class="v" id="k2"></div><div class="l">采集笔记</div></div>
    <div class="kpi"><div class="v" id="k3"></div><div class="l">原图张数</div></div>
    <div class="kpi"><div class="v" id="k4"></div><div class="l">设计师池</div></div>
    <div class="kpi"><div class="v" id="k5"></div><div class="l">发现评估</div></div>
    <div class="kpi"><div class="v" id="k6"></div><div class="l">新入选</div></div>
  </div>
  <div class="section-t">工作流程</div>
  <div class="pipe">
    <div class="step"><span class="n">1</span><h3>🔐 登录态</h3><p>扫码登录，保存 Playwright storage_state</p><p>不读账密 · 不绕验证码</p><span class="tag">xhs_login_auto.py</span></div>
    <div class="step"><span class="n">2</span><h3>🔎 搜索发现</h3><p>关键词搜「用户」：全屋定制/室内设计/家装/别墅/整装</p><span class="tag">discover_accounts.py</span></div>
    <div class="step"><span class="n">3</span><h3>⚖️ 质量判定</h3><p>粉丝≥5千 · 近期图文均赞≥50 · 图文为主</p><p>剔除视频号/低粉号</p></div>
    <div class="step"><span class="n">4</span><h3>📥 自动入池</h3><p>达标账号并入设计师池，去重</p><span class="tag">xhs_designers_daily.json</span></div>
    <div class="step"><span class="n">5</span><h3>🤖 反爬采集</h3><p>模拟真人：随机延时+定期休息</p><p>跳视频/夹带视频/图&lt;3/不相关</p><span class="tag">xhs_full_note_collect.py</span></div>
    <div class="step"><span class="n">6</span><h3>🧹 清洗评分</h3><p>除噪正文+去广告评论</p><p>收藏0.5·点赞0.3·评论0.2 ×时间公平</p><span class="tag">generate_note_copy.py</span></div>
    <div class="step"><span class="n">7</span><h3>📦 交付</h3><p>每篇 采集笔记文案.md + 原图<br>根目录总排名</p><span class="tag">data/xhs_collected</span></div>
  </div>
  <div class="grid2" style="margin-top:24px">
    <div class="card funnel"><h2>📊 账号发现漏斗</h2>
      <div class="bar"><div class="lab"><span>关键词搜索评估</span><span id="f1n"></span></div><div class="track"><div class="fill" style="background:var(--accent2);width:100%" id="f1"></div></div></div>
      <div class="bar"><div class="lab"><span>通过质量门槛</span><span id="f2n"></span></div><div class="track"><div class="fill" style="background:var(--green)" id="f2"></div></div></div>
      <div class="bar"><div class="lab"><span>自动入池并采集</span><span id="f3n"></span></div><div class="track"><div class="fill" style="background:var(--purple)" id="f3"></div></div></div>
      <div class="rules">
        <div class="rule">✅ <b>仅图文</b>，跳过视频笔记</div><div class="rule">✅ 过滤<b>图文夹带视频</b></div>
        <div class="rule">✅ 图片数 <b>≥3 张</b></div><div class="rule">✅ <b>行业相关</b>(标题+正文)</div>
      </div></div>
    <div class="card top"><h2>🏆 Top 优质素材（按收藏）</h2><div id="toplist"></div></div>
  </div>
  <div class="card bl" style="margin-top:18px"><h2>👤 各博主累计收藏（Top 14）</h2><div id="blbars"></div></div>
  <div class="card" style="margin-top:18px"><h2>🛡️ 反爬 / 风控策略</h2>
    <p style="font-size:13px;color:var(--sub)">
      <span class="chip">随机抖动延时 base×(1±0.6)</span><span class="chip">每5账号休息~45s</span>
      <span class="chip">用正常登录态</span><span class="chip">模拟真人点页面</span>
      <span class="chip">不破解签名</span><span class="chip">不绕验证码</span><span class="chip">遇验证即停并报状态</span>
    </p></div>
  <div class="foot">小红书家居定制设计素材采集系统 · 每次采集后自动刷新 · 数据来自本地 data/xhs_collected 实际结果</div>
</div>
<script>
const DATA = __DATA__;
function fmt(n){return n>=10000?(n/10000).toFixed(1)+'万':n}
k1.textContent=DATA.blogger_count;k2.textContent=DATA.note_count;k3.textContent=DATA.image_count;
k4.textContent=DATA.pool_count;k5.textContent=DATA.discovered;k6.textContent=DATA.qualified;
f1n.textContent=DATA.discovered;f1.textContent=DATA.discovered+' 账号';
f2n.textContent=DATA.qualified;f3n.textContent=DATA.qualified;
const r=DATA.discovered?DATA.qualified/DATA.discovered*100:0;
f2.style.width=Math.max(12,r)+'%';f2.textContent=DATA.qualified+' 高质量';
f3.style.width=Math.max(12,r)+'%';f3.textContent=DATA.qualified+' 入池';
toplist.innerHTML=DATA.top.map((t,i)=>`<div class="row"><div class="rk ${i==0?'g1':i==1?'g2':i==2?'g3':''}">${i+1}</div><div class="ti"><div class="t">${t.t}</div><div class="b">${t.b} · 赞${fmt(t.like)} 评${fmt(t.com)}</div></div><div class="mx">藏 ${fmt(t.col)}</div></div>`).join('');
const bl=DATA.bloggers.slice(0,14);const mx=Math.max(1,...bl.map(x=>x.col));
blbars.innerHTML=bl.map(x=>`<div class="row"><div class="nm">${x.b}</div><div class="tr"><div class="fl" style="width:${Math.max(3,x.col/mx*100)}%"></div></div><div class="vv">${fmt(x.col)}</div></div>`).join('');
</script></body></html>"""


def toint(v):
    if v is None: return 0
    if isinstance(v, (int, float)): return int(v)
    m = re.search(r"[\d.]+", str(v))
    return int(float(m.group(0))) if m else 0


def build(today: str | None = None) -> str:
    if today is None:
        # 用最新 metadata 的采集日期，避免依赖系统时钟
        today = "—"
        latest = 0.0
        for mp in glob.glob(f"{ROOT}/*/*/metadata.json"):
            try:
                ts = os.path.getmtime(mp)
                if ts > latest:
                    latest = ts
                    m = json.load(open(mp, encoding="utf-8"))
                    today = (m.get("collected_at") or "")[:10] or today
            except Exception:
                continue

    notes = []
    for mp in glob.glob(f"{ROOT}/*/*/metadata.json"):
        try:
            m = json.load(open(mp, encoding="utf-8"))
        except Exception:
            continue
        b = os.path.basename(os.path.dirname(os.path.dirname(mp)))
        notes.append({"b": b, "title": m.get("title") or "", "like": toint(m.get("like_count")),
                      "col": toint(m.get("collect_count")), "com": toint(m.get("comment_count")),
                      "imgs": toint(m.get("downloaded_image_count"))})
    bloggers = sorted(set(n["b"] for n in notes))

    discovered = qualified = 0
    if os.path.exists(DISCOVERED):
        try:
            disc = json.load(open(DISCOVERED, encoding="utf-8"))
            discovered = len(disc)
            qualified = len({r["user_id"] for r in disc if r.get("qualify")})
        except Exception:
            pass
    pool = 0
    if os.path.exists(ROSTER):
        try:
            pool = len(json.load(open(ROSTER, encoding="utf-8")).get("targets", []))
        except Exception:
            pass

    top = sorted(notes, key=lambda x: x["col"], reverse=True)[:8]
    by = defaultdict(lambda: [0, 0, 0])
    for n in notes:
        by[n["b"]][0] += n["like"]; by[n["b"]][1] += n["col"]; by[n["b"]][2] += 1
    blo = sorted([{"b": k, "like": v[0], "col": v[1], "n": v[2]} for k, v in by.items()],
                 key=lambda x: x["col"], reverse=True)

    data = {"blogger_count": len(bloggers), "note_count": len(notes),
            "image_count": sum(n["imgs"] for n in notes), "discovered": discovered,
            "qualified": qualified, "pool_count": pool,
            "top": [{"b": t["b"], "t": t["title"], "like": t["like"], "col": t["col"], "com": t["com"]} for t in top],
            "bloggers": blo}

    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__DATE__", today)
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(html)
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"全景图已生成：{out}")
