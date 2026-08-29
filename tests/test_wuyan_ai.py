#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unit tests for wuyan_ai core functionality."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from wuyan_ai.server.main import app
from wuyan_ai.core.schemas import (
    LocalFoodRequest,
    ContentStrategyBrief,
    TemplateMatch,
    GeneratedContentPack,
    VisualAssetSuggestion,
)
from wuyan_ai.core.templates import (
    LOCAL_FOOD_TEMPLATES,
    get_template_definition,
)
from wuyan_ai.core.agents.prompter.agent import build_local_food_content_plan
from wuyan_ai.core.agents.analyzer.agent import build_local_food_strategy_brief


class TestSchemas:
    """测试乡礼 Spark Pydantic schema 验证。"""

    def test_local_food_request_accepts_expected_fields(self):
        """测试地方食品请求schema字段。"""
        req = LocalFoodRequest(
            product_name="贵州刺梨果干",
            product_category="果干",
            origin_place="贵州",
            target_audience="年轻游客",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            target_platforms=["xiaohongshu", "douyin", "moments"],
            selling_scene="游客伴手礼",
            user_note="想做成愿意带走的伴手礼内容",
            image_paths=["/tmp/product.jpg", "/tmp/package.jpg"],
        )
        assert req.product_name == "贵州刺梨果干"
        assert req.primary_goal == "种草引流"
        assert "douyin" in req.target_platforms

    def test_local_food_request_defaults(self):
        """测试地方食品请求默认值。"""
        req = LocalFoodRequest(
            product_name="安吉白茶",
            product_category="茶",
            origin_place="浙江安吉",
            target_audience="送礼人群",
        )
        assert req.primary_goal == "种草引流"
        assert req.secondary_goal == "地方故事增强"
        assert req.target_platforms == ["xiaohongshu", "douyin", "moments"]
        assert req.image_paths == []

    def test_content_strategy_brief_supports_template_selection(self):
        """测试策略brief支持模板选择与解释字段。"""
        brief = ContentStrategyBrief(
            product_name="贵州刺梨果干",
            product_category="果干",
            origin_place="贵州",
            target_audience="年轻游客",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            chosen_template="difference_seed",
            supporting_template="story_boost",
            key_points=["贵州在地感", "酸香差异", "伴手礼属性"],
            avoid_points=["夸大疗效", "泛泛健康宣称"],
            suggested_visual_order=["产品图", "包装图", "产地图"],
        )
        assert brief.chosen_template == "difference_seed"
        assert brief.supporting_template == "story_boost"
        assert "贵州在地感" in brief.key_points

    def test_template_match_tracks_reasoning_and_priority(self):
        """测试模板命中结果schema。"""
        match = TemplateMatch(
            template_name="gift_scene",
            role="primary",
            reason="用户明确强调伴手礼与送礼场景",
            confidence=0.86,
        )
        assert match.template_name == "gift_scene"
        assert match.role == "primary"
        assert match.confidence == 0.86

    def test_generated_content_pack_contains_all_v1_outputs(self):
        """测试内容包包含v1全部输出。"""
        pack = GeneratedContentPack(
            xiaohongshu_post="小红书内容",
            douyin_script="抖音脚本",
            moments_copy="朋友圈短文案",
            hero_title="封面标题",
            story_enhancement="故事增强段",
            visual_card_suggestions=["第一张图放产品图"],
        )
        assert pack.hero_title == "封面标题"
        assert len(pack.visual_card_suggestions) == 1

    def test_visual_asset_suggestion_defaults(self):
        """测试视觉资产建议schema默认值。"""
        suggestion = VisualAssetSuggestion(
            hero_title="贵州山里带回来的酸香果干",
        )
        assert suggestion.hero_title.startswith("贵州")
        assert suggestion.visual_card_suggestions == []


