#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Current unit tests for the two-agent content pipeline."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wuyan_ai.core.agents.analyzer.agent import _rule_based_analyze
from wuyan_ai.core.agents.creator._prompts import build_user_prompt
from wuyan_ai.core.agents.creator.agent import _rule_based_create
from wuyan_ai.core.dnas import get_top_fragments_by_type
from wuyan_ai.core.schemas import (
    DnaFragmentSelection,
    DnaStrategyBrief,
    GenerateResult,
    LocalFoodRequest,
)


def _request() -> LocalFoodRequest:
    return LocalFoodRequest(
        product_name="椒麻鸡",
        product_category="熟食",
        origin_place="成都",
        target_audience="附近下班后的年轻人",
        selling_scene="晚餐到店",
        user_note="人均32元，想突出分量和香味",
    )


def test_local_food_request_defaults_image_paths_to_empty_list():
    request = LocalFoodRequest(
        product_name="安吉白茶",
        product_category="茶",
        origin_place="浙江安吉",
        target_audience="送礼人群",
    )

    assert request.image_paths == []
    assert request.selling_scene is None


def test_rule_fallback_selects_one_fragment_for_each_dimension():
    request = _request()
    brief = _rule_based_analyze(request, get_top_fragments_by_type(limit=10))

    assert len(brief.selected_fragments) == 6
    assert {item.type for item in brief.selected_fragments} == {
        "scene", "valuePromise", "hook", "structure", "tone", "visualStyle",
    }
    assert all(item.score > 0 for item in brief.selected_fragments)


def test_creator_prompt_contains_selected_fragment_values():
    pools = get_top_fragments_by_type(limit=10)
    selected = [pools[fragment_type][0] for fragment_type in pools]
    prompt = build_user_prompt(
        {
            **_request().model_dump(),
            "selected_fragments": [
                {
                    "fragment_id": item["fragmentId"],
                    "type": item["type"],
                    "value": item["value"],
                    "score": item["score"],
                    "version": item["version"],
                    "reason": "测试",
                }
                for item in selected
            ],
            "key_selling_points": ["分量足"],
            "avoid_points": ["不夸大"],
            "image_summaries": [],
        },
        selected,
    )

    assert "下班后附近餐饮推荐" in prompt
    assert "价格对比 + 结果反差" in prompt
    assert "视觉风格" in prompt


def test_rule_creator_preserves_selected_fragments_in_result():
    request = _request()
    brief = _rule_based_analyze(request, get_top_fragments_by_type(limit=10))
    result = _rule_based_create(brief)

    assert isinstance(result, GenerateResult)
    assert result.selected_fragments == brief.selected_fragments
    assert result.post.title
    assert len(result.image_suggestions) >= 3


def test_selected_fragment_schema_rejects_invalid_score():
    try:
        DnaFragmentSelection(
            fragment_id="hook_001",
            type="hook",
            value="价格反差",
            score=1.2,
        )
        assert False, "score超过1应该校验失败"
    except ValueError:
        pass
