"""Agent · 内容创作器（Creator · 纯文本版本）

职责：
- 输入：DnaStrategyBrief（含六个细粒度 DNA 片段 + 卖点 + 图片摘要）
- 纯文本 LLM 生成：小红书笔记（标题+正文+标签）+ 配图建议
- LLM 失败时退回规则兜底
"""

from __future__ import annotations

import logging
from typing import Any

from ...dnas import get_fragment
from ...schemas import (
    DnaStrategyBrief,
    GenerateResult,
    IMAGE_SUGGESTION_LABELS,
    ImageSuggestion,
    MAX_IMAGE_SUGGESTIONS,
    XiaohongshuPost,
)
from ....tools.llm import chat, extract_json_from_llm_response, normalize_list_field
from ._prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


# ============================================================
# 对外主入口
# ============================================================

async def create_content(brief: DnaStrategyBrief) -> GenerateResult:
    """根据策略简报生成完整小红书笔记 + 视觉建议。"""
    try:
        return await _llm_create(brief)
    except Exception as e:
        logger.warning("Creator LLM生成失败，退回规则兜底: %s", e)
        return _rule_based_create(brief)


# ============================================================
# LLM生成路径（纯文本）
# ============================================================

async def _llm_create(brief: DnaStrategyBrief) -> GenerateResult:
    """调用纯文本LLM生成内容。"""
    fragment_defs = []
    for selection in brief.selected_fragments:
        try:
            fragment_defs.append(get_fragment(selection.fragment_id))
        except KeyError:
            logger.warning("DNA片段不存在，跳过: %s", selection.fragment_id)

    if not fragment_defs:
        raise ValueError("没有可用的DNA片段")

    user_prompt = build_user_prompt(brief.model_dump(), fragment_defs)

    response = await chat(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        temperature=0.8,
        max_tokens=4096,
    )

    result = _parse_llm_response(response)

    post = XiaohongshuPost(
        title=result["title"],
        content=result["content"],
        hashtags=result["hashtags"],
    )

    image_suggestions = []
    for vs in result["image_suggestions"][:MAX_IMAGE_SUGGESTIONS]:
        idx = vs.get("index", len(image_suggestions) + 1)
        idx = max(1, min(MAX_IMAGE_SUGGESTIONS, int(idx)))
        content = vs.get("content") or vs.get("description") or vs.get("content_type") or ""
        if not content.strip():
            continue
        image_suggestions.append(
            ImageSuggestion(index=idx, content=content.strip())
        )

    # 至少保证3张（避免LLM返回太少），不再强制补满
    while len(image_suggestions) < 3:
        idx = len(image_suggestions) + 1
        image_suggestions.append(
            ImageSuggestion(
                index=idx,
                content=f"{brief.product_name}展示图",
            )
        )

    return GenerateResult(
        post=post,
        image_suggestions=image_suggestions,
        selected_fragments=brief.selected_fragments,
        key_selling_points=brief.key_selling_points,
    )


def _parse_llm_response(response: str) -> dict[str, Any]:
    """解析LLM的JSON响应。"""
    data = extract_json_from_llm_response(response)

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not title or not content:
        raise ValueError("LLM响应缺少title或content")

    hashtags = normalize_list_field(
        data.get("hashtags"),
        max_len=8,
        transform=lambda s: s.lstrip("#"),
    )

    images = data.get("image_suggestions", [])
    if not isinstance(images, list):
        images = []

    return {
        "title": title,
        "content": content,
        "hashtags": hashtags,
        "image_suggestions": images,
    }


# ============================================================
# 规则兜底
# ============================================================

def _rule_based_create(brief: DnaStrategyBrief) -> GenerateResult:
    """纯规则兜底：模板拼接生成笔记 + 默认视觉建议。"""
    product_name = brief.product_name
    origin = brief.origin_place
    audience = brief.target_audience
    category = brief.product_category
    selling_points = brief.key_selling_points or [f"{origin}地道{category}"]

    # 标题
    title = f"🔥 {origin}宝藏{category}！{product_name}也太绝了"

    # 正文
    body_lines = [
        f"姐妹们！！今天必须给你们安利这款{origin}特产👉{product_name}",
        "",
    ]
    for i, point in enumerate(selling_points[:4]):
        emoji = ["✨", "💯", "🌿", "❤️"][i % 4]
        body_lines.append(f"{emoji} {point}")
    body_lines += [
        "",
        f"真的，吃过的都说好👍",
        f"给{audience}带这个绝对不会错！",
        "",
        "📌 小tips：",
        f"   去{origin}旅游的姐妹一定要试试！",
        "   不踩雷不踩雷不踩雷！重要的事说三遍！",
        "",
        "喜欢的姐妹点赞收藏不迷路~",
    ]
    content = "\n".join(body_lines)

    # 标签
    hashtags = [
        f"{origin}特产",
        product_name,
        f"{category}推荐",
        "地方特产",
        "小红书美食",
        "伴手礼推荐",
        "宝藏零食",
    ]

    post = XiaohongshuPost(title=title, content=content, hashtags=hashtags)

    # 笔记配图建议：复用brief里的suggested_visual_directions（规则兜底默认4张）
    image_suggestions = []
    image_summaries = brief.image_summaries or []
    visual_dirs = brief.suggested_visual_directions or []

    default_suggestions = [
        f"{product_name}产品特写",
        f"{product_name}包装展示",
        f"{origin}产地/原料场景",
        f"{product_name}食用/使用场景",
    ]
    count = max(3, min(6, len(visual_dirs) if visual_dirs else 4))

    for i in range(count):
        if i < len(image_summaries):
            content = f"用户上传图片：{image_summaries[i]}"
        elif i < len(visual_dirs):
            content = visual_dirs[i]
        else:
            content = default_suggestions[i] if i < len(default_suggestions) else f"{product_name}展示图"

        image_suggestions.append(
            ImageSuggestion(index=i + 1, content=content)
        )

    return GenerateResult(
        post=post,
        image_suggestions=image_suggestions,
        selected_fragments=brief.selected_fragments,
        key_selling_points=brief.key_selling_points,
    )