class TestLocalFoodTemplates:
    """测试地方食品模板库。"""

    def test_local_food_templates_include_all_v1_templates(self):
        """测试模板库包含全部4个v1模板。"""
        assert "difference_seed" in LOCAL_FOOD_TEMPLATES
        assert "gift_scene" in LOCAL_FOOD_TEMPLATES
        assert "local_story_seed" in LOCAL_FOOD_TEMPLATES
        assert "story_boost" in LOCAL_FOOD_TEMPLATES

    def test_get_template_definition_returns_expected_display_name_and_sections(self):
        """测试根据模板名读取模板定义。"""
        difference_template = get_template_definition("difference_seed")
        assert difference_template["display_name"] == "差异点种草模板"
        assert difference_template["sections"] == ["钩子", "差异点定义", "具体体感", "适合谁", "轻CTA"]

        gift_template = get_template_definition("gift_scene")
        assert gift_template["display_name"] == "送礼场景模板"
        assert gift_template["sections"] == ["场景钩子", "礼感来源", "适合送谁", "送礼后的感受", "行动引导"]

    def test_get_template_definition_raises_key_error_for_unknown_template(self):
        """测试不存在的模板名抛出KeyError。"""
        try:
            get_template_definition("unknown_template")
            assert False, "应该抛出KeyError"
        except KeyError:
            pass


class TestLocalFoodAnalyzer:
    """测试地方食品传播任务分析与模板匹配。"""

    def test_build_local_food_strategy_brief_defaults_to_difference_seed_plus_story_boost(self):
        req = LocalFoodRequest(
            product_name="贵州刺梨果干",
            product_category="果干",
            origin_place="贵州",
            target_audience="年轻游客",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            selling_scene="游客尝鲜",
            user_note="想让外地游客愿意带走，也记住贵州风味",
            image_paths=["product.jpg", "package.jpg", "origin.jpg"],
        )

        brief = build_local_food_strategy_brief(req)

        assert brief.chosen_template == "difference_seed"
        assert brief.supporting_template == "story_boost"
        assert "贵州在地感" in brief.key_points
        assert any("风味差异" in point for point in brief.key_points)
        assert any("游客尝鲜" in point for point in brief.key_points)
        assert brief.avoid_points == ["夸大疗效", "泛泛健康宣称", "硬广式口播"]
        assert brief.suggested_visual_order == ["产品图", "包装图", "产地图"]

    def test_build_local_food_strategy_brief_switches_to_gift_scene_for_explicit_gift_need(self):
        req = LocalFoodRequest(
            product_name="贵州茶礼盒",
            product_category="茶",
            origin_place="贵州",
            target_audience="送礼人群",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            selling_scene="节庆送礼",
            user_note="想突出拿得出手的伴手礼气质",
            image_paths=["package.jpg"],
        )

        brief = build_local_food_strategy_brief(req)

        assert brief.chosen_template == "gift_scene"
        assert brief.supporting_template == "story_boost"
        assert "贵州在地感" in brief.key_points
        assert any("礼感" in point for point in brief.key_points)
        assert any("节庆送礼" in point for point in brief.key_points)
        assert "包装图" in brief.suggested_visual_order


