"""Agent · 传播策略分析器（地方食品特产 · 爆款DNA匹配 · 多模态版本）

职责：
- 接收文字 + 图片输入，多模态理解产品
- 两级DNA匹配：粗筛（关键词规则）→ 精筛（LLM选Top3+权重）
- 提炼核心卖点、避坑点、视觉方向
- 输出图片内容摘要（供下游creator使用，无需再看图）
- 输出 DnaStrategyBrief
- LLM失败时自动退回规则兜底
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ...dnas import (
    get_dna,
    list_dnas,
    match_dnas_by_keywords,
    pick_default_dnas,
)
from ...schemas import DnaMatch, DnaRole, DnaStrategyBrief, LocalFoodRequest
from ....tools.llm import (
    chat,
    chat_with_images,
    extract_json_from_llm_response,
    normalize_list_field,
)
from ._prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

_MAX_CANDIDATE_DNAS = 5
_MATCH_COUNT = 3


# ============================================================
# 对外主入口
# ============================================================

async def analyze_request(request: LocalFoodRequest) -> DnaStrategyBrief:
    """分析用户请求（文字+图片），输出策略简报。"""
    candidates = _coarse_filter(request)
    try:
        return await _llm_analyze(request, candidates)
    except Exception as e:
        logger.warning("LLM分析失败，退回规则兜底: %s", e)
        return _rule_based_analyze(request, candidates)


# ============================================================
# 粗筛：关键词规则匹配
# ============================================================

def _coarse_filter(request: LocalFoodRequest) -> list[dict[str, Any]]:
    """基于关键词从DNA库中挑出候选，返回候选DNA定义列表。"""
    text_parts = [
        request.product_name,
        request.product_category,
        request.target_audience,
    ]
    if request.selling_scene:
        text_parts.append(request.selling_scene)
    if request.user_note:
        text_parts.append(request.user_note)
    combined_text = " ".join(text_parts)

    matches = match_dnas_by_keywords(combined_text)
    matched_ids = [dna_id for dna_id, _ in matches]

    # 补全候选：命中的在前，没命中的按顺序补
    all_ids = [dna["id"] for dna in list_dnas()]
    candidate_ids = matched_ids + [dna_id for dna_id in all_ids if dna_id not in set(matched_ids)]

    return [get_dna(dna_id) for dna_id in candidate_ids[:_MAX_CANDIDATE_DNAS]]


# ============================================================
# 精筛：多模态LLM驱动
# ============================================================

async def _llm_analyze(
    request: LocalFoodRequest,
    candidates: list[dict[str, Any]],
) -> DnaStrategyBrief:
    """调用多模态LLM从候选DNA中选Top3并生成策略。"""
    product_info = {
        "product_name": request.product_name,
        "product_category": request.product_category,
        "origin_place": request.origin_place,
        "target_audience": request.target_audience,
        "selling_scene": request.selling_scene,
        "user_note": request.user_note,
    }

    image_paths = request.image_paths or []
    has_images = len(image_paths) > 0

    user_prompt = build_user_prompt(product_info, candidates, has_images)

    if has_images:
        image_urls = [_path_to_url(p) for p in image_paths[:3]]
        response = await chat_with_images(
            system=SYSTEM_PROMPT,
            user_text=user_prompt,
            image_urls=image_urls,
            temperature=0.7,
            max_tokens=2048,
        )
    else:
        response = await chat(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.7,
            max_tokens=2048,
        )

    result = _parse_llm_response(response, candidates)

    # 构造 DnaStrategyBrief
    dna_matches = []
    for match_data in result["dna_matches"]:
        dna_id = match_data["dna_id"]
        dna_def = get_dna(dna_id)
        dna_matches.append(
            DnaMatch(
                dna_id=dna_id,
                dna_name=dna_def["name"],
                role=match_data["role"],
                weight=match_data["weight"],
                reason=match_data.get("reason", ""),
            )
        )

    return DnaStrategyBrief(
        product_name=request.product_name,
        product_category=request.product_category,
        origin_place=request.origin_place,
        target_audience=request.target_audience,
        selling_scene=request.selling_scene,
        user_note=request.user_note,
        image_summaries=result["image_summaries"],
        dna_matches=dna_matches,
        key_selling_points=result["key_selling_points"],
        avoid_points=result["avoid_points"],
        suggested_visual_directions=result["suggested_visual_directions"],
    )


def _path_to_url(path: str) -> str:
    """本地路径转file:// URL。已经是http(s)/data:开头直接返回。"""
    if path.startswith(("http://", "https://", "data:")):
        return path
    return f"file://{os.path.abspath(path)}"


