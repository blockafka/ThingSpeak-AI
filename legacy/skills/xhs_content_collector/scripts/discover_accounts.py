#!/usr/bin/env python3
"""
按关键词在小红书搜索家居定制设计账号，判定质量，输出高质量候选名单。

质量门槛（宽松，可调）：
  粉丝 >= MIN_FANS (默认 5000)
  且 主页近期图文笔记平均互动(点赞) >= MIN_RECENT_LIKE (默认 50)
  且 图文笔记占比 >= MIN_IMG_RATIO (默认 0.5)

只读评估，不下载笔记。输出：
  data/xhs/discovered_candidates.json / .csv
排除已在 hermes/tasks/xhs_designers_daily.json 池中的账号。
"""
from __future__ import annotations
import argparse, csv, json, re, time, urllib.parse
from pathlib import Path
from playwright.sync_api import sync_playwright

STATE = "data/xhs/auth/storage_state.json"
ROSTER = "hermes/tasks/xhs_designers_daily.json"
KEYWORDS = ["全屋定制", "室内设计", "家装设计", "别墅设计", "整装定制"]

# 主页：抓 关注/粉丝/获赞与收藏 三个数 + 笔记卡片(判断图文/视频 + 互动)
USER_EXTRACTOR = r"""
()=>{
 const num=(s)=>{ if(!s)return null; s=String(s).replace(/,/g,''); const m=s.match(/([\d.]+)/); if(!m)return null;
   let n=parseFloat(m[1]); if(/万/.test(s))n*=10000; if(/千/.test(s))n*=1000; return Math.round(n); };
 const body=document.body.innerText||'';
 const fans=num((body.match(/([\d.]+[万千]?)\s*粉丝/)||[])[1]);
 const follow=num((body.match(/([\d.]+[万千]?)\s*关注/)||[])[1]);
 const liked=num((body.match(/([\d.]+[万千]?)\s*(获赞与收藏|赞与收藏)/)||[])[1]);
 const nameEl=document.querySelector('.user-name,.user-nickname,[class*="nickname"],.name');
 const name=nameEl?nameEl.innerText.trim():((document.title||'').replace(/\s*-\s*小红书.*$/,''));
 // 笔记卡片：图文 vs 视频(带播放图标)，并抓卡片上的点赞数
 let imgtext=0, video=0; const likes=[];
 const cards=Array.from(document.querySelectorAll('section.note-item,.note-item,[class*="note-item"]')).slice(0,20);
 for(const c of cards){
   const isVideo=!!c.querySelector('.play-icon,[class*="play"],svg[class*="play"]');
   if(isVideo)video++; else imgtext++;
   const lk=c.querySelector('.count,[class*="like"] .count,.like-wrapper .count');
   if(lk){const v=num(lk.innerText); if(v!=null)likes.push(v);}
 }
 return {name, fans, follow, liked, card_count:cards.length, imgtext, video,
   avg_like: likes.length? Math.round(likes.reduce((a,b)=>a+b,0)/likes.length):null,
   sample_likes: likes.slice(0,10)};
}
"""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="*", default=KEYWORDS)
    ap.add_argument("--min-fans", type=int, default=5000)
    ap.add_argument("--min-recent-like", type=int, default=50)
    ap.add_argument("--min-img-ratio", type=float, default=0.5)
    ap.add_argument("--max-per-keyword", type=int, default=12, help="每个关键词最多评估的候选数")
    args=ap.parse_args()

    pool_ids=set()
    roster=json.load(open(ROSTER,encoding="utf-8"))
    for t in roster["targets"]:
        m=re.search(r"/user/profile/([^/?#]+)", t["url"])
        if m: pool_ids.add(m.group(1))

    results=[]; evaluated=set()
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True)
        ctx=b.new_context(storage_state=STATE, viewport={"width":1280,"height":900}, locale="zh-CN")
        pg=ctx.new_page()
        for kw in args.keywords:
            url="https://www.xiaohongshu.com/search_result?keyword="+urllib.parse.quote(kw)+"&type=54"
            pg.goto(url, wait_until="domcontentloaded", timeout=30000); pg.wait_for_timeout(4000)
            for _ in range(3): pg.mouse.wheel(0,1200); pg.wait_for_timeout(1000)
            hrefs=pg.eval_on_selector_all('a[href*="/user/profile/"]',
                "els=>els.map(a=>a.getAttribute('href'))")
            # 去重、保序
            seen=set(); cand=[]
            for h in hrefs:
                mm=re.search(r"/user/profile/([^/?#]+)", h)
                if not mm: continue
                uid=mm.group(1)
                if uid in seen or uid in pool_ids or uid in evaluated: continue
                seen.add(uid); cand.append((uid,h))
                if len(cand)>=args.max_per_keyword: break
            print(f"[{kw}] 评估 {len(cand)} 个候选...", flush=True)
            for uid,h in cand:
                evaluated.add(uid)
                full=h if h.startswith("http") else "https://www.xiaohongshu.com"+h
                try:
                    pg.goto(full, wait_until="domcontentloaded", timeout=30000); pg.wait_for_timeout(3000)
                    pg.mouse.wheel(0,800); pg.wait_for_timeout(1200)
                    info=pg.evaluate(USER_EXTRACTOR)
                except Exception as e:
                    print(f"   跳过 {uid}: {e}", flush=True); continue
                fans=info.get("fans") or 0
                ratio=(info["imgtext"]/info["card_count"]) if info.get("card_count") else 0
                avg=info.get("avg_like") or 0
                qualify = fans>=args.min_fans and avg>=args.min_recent_like and ratio>=args.min_img_ratio
                row={"keyword":kw,"name":info.get("name"),"user_id":uid,"url":full,
                     "fans":fans,"liked":info.get("liked"),"img_ratio":round(ratio,2),
                     "avg_recent_like":avg,"qualify":qualify}
                results.append(row)
                print(f"   {'✅' if qualify else '⛔'} {info.get('name')} 粉{fans} 图文比{ratio:.0%} 近期均赞{avg}", flush=True)
                time.sleep(1)
        ctx.close(); b.close()

    Path("data/xhs").mkdir(parents=True, exist_ok=True)
    json.dump(results, open("data/xhs/discovered_candidates.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
    with open("data/xhs/discovered_candidates.csv","w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f, fieldnames=["keyword","name","user_id","url","fans","liked","img_ratio","avg_recent_like","qualify"])
        w.writeheader(); w.writerows(results)
    good=[r for r in results if r["qualify"]]
    print(f"\n评估 {len(results)} 个账号，高质量 {len(good)} 个")
    for r in good: print(f"  ✅ {r['name']} 粉{r['fans']} 均赞{r['avg_recent_like']} -> {r['url']}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