class TestLocalFoodPrompter:
    """测试地方食品多平台内容骨架编排。"""

    def test_build_local_food_content_plan_returns_platform_skeletons_for_difference_seed(self):
        brief = ContentStrategyBrief(
            product_name="贵州刺梨果干",
            product_category="果干",
            origin_place="贵州",
            target_audience="年轻游客",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            chosen_template="difference_seed",
            supporting_template="story_boost",
            key_points=["贵州在地感", "酸香差异", "伴手礼属性"],
            avoid_points=["夸大疗效"],
            suggested_visual_order=["产品图", "包装图", "产地图"],
        )

        plan = build_local_food_content_plan(brief)

        assert plan["xiaohongshu"] == ["钩子", "差异点定义", "具体体感", "适合谁", "轻CTA", "地方故事增强"]
        assert plan["douyin"] == ["强钩子", "快速卖点", "在地感点题", "CTA"]
        assert plan["moments"] == ["一句推荐", "地方亮点", "轻推荐"]
        assert plan["hero"] == ["封面标题", "主卖点短句"]

    def test_build_local_food_content_plan_returns_gift_oriented_sections(self):
        brief = ContentStrategyBrief(
            product_name="贵州茶礼盒",
            product_category="茶",
            origin_place="贵州",
            target_audience="送礼人群",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            chosen_template="gift_scene",
            supporting_template="story_boost",
            key_points=["贵州在地感", "礼感", "节庆送礼"],
            avoid_points=["夸大疗效"],
            suggested_visual_order=["包装图", "产品图", "产地图"],
        )

        plan = build_local_food_content_plan(brief)

        assert plan["xiaohongshu"] == ["场景钩子", "礼感来源", "适合送谁", "送礼后的感受", "行动引导", "地方故事增强"]
        assert plan["douyin"] == ["礼物痛点钩子", "礼感亮点", "适合谁送", "CTA"]
        assert plan["moments"] == ["送礼推荐", "地方亮点", "轻推荐"]
        assert plan["hero"] == ["封面标题", "礼盒短句"]


