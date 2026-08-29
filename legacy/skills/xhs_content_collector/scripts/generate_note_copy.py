#!/usr/bin/env python3
"""
生成「采集笔记文案」：对已采集的小红书图文笔记做内容整理。

功能：
1. 清洗正文（去版权声明/水印/广告导流/重复标点等噪声）。
2. 清洗评论（去作者自导流广告、去重、去空噪声），保留有价值评论。
3. 依据 收藏/点赞/评论 三项互动做质量评分，并兼顾发布时间做公平性补偿。
4. 每篇输出 采集笔记文案.md；并产出一个跨笔记的总排名文件。

只读取本地已采集数据，不联网。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
from datetime import date, datetime

# —— 正文噪声规则 ——
BODY_NOISE_PATTERNS = [
    r"©.*?原创",
    r"©?\s*严禁盗用.*",
    r"所有图文均为.*?原创",
    r"\d+\s*天?，?每日原创案例分享.*",
    r"明儿见.*",
    r"未经允许.*?转载",
    r"侵权必究.*",
]
# 评论噪声/广告导流规则（命中即丢弃该评论）
COMMENT_AD_PATTERNS = [
    r"报价", r"获取?\s*装.?修.?报.?价", r"私信", r"📩", r"加微", r"vx", r"威信",
    r"同款风格.*空间", r"做.*家装顾问", r"咨询", r"领取", r"扣1", r"扣\s*1",
]


def clean_body(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r", "")
    for pat in BODY_NOISE_PATTERNS:
        t = re.sub(pat, "", t)
    # 去掉孤立的装饰符号行
    lines = []
    for ln in t.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if re.fullmatch(r"[·\-〰️^_~\s]+", s):
            continue
        lines.append(s)
    # 折叠重复空行已在上面处理
    return "\n".join(lines).strip()


def extract_tags(text: str) -> list[str]:
    return re.findall(r"#([^#\s][^#]*?)(?=\s|#|$)", text or "")


def clean_comments(comments: list[dict], author_name: str) -> list[dict]:
    seen = set()
    out = []
    for c in comments or []:
        content = (c.get("content") or "").strip()
        if not content:
            continue
        # 去广告导流
        if any(re.search(p, content) for p in COMMENT_AD_PATTERNS):
            continue
        # 去重（按正文）
        key = re.sub(r"\s+", "", content)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def to_int(v) -> int:
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"[\d.]+", str(v))
    return int(float(m.group(0))) if m else 0


def days_since(pub: str | None, today: date) -> int:
    if not pub:
        return 30  # 未知发布时间，给中性值
    try:
        d = datetime.strptime(pub, "%Y-%m-%d").date()
        return max((today - d).days, 0)
    except Exception:
        return 30


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/xhs_collected")
    ap.add_argument("--bloggers", nargs="*", help="只处理这些博主目录，缺省处理全部含 metadata 的目录")
    ap.add_argument("--batch", help="只处理 metadata.batch 等于该值的笔记")
    ap.add_argument("--date-prefix", help="只处理二级目录名以该前缀开头的笔记，如 2026-06-28")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--out-rank", default="data/xhs_collected/采集笔记文案_排名.md")
    args = ap.parse_args()

    today = datetime.strptime(args.today, "%Y-%m-%d").date()
    notes = []
    for meta_path in glob.glob(os.path.join(args.root, "*", "*", "metadata.json")):
        try:
            m = json.load(open(meta_path, encoding="utf-8"))
        except Exception:
            continue
        if args.bloggers and m.get("target_blogger") not in args.bloggers:
            continue
        if args.batch and m.get("batch") != args.batch:
            continue
        d = os.path.dirname(meta_path)
        if args.date_prefix and not os.path.basename(d).startswith(args.date_prefix):
            continue
        body_raw = ""
        bp = os.path.join(d, "body.txt")
        if os.path.exists(bp):
            raw = open(bp, encoding="utf-8").read()
            mobj = re.search(r"正文：\s*(.*)$", raw, re.S)
            body_raw = mobj.group(1) if mobj else raw
        like = to_int(m.get("like_count"))
        collect = to_int(m.get("collect_count"))
        comment = to_int(m.get("comment_count"))
        notes.append({
            "dir": d,
            "blogger": m.get("target_blogger"),
            "title": m.get("title"),
            "url": m.get("note_url"),
            "like": like, "collect": collect, "comment": comment,
            "publish": m.get("publish_date"),
            "publish_raw": m.get("publish_raw"),
            "images": m.get("downloaded_image_count") or m.get("image_count") or 0,
            "body": clean_body(body_raw),
            "tags": extract_tags(body_raw),
            "comments": clean_comments(m.get("comments") or [], m.get("author") or ""),
        })

    if not notes:
        print("没有找到可处理的笔记。")
        return 1

    # —— 评分：互动对数归一 + 加权 + 时间公平性补偿 ——
    # 用 log1p 抑制头部极值；三项各自按本批最大值归一到 [0,1]
    def lg(x): return math.log1p(max(x, 0))
    max_like = max(lg(n["like"]) for n in notes) or 1
    max_col = max(lg(n["collect"]) for n in notes) or 1
    max_com = max(lg(n["comment"]) for n in notes) or 1
    W_COL, W_LIKE, W_COM = 0.5, 0.3, 0.2
    for n in notes:
        base = (W_COL * lg(n["collect"]) / max_col
                + W_LIKE * lg(n["like"]) / max_like
                + W_COM * lg(n["comment"]) / max_com)
        # 时间公平性：老笔记积累久，给与温和上浮补偿（按天数对数）
        dd = days_since(n["publish"], today)
        fairness = 1.0 + 0.06 * math.log1p(dd)  # 30天≈+0.20，180天≈+0.31
        n["days"] = dd
        n["score"] = round(base * fairness * 100, 2)

    notes.sort(key=lambda x: x["score"], reverse=True)
    for i, n in enumerate(notes, 1):
        n["rank"] = i

    # —— 每篇输出 采集笔记文案.md ——
    for n in notes:
        lines = [
            f"# 采集笔记文案 · {n['title']}",
            "",
            f"- 博主：{n['blogger']}",
            f"- 链接：{n['url']}",
            f"- 发布：{n['publish_raw'] or '未知'}（距今约 {n['days']} 天）",
            f"- 互动：点赞 {n['like']} · 收藏 {n['collect']} · 评论 {n['comment']}",
            f"- 图片：{n['images']} 张",
            f"- 质量评分：**{n['score']}**（本批排名 #{n['rank']}）",
            "",
            "## 清洗后正文",
            "",
            n["body"] or "(无正文)",
            "",
        ]
        if n["tags"]:
            lines += ["## 话题标签", "", " ".join("#" + t.strip() for t in n["tags"]), ""]
        if n["comments"]:
            lines += ["## 精选评论（已去广告/去重）", ""]
            for c in n["comments"][:10]:
                meta = " · ".join(x for x in [c.get("user", ""), c.get("time", "")] if x)
                lines.append(f"- {c.get('content','').strip()}" + (f"  〔{meta}〕" if meta else ""))
            lines.append("")
        open(os.path.join(n["dir"], "采集笔记文案.md"), "w", encoding="utf-8").write("\n".join(lines))

    # —— 总排名文件 ——
    rl = [
        "# 采集笔记文案 · 质量评分排名",
        "",
        f"生成日期：{args.today}　|　评分=对数归一(收藏0.5/点赞0.3/评论0.2)×时间公平补偿",
        "",
        "| 排名 | 评分 | 博主 | 标题 | 点赞 | 收藏 | 评论 | 发布 | 图 |",
        "|---:|---:|---|---|---:|---:|---:|---|---:|",
    ]
    for n in notes:
        rl.append("| {rank} | {score} | {blogger} | {title} | {like} | {collect} | {comment} | {pub} | {img} |".format(
            rank=n["rank"], score=n["score"], blogger=n["blogger"],
            title=(n["title"] or "").replace("|", "\\|"),
            like=n["like"], collect=n["collect"], comment=n["comment"],
            pub=n["publish_raw"] or "?", img=n["images"]))
    open(args.out_rank, "w", encoding="utf-8").write("\n".join(rl))
    print(f"已为 {len(notes)} 篇生成 采集笔记文案.md")
    print(f"排名文件：{args.out_rank}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