def _parse_llm_response(
    response: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """解析LLM的JSON响应，做格式校验。"""
    data = extract_json_from_llm_response(response)

    # image_summaries
    image_summaries = normalize_list_field(data.get("image_summaries"))

    # dna_matches 校验
    dna_matches = data.get("dna_matches", [])
    if not isinstance(dna_matches, list) or len(dna_matches) < _MATCH_COUNT:
        raise ValueError(f"dna_matches数量不足，期望至少{_MATCH_COUNT}个")

    valid_ids = {dna["id"] for dna in candidates}
    has_primary = False
    total_weight = 0.0
    seen_ids = set()

    for match in dna_matches[:_MATCH_COUNT]:
        dna_id = match.get("dna_id")
        if not dna_id or dna_id not in valid_ids:
            raise ValueError(f"无效的dna_id: {dna_id}")
        if dna_id in seen_ids:
            raise ValueError(f"重复的dna_id: {dna_id}")
        seen_ids.add(dna_id)

        role = match.get("role")
        if role not in ("primary", "supporting"):
            raise ValueError(f"无效的role: {role}")
        if role == "primary":
            has_primary = True

        weight = match.get("weight", 0)
        if not isinstance(weight, (int, float)) or weight <= 0:
            raise ValueError(f"无效的weight: {weight}")
        total_weight += weight

    if not has_primary:
        dna_matches[0]["role"] = "primary"

    # 权重归一化
    if abs(total_weight - 1.0) > 0.01:
        for match in dna_matches[:_MATCH_COUNT]:
            match["weight"] = round(match["weight"] / total_weight, 3)

    return {
        "image_summaries": image_summaries,
        "dna_matches": dna_matches[:_MATCH_COUNT],
        "key_selling_points": normalize_list_field(data.get("key_selling_points"), 5),
        "avoid_points": normalize_list_field(data.get("avoid_points"), 3),
        "suggested_visual_directions": normalize_list_field(data.get("suggested_visual_directions"), 9),
    }


# ============================================================
# 规则兜底
# ============================================================

def _rule_based_analyze(
    request: LocalFoodRequest,
    candidates: list[dict[str, Any]],
) -> DnaStrategyBrief:
    """纯规则兜底：基于关键词命中和默认组合生成策略简报。"""
    dna_matches: list[DnaMatch] = []
    weights = [0.5, 0.3, 0.2]

    candidate_ids = [dna["id"] for dna in candidates]
    for default_id, _ in pick_default_dnas():
        if default_id not in candidate_ids:
            candidate_ids.append(default_id)
        if len(candidate_ids) >= _MATCH_COUNT:
            break

    for i in range(min(_MATCH_COUNT, len(candidate_ids))):
        dna_id = candidate_ids[i]
        dna_def = get_dna(dna_id)
        role: DnaRole = "primary" if i == 0 else "supporting"
        dna_matches.append(
            DnaMatch(
                dna_id=dna_id,
                dna_name=dna_def["name"],
                role=role,
                weight=weights[i],
                reason=f"规则匹配：{'主风格' if i == 0 else '辅助风格'}",
            )
        )

    # 图片摘要
    image_summaries = []
    if request.image_paths:
        for i, _ in enumerate(request.image_paths[:3]):
            image_summaries.append(f"用户上传的第{i+1}张产品图片")

    # 核心卖点
    key_selling_points = _rule_key_points(request)

    # 避坑点
    avoid_points = [
        "避免夸大疗效或虚假宣传",
        "避免硬广式口播感",
        "避免泛泛而谈没有具体体感",
    ]

    # 视觉方向
    visual_directions = _rule_visual_directions(request)

    return DnaStrategyBrief(
        product_name=request.product_name,
        product_category=request.product_category,
        origin_place=request.origin_place,
        target_audience=request.target_audience,
        selling_scene=request.selling_scene,
        user_note=request.user_note,
        image_summaries=image_summaries,
        dna_matches=dna_matches,
        key_selling_points=key_selling_points,
        avoid_points=avoid_points,
        suggested_visual_directions=visual_directions,
    )


def _rule_key_points(request: LocalFoodRequest) -> list[str]:
    """规则生成核心卖点。"""
    points = [f"{request.origin_place}在地特产，地道风味"]
    points.append(f"{request.product_name}，{request.product_category}中的宝藏款")
    if request.selling_scene:
        points.append(f"适合{request.selling_scene}场景")
    if request.user_note:
        points.append(request.user_note[:30])
    return points[:5]


def _rule_visual_directions(request: LocalFoodRequest) -> list[str]:
    """规则生成视觉卡片方向（默认4条，简洁够用）。"""
    return [
        f"{request.product_name}产品主图（特写）",
        f"{request.product_name}包装展示",
        f"{request.origin_place}产地/原料场景",
        f"{request.product_name}食用/使用场景",
    ]