class TestLocalFoodCopywriter:
    """测试地方食品多平台内容包生成。"""

    def _make_difference_seed_request_and_brief(self):
        req = LocalFoodRequest(
            product_name="贵州刺梨果干",
            product_category="果干",
            origin_place="贵州",
            target_audience="年轻游客",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            selling_scene="游客伴手礼",
            user_note="想做成游客愿意带走的伴手礼内容",
            image_paths=["product.jpg", "package.jpg", "origin.jpg"],
        )
        brief = ContentStrategyBrief(
            product_name="贵州刺梨果干",
            product_category="果干",
            origin_place="贵州",
            target_audience="年轻游客",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            chosen_template="difference_seed",
            supporting_template="story_boost",
            key_points=["贵州在地感", "酸香差异", "伴手礼属性"],
            avoid_points=["夸大疗效"],
            suggested_visual_order=["产品图", "包装图", "产地图"],
        )
        content_plan = {
            "xiaohongshu": ["钩子", "差异点定义", "具体体感", "适合谁", "轻CTA", "地方故事增强"],
            "douyin": ["强钩子", "快速卖点", "在地感点题", "CTA"],
            "moments": ["一句推荐", "地方亮点", "轻推荐"],
            "hero": ["封面标题", "主卖点短句"],
        }
        return req, brief, content_plan

    def _make_gift_scene_request_and_brief(self):
        req = LocalFoodRequest(
            product_name="贵州茶礼盒",
            product_category="茶",
            origin_place="贵州",
            target_audience="送礼人群",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            selling_scene="节庆送礼",
            user_note="想突出拿得出手的伴手礼气质",
            image_paths=["package.jpg", "product.jpg", "origin.jpg"],
        )
        brief = ContentStrategyBrief(
            product_name="贵州茶礼盒",
            product_category="茶",
            origin_place="贵州",
            target_audience="送礼人群",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            chosen_template="gift_scene",
            supporting_template="story_boost",
            key_points=["贵州在地感", "礼感", "节庆送礼"],
            avoid_points=["夸大疗效"],
            suggested_visual_order=["包装图", "产品图", "产地图"],
        )
        content_plan = {
            "xiaohongshu": ["场景钩子", "礼感来源", "适合送谁", "送礼后的感受", "行动引导", "地方故事增强"],
            "douyin": ["礼物痛点钩子", "礼感亮点", "适合谁送", "CTA"],
            "moments": ["送礼推荐", "地方亮点", "轻推荐"],
            "hero": ["封面标题", "礼盒短句"],
        }
        return req, brief, content_plan

    def test_difference_seed_pack_contains_all_expected_outputs(self):
        """差异点种草模板：内容包包含 v1 五项输出且引用关键字段。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        req, brief, content_plan = self._make_difference_seed_request_and_brief()
        pack = generate_local_food_content_pack(req, brief, content_plan)

        assert pack.xiaohongshu_post.strip()
        assert pack.douyin_script.strip()
        assert pack.moments_copy.strip()
        assert pack.hero_title.strip()
        assert pack.story_enhancement.strip()

        assert len(pack.visual_card_suggestions) >= 2

        assert "贵州刺梨果干" in pack.xiaohongshu_post
        assert "贵州" in pack.story_enhancement
        assert "游客伴手礼" in pack.xiaohongshu_post or "游客伴手礼" in pack.douyin_script
        assert "贵州" in pack.hero_title
        assert "贵州" in pack.douyin_script

    def test_difference_seed_pack_leans_toward_difference_seeding_framing(self):
        """差异点种草模板：内容倾向差异点种草口吻而非送礼口吻。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        req, brief, content_plan = self._make_difference_seed_request_and_brief()
        pack = generate_local_food_content_pack(req, brief, content_plan)

        assert "强钩子" in pack.douyin_script
        assert "在地感点题" in pack.douyin_script
        assert "别再把" in pack.xiaohongshu_post or "普通" in pack.xiaohongshu_post
        assert "礼物痛点钩子" not in pack.douyin_script

    def test_difference_seed_pack_story_enhancement_references_origin(self):
        """差异点种草模板：故事增强段引用产地并带风土表达。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        req, brief, content_plan = self._make_difference_seed_request_and_brief()
        pack = generate_local_food_content_pack(req, brief, content_plan)

        assert "贵州" in pack.story_enhancement
        assert "刺梨果干" in pack.story_enhancement
        assert "风土" in pack.story_enhancement or "地方" in pack.story_enhancement

    def test_difference_seed_pack_visual_suggestions_align_with_brief_order(self):
        """差异点种草模板：视觉建议跟随 brief.suggested_visual_order。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        req, brief, content_plan = self._make_difference_seed_request_and_brief()
        pack = generate_local_food_content_pack(req, brief, content_plan)

        suggestions = pack.visual_card_suggestions
        assert len(suggestions) >= 2
        assert "产品图" in suggestions[0]
        assert "包装图" in suggestions[1]
        assert "产地图" in suggestions[2]

    def test_gift_scene_pack_contains_all_expected_outputs(self):
        """送礼场景模板：内容包包含 v1 五项输出且引用关键字段。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        req, brief, content_plan = self._make_gift_scene_request_and_brief()
        pack = generate_local_food_content_pack(req, brief, content_plan)

        assert pack.xiaohongshu_post.strip()
        assert pack.douyin_script.strip()
        assert pack.moments_copy.strip()
        assert pack.hero_title.strip()
        assert pack.story_enhancement.strip()
        assert len(pack.visual_card_suggestions) >= 2

        assert "贵州茶礼盒" in pack.xiaohongshu_post
        assert "贵州" in pack.story_enhancement
        assert "节庆送礼" in pack.xiaohongshu_post or "节庆送礼" in pack.douyin_script
        assert "贵州" in pack.hero_title

    def test_gift_scene_pack_leans_toward_gift_framing(self):
        """送礼场景模板：内容倾向伴手礼/送礼口吻，含礼感关键词。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        req, brief, content_plan = self._make_gift_scene_request_and_brief()
        pack = generate_local_food_content_pack(req, brief, content_plan)

        assert "礼物痛点钩子" in pack.douyin_script
        assert "礼感亮点" in pack.douyin_script
        gift_keywords = ("礼感", "伴手礼", "送礼", "拿得出手")
        assert any(kw in pack.xiaohongshu_post for kw in gift_keywords)
        assert any(kw in pack.moments_copy for kw in gift_keywords)
        assert "强钩子" not in pack.douyin_script

    def test_gift_scene_pack_visual_suggestions_align_with_brief_order(self):
        """送礼场景模板：视觉建议跟随 brief.suggested_visual_order。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        req, brief, content_plan = self._make_gift_scene_request_and_brief()
        pack = generate_local_food_content_pack(req, brief, content_plan)

        suggestions = pack.visual_card_suggestions
        assert len(suggestions) >= 2
        assert "包装图" in suggestions[0]
        assert "产品图" in suggestions[1]
        assert "产地图" in suggestions[2]

    def test_gift_scene_pack_story_enhancement_references_origin_and_scene(self):
        """送礼场景模板：故事增强段引用产地和送礼场景。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        req, brief, content_plan = self._make_gift_scene_request_and_brief()
        pack = generate_local_food_content_pack(req, brief, content_plan)

        assert "贵州" in pack.story_enhancement
        assert "茶礼盒" in pack.story_enhancement
        assert "节庆送礼" in pack.story_enhancement

    def test_difference_seed_and_gift_scene_packs_are_distinct(self):
        """两种模板生成的同一个平台输出不应完全一致。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        diff_req, diff_brief, diff_plan = self._make_difference_seed_request_and_brief()
        gift_req, gift_brief, gift_plan = self._make_gift_scene_request_and_brief()

        diff_pack = generate_local_food_content_pack(diff_req, diff_brief, diff_plan)
        gift_pack = generate_local_food_content_pack(gift_req, gift_brief, gift_plan)

        assert diff_pack.xiaohongshu_post != gift_pack.xiaohongshu_post
        assert diff_pack.douyin_script != gift_pack.douyin_script
        assert diff_pack.hero_title != gift_pack.hero_title

    def test_pack_handles_request_without_selling_scene(self):
        """selling_scene 缺省时不报错，且各输出仍非空。"""
        from wuyan_ai.core.agents.copywriter.agent import (
            generate_local_food_content_pack,
        )

        req = LocalFoodRequest(
            product_name="云南鲜花饼",
            product_category="糕点",
            origin_place="云南",
            target_audience="外地游客",
        )
        brief = ContentStrategyBrief(
            product_name="云南鲜花饼",
            product_category="糕点",
            origin_place="云南",
            target_audience="外地游客",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            chosen_template="difference_seed",
            supporting_template="story_boost",
            key_points=["云南在地感", "花香差异"],
            avoid_points=["夸大疗效"],
            suggested_visual_order=["产品图", "产地图"],
        )
        content_plan = {
            "xiaohongshu": ["钩子", "差异点定义", "具体体感", "适合谁", "轻CTA", "地方故事增强"],
            "douyin": ["强钩子", "快速卖点", "在地感点题", "CTA"],
            "moments": ["一句推荐", "地方亮点", "轻推荐"],
            "hero": ["封面标题", "主卖点短句"],
        }
        pack = generate_local_food_content_pack(req, brief, content_plan)

        assert pack.xiaohongshu_post.strip()
        assert pack.douyin_script.strip()
        assert pack.moments_copy.strip()
        assert pack.hero_title.strip()
        assert pack.story_enhancement.strip()
        assert len(pack.visual_card_suggestions) >= 2
        assert "云南" in pack.xiaohongshu_post


class TestLocalFoodGenerator:
    """测试地方食品视觉资产建议器。"""

    def _make_brief(self, visual_order=None):
        return ContentStrategyBrief(
            product_name="贵州刺梨果干",
            product_category="果干",
            origin_place="贵州",
            target_audience="年轻游客",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            chosen_template="difference_seed",
            supporting_template="story_boost",
            key_points=["贵州在地感", "酸香差异", "伴手礼属性"],
            avoid_points=["夸大疗效"],
            suggested_visual_order=visual_order
            if visual_order is not None
            else ["产品图", "包装图", "产地图"],
        )

    def test_suggest_local_food_visual_assets_returns_ordered_card_guidance(self):
        """返回有序的视觉卡片建议，顺序跟随 brief.suggested_visual_order。"""
        from wuyan_ai.core.agents.generator.agent import (
            suggest_local_food_visual_assets,
        )

        brief = self._make_brief(["产品图", "包装图", "产地图"])
        suggestions = suggest_local_food_visual_assets(brief)

        assert len(suggestions) == 3
        assert suggestions[0].startswith("第一张图")
        assert suggestions[1].startswith("第二张图")
        assert suggestions[2].startswith("第三张图")

    def test_first_suggestion_starts_with_first_card_label(self):
        """第一条建议以'第一张图'开头。"""
        from wuyan_ai.core.agents.generator.agent import (
            suggest_local_food_visual_assets,
        )

        brief = self._make_brief(["产品图", "包装图", "产地图"])
        suggestions = suggest_local_food_visual_assets(brief)

        assert suggestions[0].startswith("第一张图")

    def test_last_suggestion_references_last_visual_order_item(self):
        """最后一条建议引用 suggested_visual_order 的最后一项。"""
        from wuyan_ai.core.agents.generator.agent import (
            suggest_local_food_visual_assets,
        )

        brief = self._make_brief(["产品图", "包装图", "产地图"])
        suggestions = suggest_local_food_visual_assets(brief)

        assert "产地图" in suggestions[-1]

    def test_suggest_local_food_visual_assets_supports_four_cards(self):
        """suggested_visual_order 含 4 项时，输出 4 条且第四条以'第四张图'开头。"""
        from wuyan_ai.core.agents.generator.agent import (
            suggest_local_food_visual_assets,
        )

        brief = self._make_brief(["产品图", "包装图", "产地图", "制作过程图"])
        suggestions = suggest_local_food_visual_assets(brief)

        assert len(suggestions) == 4
        assert suggestions[3].startswith("第四张图")
        assert "制作过程图" in suggestions[3]

    def test_suggest_local_food_visual_assets_empty_order_returns_empty(self):
        """suggested_visual_order 为空时返回空列表。"""
        from wuyan_ai.core.agents.generator.agent import (
            suggest_local_food_visual_assets,
        )

        brief = self._make_brief([])
        suggestions = suggest_local_food_visual_assets(brief)

        assert suggestions == []

    def test_suggest_local_food_visual_assets_each_references_its_visual_type(self):
        """每条建议都引用对应的视觉类型。"""
        from wuyan_ai.core.agents.generator.agent import (
            suggest_local_food_visual_assets,
        )

        order = ["产品图", "包装图", "产地图"]
        brief = self._make_brief(order)
        suggestions = suggest_local_food_visual_assets(brief)

        for suggestion, visual_type in zip(suggestions, order):
            assert visual_type in suggestion


class TestLocalFoodOrchestrator:
    """测试地方食品主编排器串联新流程。"""

    def _make_difference_seed_request(self):
        return LocalFoodRequest(
            product_name="贵州刺梨果干",
            product_category="果干",
            origin_place="贵州",
            target_audience="年轻游客",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            selling_scene="游客尝鲜",
            user_note="想让外地游客愿意带走，也记住贵州风味",
            image_paths=["product.jpg", "package.jpg", "origin.jpg"],
        )

    def _make_gift_scene_request(self):
        return LocalFoodRequest(
            product_name="贵州茶礼盒",
            product_category="茶",
            origin_place="贵州",
            target_audience="送礼人群",
            primary_goal="种草引流",
            secondary_goal="地方故事增强",
            selling_scene="节庆送礼",
            user_note="想突出拿得出手的伴手礼气质",
            image_paths=["package.jpg", "product.jpg"],
        )

    def test_run_local_food_pipeline_returns_brief_and_generated_pack(self):
        """编排器返回 strategy_brief、content_plan、generated_pack 三个键。"""
        from wuyan_ai.core.orchestrator import run_local_food_pipeline

        req = self._make_difference_seed_request()
        result = run_local_food_pipeline(req)

        assert "strategy_brief" in result
        assert "content_plan" in result
        assert "generated_pack" in result

    def test_chosen_template_propagates_through_result_difference_seed(self):
        """difference_seed 模板在 brief 与 generated_pack 之间一致传播。"""
        from wuyan_ai.core.orchestrator import run_local_food_pipeline

        req = self._make_difference_seed_request()
        result = run_local_food_pipeline(req)

        brief = result["strategy_brief"]
        assert brief.chosen_template == "difference_seed"
        assert brief.supporting_template == "story_boost"

    def test_chosen_template_propagates_through_result_gift_scene(self):
        """gift_scene 模板在 brief 与 generated_pack 之间一致传播。"""
        from wuyan_ai.core.orchestrator import run_local_food_pipeline

        req = self._make_gift_scene_request()
        result = run_local_food_pipeline(req)

        brief = result["strategy_brief"]
        assert brief.chosen_template == "gift_scene"
        assert brief.supporting_template == "story_boost"

    def test_generated_pack_exists_and_hero_title_non_empty(self):
        """generated_pack 存在且 hero_title 非空。"""
        from wuyan_ai.core.orchestrator import run_local_food_pipeline

        req = self._make_difference_seed_request()
        result = run_local_food_pipeline(req)

        pack = result["generated_pack"]
        assert pack is not None
        assert isinstance(pack.hero_title, str)
        assert pack.hero_title.strip() != ""

    def test_visual_suggestions_present_in_generated_pack(self):
        """视觉建议被注入到 generated_pack.visual_card_suggestions 中。"""
        from wuyan_ai.core.orchestrator import run_local_food_pipeline

        req = self._make_difference_seed_request()
        result = run_local_food_pipeline(req)

        pack = result["generated_pack"]
        assert len(pack.visual_card_suggestions) > 0
        assert pack.visual_card_suggestions[0].startswith("第一张图")

    def test_visual_suggestions_injected_match_brief_visual_order(self):
        """注入的视觉建议顺序与 brief.suggested_visual_order 一致。"""
        from wuyan_ai.core.orchestrator import run_local_food_pipeline

        req = self._make_difference_seed_request()
        result = run_local_food_pipeline(req)

        brief = result["strategy_brief"]
        pack = result["generated_pack"]
        assert len(pack.visual_card_suggestions) == len(brief.suggested_visual_order)
        for suggestion, visual_type in zip(
            pack.visual_card_suggestions, brief.suggested_visual_order
        ):
            assert visual_type in suggestion

    def test_content_plan_has_expected_platforms(self):
        """content_plan 包含 xiaohongshu、douyin、moments、hero 四个平台骨架。"""
        from wuyan_ai.core.orchestrator import run_local_food_pipeline

        req = self._make_difference_seed_request()
        result = run_local_food_pipeline(req)

        plan = result["content_plan"]
        assert "xiaohongshu" in plan
        assert "douyin" in plan
        assert "moments" in plan
        assert "hero" in plan
        assert len(plan["xiaohongshu"]) > 0


class TestLocalFoodAPI:
    """测试地方食品生成 API。"""

    def _payload(self):
        return {
            "product_name": "贵州刺梨果干",
            "product_category": "果干",
            "origin_place": "贵州",
            "target_audience": "年轻游客",
            "primary_goal": "种草引流",
            "secondary_goal": "地方故事增强",
            "target_platforms": ["xiaohongshu", "douyin", "moments"],
            "selling_scene": "游客尝鲜",
            "user_note": "想突出贵州风味差异，让游客愿意带走",
            "image_paths": ["product.jpg", "package.jpg", "origin.jpg"],
        }

    def test_generate_local_food_api_returns_200(self):
        client = TestClient(app)
        response = client.post("/api/generate-local-food", json=self._payload())
        assert response.status_code == 200

    def test_generate_local_food_api_exposes_chosen_template(self):
        client = TestClient(app)
        response = client.post("/api/generate-local-food", json=self._payload())
        data = response.json()
        assert data["strategy_brief"]["chosen_template"] == "difference_seed"

    def test_generate_local_food_api_returns_non_empty_hero_title(self):
        client = TestClient(app)
        response = client.post("/api/generate-local-food", json=self._payload())
        data = response.json()
        assert data["generated_pack"]["hero_title"].strip() != ""
