#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the fine-grained DNA library and analyzer contract."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from wuyan_ai.core.dnas import (
    FRAGMENT_TYPES,
    get_top_fragments,
    get_top_fragments_by_type,
    list_fragments,
)
from wuyan_ai.core.agents.analyzer._prompts import build_user_prompt
from wuyan_ai.core.agents.analyzer.agent import _parse_llm_response


def test_mock_library_has_twenty_fragments_for_each_required_dimension():
    pools = get_top_fragments_by_type(limit=20)

    assert set(pools) == set(FRAGMENT_TYPES)
    for fragment_type in FRAGMENT_TYPES:
        fragments = pools[fragment_type]
        assert len(fragments) == 20
        assert all(fragment["type"] == fragment_type for fragment in fragments)
        assert all(fragment["fragmentId"].startswith(f"{fragment_type}_") for fragment in fragments)
        assert all(0 <= fragment["score"] <= 1 for fragment in fragments)


def test_top_fragments_are_sorted_by_score_and_skip_retired_entries():
    fragments = get_top_fragments("hook", limit=10)
    scores = [fragment["score"] for fragment in fragments]

    assert len(fragments) == 10
    assert scores == sorted(scores, reverse=True)
    assert all(fragment["state"] != "retired" for fragment in fragments)


def test_analyzer_prompt_contains_top_ten_candidates_for_each_dimension():
    pools = get_top_fragments_by_type(limit=10)
    prompt = build_user_prompt(
        {
            "product_name": "椒麻鸡",
            "product_category": "熟食",
            "origin_place": "成都",
            "target_audience": "附近下班后的年轻人",
            "selling_scene": "晚餐到店",
            "user_note": "人均32元",
        },
        pools,
        has_images=False,
    )

    for fragment_type in FRAGMENT_TYPES:
        assert prompt.count(f"{fragment_type}_") >= 10


def test_analyzer_response_requires_one_selection_per_dimension():
    pools = get_top_fragments_by_type(limit=10)
    selections = [
        {
            "type": fragment_type,
            "fragmentId": pools[fragment_type][0]["fragmentId"],
            "reason": f"选择{fragment_type}",
        }
        for fragment_type in FRAGMENT_TYPES
    ]

    parsed = _parse_llm_response(json.dumps({"selectedFragments": selections}), pools)

    assert {item["type"] for item in parsed["selected_fragments"]} == set(FRAGMENT_TYPES)
    assert len(parsed["selected_fragments"]) == len(FRAGMENT_TYPES)

    with pytest.raises(ValueError, match="每个维度恰好选择一个"):
        _parse_llm_response(
            json.dumps({"selectedFragments": selections[:-1]}),
            pools,
        )
