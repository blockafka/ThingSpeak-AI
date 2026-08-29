"""Analyzer agent: choose one fine-grained DNA fragment per dimension."""

from __future__ import annotations

import logging
import os
from typing import Any

from ...dnas import FRAGMENT_TYPES, get_fragment, get_top_fragments_by_type
from ...schemas import DnaFragmentSelection, DnaStrategyBrief, LocalFoodRequest
from ....tools.llm import (
    chat,
    chat_with_images,
    extract_json_from_llm_response,
    normalize_list_field,
)
from ._prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

# 每个维度召回候选数：本地默认 Top 5；云端可设 ANALYZER_CANDIDATES=3 压延迟
_MAX_CANDIDATES_PER_TYPE = int(os.environ.get("ANALYZER_CANDIDATES", "5"))


async def analyze_request(request: LocalFoodRequest) -> DnaStrategyBrief:
    """Analyze a request and select one DNA fragment for each dimension."""
    candidate_pools = get_top_fragments_by_type(limit=_MAX_CANDIDATES_PER_TYPE)
    try:
        return await _llm_analyze(request, candidate_pools)
    except Exception as exc:
        logger.warning("LLM分析失败，退回规则兜底: %s", exc)
        return _rule_based_analyze(request, candidate_pools)


async def _llm_analyze(
    request: LocalFoodRequest,
    candidate_pools: dict[str, list[dict[str, Any]]],
) -> DnaStrategyBrief:
    """Use one multimodal/text LLM call to choose the six fragments."""
    product_info = {
        "product_name": request.product_name,
        "product_category": request.product_category,
        "origin_place": request.origin_place,
        "target_audience": request.target_audience,
        "selling_scene": request.selling_scene,
        "user_note": request.user_note,
    }
    image_paths = request.image_paths or []
    user_prompt = build_user_prompt(
        product_info,
        candidate_pools,
        has_images=bool(image_paths),
    )

    if image_paths:
        response = await chat_with_images(
            system=SYSTEM_PROMPT,
            user_text=user_prompt,
            image_urls=[_path_to_url(path) for path in image_paths[:3]],
            temperature=0.7,
            max_tokens=3096,
        )
    else:
        response = await chat(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.7,
            max_tokens=3096,
        )

    result = _parse_llm_response(response, candidate_pools)
    selections = [DnaFragmentSelection(**item) for item in result["selected_fragments"]]
    return DnaStrategyBrief(
        product_name=request.product_name,
        product_category=request.product_category,
        origin_place=request.origin_place,
        target_audience=request.target_audience,
        selling_scene=request.selling_scene,
        user_note=request.user_note,
        image_summaries=result["image_summaries"],
        selected_fragments=selections,
        key_selling_points=result["key_selling_points"],
        avoid_points=result["avoid_points"],
        suggested_visual_directions=result["suggested_visual_directions"],
    )


def _path_to_url(path: str) -> str:
    """Turn a local image path into a file URL; preserve remote/data URLs."""
    if path.startswith(("http://", "https://", "data:")):
        return path
    return f"file://{os.path.abspath(path)}"


def _parse_llm_response(
    response: str,
    candidate_pools: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Validate the structured selection returned by the LLM."""
    data = extract_json_from_llm_response(response)
    raw_selections = data.get("selectedFragments", data.get("selected_fragments", []))
    if not isinstance(raw_selections, list) or len(raw_selections) != len(FRAGMENT_TYPES):
        raise ValueError("每个维度恰好选择一个DNA片段")

    by_id = {
        fragment["fragmentId"]: fragment
        for fragments in candidate_pools.values()
        for fragment in fragments
    }
    selected: list[dict[str, Any]] = []
    seen_types: set[str] = set()
    for raw in raw_selections:
        if not isinstance(raw, dict):
            raise ValueError("DNA片段选择格式无效")
        fragment_type = raw.get("type") or raw.get("fragment_type")
        fragment_id = raw.get("fragmentId") or raw.get("fragment_id")
        if fragment_type not in FRAGMENT_TYPES or fragment_type in seen_types:
            raise ValueError("每个维度恰好选择一个DNA片段")
        if fragment_id not in by_id:
            raise ValueError(f"无效的fragmentId: {fragment_id}")
        fragment = by_id[fragment_id]
        if fragment["type"] != fragment_type:
            raise ValueError("fragmentId与type不匹配")
        seen_types.add(fragment_type)
        selected.append(
            {
                "fragment_id": fragment["fragmentId"],
                "type": fragment["type"],
                "value": fragment["value"],
                "score": fragment["score"],
                "version": fragment.get("version", "1.0"),
                "reason": str(raw.get("reason", "")).strip(),
            }
        )

    if seen_types != set(FRAGMENT_TYPES):
        raise ValueError("每个维度恰好选择一个DNA片段")

    return {
        "selected_fragments": selected,
        "image_summaries": normalize_list_field(data.get("image_summaries")),
        "key_selling_points": normalize_list_field(data.get("key_selling_points"), 5),
        "avoid_points": normalize_list_field(data.get("avoid_points"), 3),
        "suggested_visual_directions": normalize_list_field(
            data.get("suggested_visual_directions"), 9
        ),
    }


def _rule_based_analyze(
    request: LocalFoodRequest,
    candidate_pools: dict[str, list[dict[str, Any]]],
) -> DnaStrategyBrief:
    """Deterministic fallback: choose Top 1 from every dimension."""
    selections = [
        DnaFragmentSelection(
            fragment_id=fragment["fragmentId"],
            type=fragment["type"],
            value=fragment["value"],
            score=fragment["score"],
            version=fragment.get("version", "1.0"),
            reason="",
        )
        for fragment_type in FRAGMENT_TYPES
        for fragment in candidate_pools[fragment_type][:1]
    ]

    image_summaries = [
        f"用户上传的第{i + 1}张产品图片"
        for i, _ in enumerate(request.image_paths[:3])
    ]
    return DnaStrategyBrief(
        product_name=request.product_name,
        product_category=request.product_category,
        origin_place=request.origin_place,
        target_audience=request.target_audience,
        selling_scene=request.selling_scene,
        user_note=request.user_note,
        image_summaries=image_summaries,
        selected_fragments=selections,
        key_selling_points=_rule_key_points(request),
        avoid_points=[
            "避免夸大疗效或虚假宣传",
            "避免硬广式口播感",
            "避免泛泛而谈没有具体体感",
        ],
        suggested_visual_directions=_rule_visual_directions(request),
    )


def _rule_key_points(request: LocalFoodRequest) -> list[str]:
    """Generate a compact set of fallback selling points."""
    points = [f"{request.origin_place}在地特产，地道风味"]
    points.append(f"{request.product_name}，{request.product_category}中的宝藏款")
    if request.selling_scene:
        points.append(f"适合{request.selling_scene}场景")
    if request.user_note:
        points.append(request.user_note[:30])
    return points[:5]


def _rule_visual_directions(request: LocalFoodRequest) -> list[str]:
    """Generate four simple fallback visual directions."""
    return [
        f"{request.product_name}产品主图（特写）",
        f"{request.product_name}包装展示",
        f"{request.origin_place}产地/原料场景",
        f"{request.product_name}食用/使用场景",
    ]
