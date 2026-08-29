#!/usr/bin/env python
"""Archive Xiaohongshu image-text notes for Hermes scheduled jobs.

The runner uses a saved Playwright storage_state produced by a manual official
login flow. It does not collect passwords, solve captchas, or bypass security
checks.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover
    sync_playwright = None  # type: ignore
    PlaywrightTimeoutError = Exception  # type: ignore


INVALID_PATH = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
NOTE_ID_RE = re.compile(r"[a-f0-9]{24}", re.I)


def jitter_sleep(base: float, spread: float = 0.6) -> None:
    """带随机抖动的休眠：base*(1±spread)，模拟真人节奏、降低风控风险。"""
    base = max(0.0, float(base))
    if base <= 0:
        return
    low = base * (1 - spread)
    high = base * (1 + spread)
    time.sleep(random.uniform(max(0.5, low), high))


def rebuild_note_copy() -> None:
    """调用项目 scripts/generate_note_copy.py 全库重生成「采集笔记文案」+总排名。
    用 subprocess 隔离失败；找不到脚本则静默跳过。"""
    import subprocess
    candidates = [
        Path.cwd() / "scripts" / "generate_note_copy.py",
        Path("scripts/generate_note_copy.py"),
    ]
    script = next((p for p in candidates if p.exists()), None)
    if script is None:
        return
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    res = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, cwd=str(Path.cwd()),
    )
    if res.returncode == 0:
        print(f"[note_copy] 采集笔记文案+排名已刷新")
    else:
        print(f"[note_copy] 生成失败: {res.stderr.strip()[:200]}", file=sys.stderr)


def rebuild_dashboard() -> None:
    """调用项目 scripts/build_dashboard.py 重生成全景图。
    通过当前工作目录定位脚本，找不到则静默跳过。"""
    candidates = [
        Path.cwd() / "scripts" / "build_dashboard.py",
        Path("scripts/build_dashboard.py"),
    ]
    script = next((p for p in candidates if p.exists()), None)
    if script is None:
        return
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_dashboard", str(script))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_dashboard"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    out = mod.build()
    print(f"[dashboard] 全景图已刷新: {out}")


def now_date() -> str:
    if ZoneInfo:
        try:
            return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
        except Exception:
            pass
    return datetime.now().date().isoformat()


def safe_part(value: str, fallback: str = "未命名笔记") -> str:
    value = INVALID_PATH.sub("_", str(value or fallback))
    value = re.sub(r"\s+", " ", value).strip()
    return (value or fallback)[:86]


def parse_count(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).replace(",", "").strip()
    match = re.search(r"([\d.]+)", text)
    if not match:
        return None
    number = float(match.group(1))
    if "万" in text:
        number *= 10000
    if "千" in text:
        number *= 1000
    return int(round(number))


# 家居定制设计行业关键词（标题命中其一即视为相关）
DEFAULT_INDUSTRY_KEYWORDS = [
    "家居", "家装", "装修", "定制", "全屋定制", "室内设计", "空间设计", "别墅",
    "大平层", "复式", "客厅", "卧室", "餐厨", "厨房", "卫生间", "衣柜", "橱柜",
    "收纳", "样板间", "硬装", "软装", "户型", "改造", "原木", "岩板", "豪宅",
    "私宅", "玄关", "餐边柜", "阳台", "书房", "儿童房", "主卧", "次卧", "平层",
    "极简", "侘寂", "中古", "奶油风", "现代风", "新中式", "美式", "法式", "意式",
    "托斯卡纳", "托斯卡纳风", "地中海", "侘寂风", "原木风", "庭院", "石灰华", "岛台",
    "㎡", "空间", "设计", "原创", "落地", "实景", "案例",
]
# 明显与家居设计无关的黑名单（标题命中即过滤，如团建、招聘、探店、抽奖等）
DEFAULT_TITLE_BLOCKLIST = [
    "团建", "招聘", "入职", "年会", "聚餐", "生日", "旅行", "旅游", "出游",
    "探店", "抽奖", "中奖", "打卡", "vlog", "plog", "日常", "随手记",
    "充电", "放假", "通知", "招募", "实习", "山野",
]


def title_relevance(title: str, keywords: list[str], blocklist: list[str]) -> tuple[bool, str]:
    """基于标题做行业相关性初筛。返回 (是否相关, 原因)。黑名单优先于关键词。"""
    t = str(title or "")
    low = t.lower()
    for bad in blocklist:
        if bad.lower() in low:
            return False, f"标题命中黑名单词:{bad}"
    for kw in keywords:
        if kw.lower() in low:
            return True, f"标题命中行业词:{kw}"
    return False, "标题未命中任何行业关键词"


def parse_publish_date(raw: Any, run_date: str) -> str | None:
    """把 '06-06 湖北' / '2025-06-06' / '3天前' 尽量规整为 YYYY-MM-DD。"""
    if not raw:
        return None
    text = str(raw).strip()
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(?<!\d)(\d{1,2})-(\d{1,2})(?!\d)", text)
    if m:
        year = (run_date or "")[:4] or str(datetime.utcnow().year)
        return f"{year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    if "今天" in text:
        return run_date
    m = re.search(r"(\d+)\s*天前", text)
    if m:
        try:
            from datetime import timedelta
            base = datetime.strptime(run_date, "%Y-%m-%d").date()
            return (base - timedelta(days=int(m.group(1)))).isoformat()
        except Exception:
            pass
    if "昨天" in text:
        try:
            from datetime import timedelta
            base = datetime.strptime(run_date, "%Y-%m-%d").date()
            return (base - timedelta(days=1)).isoformat()
        except Exception:
            pass
    return None


def parse_publish_location(raw: Any) -> str | None:
    if not raw:
        return None
    text = re.sub(r"\d{4}-\d{1,2}-\d{1,2}", " ", str(raw))
    text = re.sub(r"(?<!\d)\d{1,2}-\d{1,2}(?!\d)", " ", text)
    text = re.sub(r"今天|昨天|前天|\d+\s*(天|小时|分钟)前|编辑于|发布于", " ", text)
    loc = text.strip()
    return loc or None


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def existing_note_ids(output_root: Path) -> set[str]:
    ids: set[str] = set()
    if not output_root.exists():
        return ids
    for metadata in output_root.rglob("metadata.json"):
        try:
            note_id = load_json(metadata).get("note_id")
            if note_id:
                ids.add(str(note_id))
        except Exception:
            continue
    return ids


def unique_dir(path: Path) -> Path:
    candidate = path
    index = 2
    while candidate.exists():
        candidate = Path(f"{path}_{index}")
        index += 1
    return candidate


def download_image(url: str, file_base: Path, referer: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Referer": referer or "https://www.xiaohongshu.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        content_type = response.headers.get("content-type", "").lower()
        data = response.read()
    if "jpeg" in content_type or "jpg" in content_type:
        ext = "jpg"
    elif "png" in content_type:
        ext = "png"
    elif "gif" in content_type:
        ext = "gif"
    else:
        ext = "webp"
    file_path = file_base.with_suffix(f".{ext}")
    file_path.write_bytes(data)
    return {"file": str(file_path), "bytes": len(data), "contentType": content_type}


PROFILE_EXTRACTOR = r"""
(target) => {
  function text(v) { return v == null ? '' : String(v).trim(); }
  function cleanText(v) { return text(v).replace(/\s+/g, ' '); }
  function validId(id) { return /^[a-f0-9]{24}$/i.test(String(id || '')); }
  function abs(href) { try { return new URL(href, location.origin).href; } catch (e) { return href || ''; } }
  function noteIdFromHref(href) {
    try {
      const u = new URL(href, location.origin);
      const parts = u.pathname.split('/').filter(Boolean);
      if (parts[0] === 'explore' && validId(parts[1])) return parts[1];
      if (parts[0] === 'discovery' && parts[1] === 'item' && validId(parts[2])) return parts[2];
      if (parts[0] === 'user' && parts[1] === 'profile' && parts.length >= 4 && validId(parts[3])) return parts[3];
    } catch (e) {}
    return '';
  }
  const notes = [];
  const seen = new Set();
  function add(note) {
    if (!note || seen.has(note.note_id)) return;
    seen.add(note.note_id);
    notes.push(note);
  }
  for (const a of Array.from(document.querySelectorAll('a[href]')).slice(0, 500)) {
    const hrefRaw = a.getAttribute('href') || '';
    const noteId = noteIdFromHref(hrefRaw);
    if (!noteId) continue;
    const card = a.closest('.note-item') || a.parentElement;
    const rect = card && card.getBoundingClientRect ? card.getBoundingClientRect() : null;
    const cardText = cleanText((card && card.innerText) || a.innerText || a.getAttribute('aria-label') || a.title);
    const title = (cardText.split(target.name || '')[0] || cardText).replace(/^置顶\s*/, '').trim();
    add({
      note_id: noteId,
      title,
      type: '',
      href: abs(hrefRaw),
      card_index: card && card.getAttribute ? card.getAttribute('data-index') : null,
      card_text: cardText,
      click: rect ? {
        x: Math.round(rect.left + rect.width / 2),
        y: Math.round(rect.top + Math.min(rect.height / 2, 180)),
        top: Math.round(rect.top),
        bottom: Math.round(rect.bottom)
      } : null
    });
  }
  return {
    url: location.href,
    title: document.title,
    body_hint: String(document.body && document.body.innerText || '').slice(0, 1500),
    notes
  };
}
"""


DETAIL_EXTRACTOR = r"""
(expected) => {
  function text(v) { return v == null ? '' : String(v).trim(); }
  function clean(v) { return text(v).replace(/\r/g, '').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n'); }
  function noteIdFrom(s) { const m = String(s || '').match(/[a-f0-9]{24}/i); return m ? m[0] : ''; }
  const root = document.querySelector('.note-detail-mask .note-container') ||
    document.querySelector('.note-detail-mask') ||
    document.querySelector('.note-container') ||
    document.querySelector('.note-scroller') ||
    document.body;
  const content = root.querySelector('.note-content') || root.querySelector('.note-scroller') || root;
  const titleEl = content.querySelector('.title, [class*="title"]');
  const descEl = content.querySelector('.note-text') || content.querySelector('.desc, [class*="desc"]');
  const fullText = String(root && root.innerText || document.body && document.body.innerText || '');
  const pageTitle = text(document.title.replace(/\s*-\s*小红书\s*$/, ''));
  let title = clean((titleEl && titleEl.innerText) || expected.title || pageTitle);
  let desc = clean((descEl && descEl.innerText) || '');
  if (!desc) {
    const contentText = clean(content.innerText || '');
    desc = title && contentText.startsWith(title) ? contentText.slice(title.length).trim() : contentText;
  }
  const lines = clean(fullText).split('\n').map((x) => x.trim()).filter(Boolean);
  // 作者：优先用稳定选择器，避免拿到轮播计数器(如 "1/18")
  const authorEl = document.querySelector('.author-wrapper .username, .author-container .username, .account-name, .username');
  let author = clean(authorEl && authorEl.innerText || '');
  if (!author || /^\d+\/\d+$/.test(author)) {
    author = (lines[0] && lines[0] !== title && !/^\d+\/\d+$/.test(lines[0])) ? lines[0] : (expected.blogger || '');
  }
  const images = [];
  const seen = new Set();
  for (const img of Array.from(root.querySelectorAll('.note-slider img, .swiper img, img'))) {
    const src = img.currentSrc || img.src || '';
    if (!/sns-webpic/i.test(src)) continue;
    const width = img.naturalWidth || img.width || null;
    const height = img.naturalHeight || img.height || null;
    if ((width && width < 250) || (height && height < 250)) continue;
    if (seen.has(src)) continue;
    seen.add(src);
    images.push({ url: src, width, height, trace_id: null });
  }
  // 视频判定：只认笔记媒体容器内的真实 <video>/xg-video-container。
  // 注意小红书给图片轮播也加了 "xhsplayer" 类，[class*="player"] 不可用于判定。
  const mediaRoot = root.querySelector('.media-container, .slider-container, .note-slider, .swiper') || root;
  const hasVideo = !!(mediaRoot.querySelector('video, xg-video-container'));
  // 互动数：赞 / 收藏 / 评论。
  // .like-wrapper .count 常只返回"赞"字，点赞数实际在 .interact-container 文本的首个数字。
  // .interact-container 文本可能夹带提示语(如"可以添加到收藏夹啦")，故只提取纯数字 token。
  function countOf(sel) {
    const el = document.querySelector(sel);
    if (!el) return null;
    const t = clean(el.innerText || '');
    return /^[\d.,]+[万千kK]?$/.test(t) ? t : null;
  }
  let likeCount = null, collectCount = null, chatCount = null;
  const ic = document.querySelector('.interact-container');
  if (ic) {
    const nums = (clean(ic.innerText || '').match(/[\d.]+[万千kK]?/g) || []);
    if (nums.length >= 1) likeCount = nums[0];
    if (nums.length >= 2) collectCount = nums[1];
    if (nums.length >= 3) chatCount = nums[2];
  }
  // 收藏/评论优先用更精确的独立选择器覆盖
  collectCount = countOf('.collect-wrapper .count') || collectCount;
  chatCount = countOf('.chat-wrapper .count') || chatCount;
  const commentMatch = clean(fullText).match(/共\s*([\d.万千kK]+)\s*条评论/);
  // 发布时间 / 属地，例如 "06-06 湖北"
  const dateEl = document.querySelector('.note-content .date, .bottom-container .date, .date');
  const publishRaw = clean(dateEl && dateEl.innerText || '');
  // 评论列表（顶层评论）
  const comments = [];
  for (const item of Array.from(document.querySelectorAll('.comment-item, .parent-comment')).slice(0, 40)) {
    const nameEl = item.querySelector('.author .name, .name, .author .username, .username');
    const contentEl = item.querySelector('.content .note-text, .note-text, .content');
    const dateEl2 = item.querySelector('.date');
    const likeEl = item.querySelector('.like .count, .like-wrapper .count, .like .like-count');
    const ctext = clean(contentEl && contentEl.innerText || '');
    if (!ctext) continue;
    let uname = clean(nameEl && nameEl.innerText || '').split('\n')[0].trim();
    comments.push({
      user: uname,
      content: ctext,
      time: clean(dateEl2 && dateEl2.innerText || ''),
      like: clean(likeEl && likeEl.innerText || '')
    });
  }
  return {
    url: location.href,
    page_title: document.title,
    is_404: /\/404/.test(location.pathname) || /页面不见了|无法浏览|404/.test(document.title + '\n' + fullText),
    full_text: fullText,
    note: {
      note_id: expected.note_id || noteIdFrom(location.href),
      title,
      desc,
      type: hasVideo && !images.length ? 'video' : '',
      has_video: hasVideo,
      author,
      like_count: likeCount,
      collect_count: collectCount,
      comment_count: chatCount || (commentMatch ? commentMatch[1] : null),
      publish_raw: publishRaw,
      comments,
      images
    }
  };
}
"""


@dataclass
class RunnerConfig:
    task: dict[str, Any]
    output: Path
    storage_state: Path | None
    headless: bool
    date: str


def extract_profile(page: Any, target: dict[str, Any]) -> dict[str, Any]:
    return page.evaluate(PROFILE_EXTRACTOR, target)


def extract_detail(page: Any, expected: dict[str, Any]) -> dict[str, Any]:
    return page.evaluate(DETAIL_EXTRACTOR, expected)


def open_candidate(page: Any, candidate: dict[str, Any]) -> None:
    card_index = candidate.get("card_index")
    if card_index not in (None, ""):
        selector = f'.note-item[data-index="{str(card_index).replace(chr(34), "")}"]'
        locator = page.locator(selector)
        if locator.count() == 1:
            locator.click()
            return
    href = candidate.get("href")
    if href:
        page.goto(href, wait_until="domcontentloaded", timeout=30000)
        return
    click = candidate.get("click") or {}
    if click:
        page.mouse.click(int(click["x"]), int(click["y"]))
        return
    raise RuntimeError(f"cannot open candidate {candidate.get('note_id')}")


def archive_note(
    output_root: Path,
    target: dict[str, Any],
    candidate: dict[str, Any],
    detail: dict[str, Any],
    task_name: str,
    run_date: str,
    download_images: bool,
    task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task = task or {}
    if detail.get("is_404"):
        raise RuntimeError("detail_unavailable")
    note = detail.get("note") or {}
    # 过滤1：视频笔记 / 图文中夹带视频
    if "video" in str(note.get("type") or candidate.get("type") or "").lower():
        raise RuntimeError("video_note")
    if task.get("filter_embedded_video", True) and note.get("has_video"):
        raise RuntimeError("embedded_video")
    images = []
    seen = set()
    for image in note.get("images") or []:
        url = image.get("url")
        if url and url not in seen:
            seen.add(url)
            images.append(image)
    if not images:
        raise RuntimeError("no_detail_images")
    # 过滤2：图片数量下限
    min_images = int(task.get("min_images", 3))
    if len(images) < min_images:
        raise RuntimeError(f"too_few_images:{len(images)}<{min_images}")

    title = note.get("title") or candidate.get("title") or note.get("note_id") or "未命名笔记"
    # 过滤3：行业相关性初筛（标题黑名单优先；标题未命中时回退看正文，避免误杀情绪化标题）
    keywords = task.get("industry_keywords") or DEFAULT_INDUSTRY_KEYWORDS
    blocklist = task.get("title_blocklist") or DEFAULT_TITLE_BLOCKLIST
    relevant, reason = title_relevance(title, keywords, blocklist)
    if not relevant and "黑名单" not in reason:
        body_relevant, body_reason = title_relevance(note.get("desc") or "", keywords, blocklist)
        if body_relevant:
            relevant, reason = True, "正文命中行业词:" + body_reason.split(":")[-1]
    if task.get("filter_irrelevant", True) and not relevant:
        raise RuntimeError(f"irrelevant:{reason}")

    blogger = target.get("name") or note.get("author") or "未知博主"
    note_id = note.get("note_id") or candidate.get("note_id")
    note_url = detail.get("url")

    note_dir = unique_dir(output_root / safe_part(blogger) / f"{run_date}_{safe_part(title)}")
    image_dir = note_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if download_images:
        for index, image in enumerate(images, 1):
            try:
                saved = download_image(image["url"], image_dir / f"{index:02d}", note_url)
                downloaded.append(
                    {
                        "index": index,
                        "url": image["url"],
                        "file": saved["file"],
                        "bytes": saved["bytes"],
                        "contentType": saved["contentType"],
                        "width": image.get("width"),
                        "height": image.get("height"),
                    }
                )
            except Exception as exc:
                errors.append({"index": index, "url": image.get("url"), "error": str(exc)})

    metadata = {
        "target_blogger": blogger,
        "target_profile_url": target.get("url"),
        "title": title,
        "author": note.get("author") or blogger,
        "note_id": note_id,
        "note_url": note_url,
        "type": note.get("type") or "normal",
        "has_video": bool(note.get("has_video")),
        "like_count": parse_count(note.get("like_count")),
        "collect_count": parse_count(note.get("collect_count")),
        "comment_count": parse_count(note.get("comment_count")),
        "publish_raw": note.get("publish_raw") or "",
        "publish_date": parse_publish_date(note.get("publish_raw"), run_date),
        "publish_location": parse_publish_location(note.get("publish_raw")),
        "body_char_count": len(note.get("desc") or ""),
        "image_count": len(images),
        "downloaded_image_count": len(downloaded),
        "download_errors": errors,
        "comments": note.get("comments") or [],
        "images": downloaded,
        "all_image_urls": [image["url"] for image in images],
        "batch": task_name,
        "collected_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

    body = "\r\n".join(
        [
            f"标题：{title}",
            f"博主：{blogger}",
            f"原作者：{metadata['author']}",
            f"笔记链接：{note_url}",
            f"点赞：{metadata['like_count'] if metadata['like_count'] is not None else ''}"
            f"  收藏：{metadata['collect_count'] if metadata['collect_count'] is not None else ''}"
            f"  评论：{metadata['comment_count'] if metadata['comment_count'] is not None else ''}",
            f"发布：{metadata['publish_raw']}",
            "",
            "正文：",
            note.get("desc") or "",
        ]
    )
    (note_dir / "body.txt").write_text(body, encoding="utf-8")
    write_json(note_dir / "metadata.json", metadata)
    # 评论原文（除噪声前的原始抓取，供后续生成"采集笔记文案"使用）
    comments = note.get("comments") or []
    if comments:
        clines = []
        for c in comments:
            head = " ".join(x for x in [c.get("user", ""), c.get("time", ""), (f"赞{c.get('like')}" if c.get("like") else "")] if x)
            clines.append(head)
            clines.append(c.get("content", ""))
            clines.append("")
        (note_dir / "comments.txt").write_text("\r\n".join(clines), encoding="utf-8")
    (note_dir / "image_urls.txt").write_text(
        "\r\n".join(f"{idx:02d}\t{image['url']}" for idx, image in enumerate(images, 1)),
        encoding="utf-8",
    )
    (note_dir / "full_text_snapshot.txt").write_text(detail.get("full_text") or "", encoding="utf-8")
    (note_dir / "采集状态.txt").write_text(
        "\r\n".join(
            [
                "状态：完成",
                f"批次：{task_name}",
                f"博主：{blogger}",
                f"标题：{title}",
                f"图片数：{len(images)}",
                f"成功下载：{len(downloaded)}",
                f"下载失败：{len(errors)}",
                f"本地目录：{note_dir}",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "status": "success",
        "blogger": blogger,
        "title": title,
        "note_id": note_id,
        "image_count": len(images),
        "downloaded_image_count": len(downloaded),
        "body_chars": metadata["body_char_count"],
        "path": str(note_dir),
        "url": note_url,
        "errors": errors,
    }


def collect_direct_note(page: Any, cfg: RunnerConfig, item: dict[str, Any], seen_ids: set[str]) -> dict[str, Any]:
    page.goto(item["url"], wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(int(cfg.task.get("candidate_sleep_seconds", 3) * 1000))
    note_match = NOTE_ID_RE.search(item["url"])
    note_id = note_match.group(0) if note_match else None
    if note_id and cfg.task.get("skip_existing", True) and note_id in seen_ids:
        return {"status": "skipped_existing", "blogger": item.get("name"), "note_id": note_id, "url": item["url"]}
    detail = extract_detail(page, {"note_id": note_id, "title": item.get("title", ""), "blogger": item.get("name", "")})
    result = archive_note(cfg.output, item, {"note_id": note_id, "title": item.get("title", "")}, detail, cfg.task_name, cfg.date, cfg.task.get("download_images", True), cfg.task)  # type: ignore[attr-defined]
    if result.get("note_id"):
        seen_ids.add(result["note_id"])
    return result


def collect_profile(page: Any, cfg: RunnerConfig, target: dict[str, Any], seen_ids: set[str]) -> list[dict[str, Any]]:
    page.goto(target["url"], wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)
    profile = extract_profile(page, target)
    if re.search(r"登录|验证码|安全验证", profile.get("body_hint", "")) and not profile.get("notes"):
        return [{"status": "login_required", "blogger": target.get("name"), "url": target.get("url")}]

    for _ in range(int(cfg.task.get("scroll_pages", 3))):
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(800)
    profile = extract_profile(page, target)

    max_notes = int(cfg.task.get("max_notes_per_blogger", 1))
    max_candidates = int(cfg.task.get("max_candidates_per_blogger", 12))
    candidates = [
        note
        for note in profile.get("notes", [])
        if not (cfg.task.get("skip_existing", True) and note.get("note_id") in seen_ids)
        and "video" not in str(note.get("type", "")).lower()
    ]
    if not candidates:
        return [{"status": "no_new_note", "blogger": target.get("name"), "url": target.get("url")}]

    results: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    for candidate in candidates[:max_candidates]:
        if len([item for item in results if item.get("status") == "success"]) >= max_notes:
            break
        page.goto(target["url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        try:
            open_candidate(page, candidate)
            page.wait_for_timeout(int(cfg.task.get("candidate_sleep_seconds", 3) * 1000))
            detail = extract_detail(page, {"note_id": candidate.get("note_id"), "title": candidate.get("title", ""), "blogger": target.get("name", "")})
            note_type = str((detail.get("note") or {}).get("type") or candidate.get("type") or "").lower()
            note_obj = detail.get("note") or {}
            image_count = len(note_obj.get("images") or [])
            if detail.get("is_404") or "video" in note_type or not image_count:
                attempts.append({"note_id": candidate.get("note_id"), "title": candidate.get("title"), "skipped": "video_or_no_images"})
                continue
            try:
                result = archive_note(cfg.output, target, candidate, detail, cfg.task_name, cfg.date, cfg.task.get("download_images", True), cfg.task)  # type: ignore[attr-defined]
            except RuntimeError as fexc:
                attempts.append({"note_id": candidate.get("note_id"), "title": candidate.get("title"), "skipped": str(fexc)})
                continue
            result["attempts"] = attempts + [{"note_id": candidate.get("note_id"), "title": candidate.get("title")}]
            results.append(result)
            if result.get("note_id"):
                seen_ids.add(result["note_id"])
        except Exception as exc:
            attempts.append({"note_id": candidate.get("note_id"), "title": candidate.get("title"), "error": str(exc)})

    if not results:
        return [{"status": "no_collectable_note", "blogger": target.get("name"), "url": target.get("url"), "attempts": attempts}]
    return results


def write_summary(output: Path, task_name: str, results: list[dict[str, Any]]) -> dict[str, str]:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f"{safe_part(task_name)}_summary.json"
    csv_path = output / f"{safe_part(task_name)}_summary.csv"
    md_path = output / f"{safe_part(task_name)}_summary.md"
    write_json(json_path, results)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["blogger", "status", "title", "image_count", "downloaded_image_count", "body_chars", "path", "url", "error"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(results)

    lines = [
        f"# {task_name} 采集汇总",
        "",
        "| 序号 | 博主 | 状态 | 标题 | 图片数 | 正文字数 | 本地目录 |",
        "|---:|---|---|---|---:|---:|---|",
    ]
    for index, item in enumerate(results, 1):
        row = [
            str(index),
            str(item.get("blogger", "")),
            str(item.get("status", "")),
            str(item.get("title") or item.get("error") or ""),
            str(item.get("downloaded_image_count", "")),
            str(item.get("body_chars", "")),
            str(item.get("path", "")),
        ]
        lines.append("| " + " | ".join(cell.replace("|", "\\|").replace("\n", " ") for cell in row) + " |")
    md_path.write_text("\ufeff" + "\r\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "csv": str(csv_path), "md": str(md_path)}


def run(cfg: RunnerConfig) -> dict[str, Any]:
    if sync_playwright is None:
        raise RuntimeError("playwright is required. Install with: python -m pip install playwright && python -m playwright install chromium")
    if not cfg.storage_state:
        raise RuntimeError("storage_state_missing: pass --storage-state or set XHS_STORAGE_STATE_PATH before collecting")
    if not cfg.storage_state.exists():
        raise RuntimeError(f"storage_state_missing: {cfg.storage_state}")

    cfg.task_name = str(cfg.task.get("task_name") or f"xhs_task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")  # type: ignore[attr-defined]
    seen_ids = existing_note_ids(cfg.output) if cfg.task.get("skip_existing", True) else set()
    results: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=cfg.headless)
        context_kwargs: dict[str, Any] = {"viewport": {"width": 1280, "height": 720}}
        context_kwargs["storage_state"] = str(cfg.storage_state)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        for item in cfg.task.get("note_urls", []):
            try:
                results.append(collect_direct_note(page, cfg, item, seen_ids))
            except Exception as exc:
                results.append({"status": "failed", "blogger": item.get("name"), "url": item.get("url"), "error": str(exc)})
        rest_every = int(cfg.task.get("rest_every_accounts", 5))
        rest_seconds = float(cfg.task.get("rest_seconds", 45))
        for idx, target in enumerate(cfg.task.get("targets", []), 1):
            try:
                results.extend(collect_profile(page, cfg, target, seen_ids))
            except Exception as exc:
                results.append({"status": "failed", "blogger": target.get("name"), "url": target.get("url"), "error": str(exc)})
            jitter_sleep(float(cfg.task.get("target_sleep_seconds", 2)))
            # 每采 rest_every 个账号，额外休息一段，模拟真人、降低风控风险
            if rest_every > 0 and idx % rest_every == 0 and idx < len(cfg.task.get("targets", [])):
                jitter_sleep(rest_seconds, spread=0.3)
        context.close()
        browser.close()

    summary_paths = write_summary(cfg.output, cfg.task_name, results)  # type: ignore[attr-defined]
    # 采集结束后：先全库重生成「采集笔记文案+排名」，再刷新全景图（均失败不影响采集结果）
    try:
        rebuild_note_copy()
    except Exception as exc:  # noqa: BLE001
        print(f"[note_copy] 跳过文案刷新: {exc}", file=sys.stderr)
    try:
        rebuild_dashboard()
    except Exception as exc:  # noqa: BLE001
        print(f"[dashboard] 跳过全景图刷新: {exc}", file=sys.stderr)
    return {
        "task_name": cfg.task_name,  # type: ignore[attr-defined]
        "success": len([item for item in results if item.get("status") == "success"]),
        "total": len(results),
        "summary": summary_paths,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Xiaohongshu full note archive for Hermes.")
    parser.add_argument("--task", required=True, help="Task JSON path.")
    parser.add_argument("--output", default=os.environ.get("XHS_OUTPUT_ROOT", "data/xhs_collected"))
    parser.add_argument("--storage-state", default=os.environ.get("XHS_STORAGE_STATE_PATH", ""))
    parser.add_argument("--headless", action="store_true", help="Run Chromium headless.")
    parser.add_argument("--show-browser", action="store_true", help="Run Chromium visibly.")
    args = parser.parse_args(argv)

    task = load_json(Path(args.task))
    storage_state = Path(args.storage_state) if args.storage_state else None
    cfg = RunnerConfig(
        task=task,
        output=Path(args.output),
        storage_state=storage_state,
        headless=not args.show_browser if not args.headless else True,
        date=now_date(),
    )
    try:
        result = run(cfg)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
