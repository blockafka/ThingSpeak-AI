# 乡土代言人（地方食品特产内容策略助理）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 StyleDNA 家装内容生成项目改造成“乡土代言人”第一版：一个面向地方食品特产商家的、以种草引流优先和地方故事增强为核心的 AI 内容策略助理。

**Architecture:** 保留现有 FastAPI + SSE + React + Pydantic + 多 Agent 管线骨架，将旧项目的“风格克隆”替换为“传播任务识别 + 模板匹配 + 多平台内容包生成”。主链路以文本内容策略为中心，视觉模块第一版退化为“视觉资产建议器”而非强依赖 AI 生图。

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, React, Vite, pytest, existing OpenAI-compatible LLM wrapper, optional ffmpeg/Whisper deferred out of v1 mainline

## Global Constraints

- 第一版只做**地方食品类特产**，不覆盖所有文旅品类。
- 第一版主目标固定为**种草引流优先，地方故事增强**。
- 新项目**不**以“爆款 DNA 提取”作为核心卖点，必须以**传播任务识别 + 内容模板匹配**为核心叙事。
- 结果页必须显式展示：主传播任务、次传播任务、命中的模板、推荐表达重点。
- 第一版输出必须包含：小红书种草文案、抖音短视频脚本、朋友圈短文案、海报/封面主文案、地方故事增强段。
- 第一版主模板库只做 3 个主模板：差异点种草、送礼场景、地方故事种草；默认组合为“差异点种草模板（主）+ 地方故事增强段（辅）”。
- 第一版主链路**不依赖**真实平台发帖 API、复杂视频生成、语音转写、销量归因或多租户能力。
- 沿用现有 Web + SSE 演示方式，路演重点是“低门槛输入 + 可解释策略识别 + 多平台内容包 + 裸写对比”。
- 遵循 DRY、YAGNI、TDD、频繁提交。

---

## File Structure

### Existing files to modify

- `interior_content_skill/core/schemas.py`
  - 新增乡土代言人的请求、策略 brief、模板类型、生成内容包等 schema；保留旧 schema 兼容。
- `interior_content_skill/core/agents/analyzer.py`
  - 从 Style DNA 提取器扩展/改造为支持“地方食品特产传播任务识别”。
- `interior_content_skill/core/agents/prompter.py`
  - 从图像 prompt 生成器改造成内容模板编排器。
- `interior_content_skill/core/agents/generator.py`
  - 从效果图生成器改造成视觉资产建议器（第一版主链路可降级）。
- `interior_content_skill/core/agents/copywriter.py`
  - 从单篇小红书文案生成器改造成多平台内容包生成器。
- `interior_content_skill/core/orchestrator.py`
  - 串联新 brief、planner、generator、copywriter 并返回新结果结构。
- `interior_content_skill/server/main.py`
  - 接收新请求字段，SSE 推送新阶段和新结果。
- `interior_content_skill/web/src/*`
  - 表单、进度展示、结果展示改为“乡土代言人”语义。
- `interior_content_skill/README.md` 或项目 README
  - 更新说明为地方食品特产场景。

### New files to create

- `interior_content_skill/core/templates/local_food_templates.py`
  - 定义第一版 3 个主模板和故事增强层结构。
- `interior_content_skill/core/agents/strategy_brief.py`
  - 如现有 analyzer 文件过大，则拆出策略 brief 构建逻辑。
- `tests/core/test_local_food_schemas.py`
  - schema 测试。
- `tests/core/test_local_food_analyzer.py`
  - 传播任务识别与模板选择测试。
- `tests/core/test_local_food_prompter.py`
  - 内容骨架编排测试。
- `tests/core/test_local_food_copywriter.py`
  - 多平台内容包输出测试。
- `tests/server/test_local_food_generate_api.py`
  - API/SSE 返回新结构测试。
- `docs/superpowers/plans/2026-07-05-xiangtu-da-yanren-implementation-plan.md`
  - 本计划文件。

---

### Task 1: Define new data contracts for 乡土代言人

**Files:**
- Modify: `interior_content_skill/core/schemas.py`
- Test: `tests/core/test_local_food_schemas.py`

**Interfaces:**
- Consumes: existing Pydantic BaseModel conventions in `schemas.py`
- Produces:
  - `LocalFoodRequest`
  - `ContentStrategyBrief`
  - `TemplateMatch`
  - `GeneratedContentPack`
  - `VisualAssetSuggestion`

- [ ] **Step 1: Write the failing test**

```python
from interior_content_skill.core.schemas import (
    LocalFoodRequest,
    ContentStrategyBrief,
    GeneratedContentPack,
)


def test_local_food_request_accepts_expected_fields():
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


def test_content_strategy_brief_supports_template_selection():
    brief = ContentStrategyBrief(
        product_name="贵州刺梨果干",
        product_category="果干",
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
    assert "贵州在地感" in brief.key_points


def test_generated_content_pack_contains_all_v1_outputs():
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_local_food_schemas.py -v`
Expected: FAIL with `ImportError` or `AttributeError` because new schema classes do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from typing import Literal
from pydantic import BaseModel, Field

TargetPlatform = Literal["xiaohongshu", "douyin", "moments"]
TemplateName = Literal["difference_seed", "gift_scene", "local_story_seed", "story_boost"]


class LocalFoodRequest(BaseModel):
    product_name: str
    product_category: str
    origin_place: str
    target_audience: str
    primary_goal: str = "种草引流"
    secondary_goal: str = "地方故事增强"
    target_platforms: list[TargetPlatform] = Field(default_factory=lambda: ["xiaohongshu", "douyin", "moments"])
    selling_scene: str | None = None
    user_note: str | None = None
    image_paths: list[str] = Field(default_factory=list)


class ContentStrategyBrief(BaseModel):
    product_name: str
    product_category: str
    target_audience: str
    primary_goal: str
    secondary_goal: str | None = None
    chosen_template: TemplateName
    supporting_template: TemplateName | None = None
    key_points: list[str] = Field(default_factory=list)
    avoid_points: list[str] = Field(default_factory=list)
    suggested_visual_order: list[str] = Field(default_factory=list)


class VisualAssetSuggestion(BaseModel):
    hero_title: str
    visual_card_suggestions: list[str] = Field(default_factory=list)


class GeneratedContentPack(BaseModel):
    xiaohongshu_post: str
    douyin_script: str
    moments_copy: str
    hero_title: str
    story_enhancement: str
    visual_card_suggestions: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_local_food_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add interior_content_skill/core/schemas.py tests/core/test_local_food_schemas.py
git commit -m "feat: add local food content schemas"
```

### Task 2: Create the v1 template library for local food content

**Files:**
- Create: `interior_content_skill/core/templates/local_food_templates.py`
- Test: `tests/core/test_local_food_analyzer.py`

**Interfaces:**
- Consumes: `TemplateName` values from `schemas.py`
- Produces:
  - `LOCAL_FOOD_TEMPLATES: dict[str, dict]`
  - `get_template_definition(template_name: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
from interior_content_skill.core.templates.local_food_templates import (
    LOCAL_FOOD_TEMPLATES,
    get_template_definition,
)


def test_local_food_templates_define_three_primary_templates_and_story_boost():
    assert "difference_seed" in LOCAL_FOOD_TEMPLATES
    assert "gift_scene" in LOCAL_FOOD_TEMPLATES
    assert "local_story_seed" in LOCAL_FOOD_TEMPLATES
    assert "story_boost" in LOCAL_FOOD_TEMPLATES


def test_difference_seed_template_has_required_sections():
    template = get_template_definition("difference_seed")
    assert template["display_name"] == "差异点种草模板"
    assert template["sections"] == ["钩子", "差异点定义", "具体体感", "适合谁", "轻CTA"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_local_food_analyzer.py::test_local_food_templates_define_three_primary_templates_and_story_boost -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
LOCAL_FOOD_TEMPLATES = {
    "difference_seed": {
        "display_name": "差异点种草模板",
        "sections": ["钩子", "差异点定义", "具体体感", "适合谁", "轻CTA"],
        "use_when": ["种草引流", "第一次尝鲜", "游客伴手礼"],
    },
    "gift_scene": {
        "display_name": "送礼场景模板",
        "sections": ["场景钩子", "礼感来源", "适合送谁", "送礼后的感受", "行动引导"],
        "use_when": ["送礼", "伴手礼", "节庆礼盒"],
    },
    "local_story_seed": {
        "display_name": "地方故事种草模板",
        "sections": ["先讲地方/人", "再讲产品", "讲形成原因", "建立连接", "轻收口"],
        "use_when": ["地方特色", "地域表达", "风土故事"],
    },
    "story_boost": {
        "display_name": "地方故事增强段",
        "sections": ["产地说明", "在地习惯", "风土背景"],
        "use_when": ["辅助增强"],
    },
}


def get_template_definition(template_name: str) -> dict:
    return LOCAL_FOOD_TEMPLATES[template_name]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_local_food_analyzer.py::test_local_food_templates_define_three_primary_templates_and_story_boost tests/core/test_local_food_analyzer.py::test_difference_seed_template_has_required_sections -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add interior_content_skill/core/templates/local_food_templates.py tests/core/test_local_food_analyzer.py
git commit -m "feat: add local food content template library"
```

### Task 3: Implement task analysis and template matching

**Files:**
- Modify: `interior_content_skill/core/agents/analyzer.py`
- Modify or Create: `interior_content_skill/core/agents/strategy_brief.py`
- Test: `tests/core/test_local_food_analyzer.py`

**Interfaces:**
- Consumes: `LocalFoodRequest`, `ContentStrategyBrief`, `LOCAL_FOOD_TEMPLATES`
- Produces:
  - `build_local_food_strategy_brief(request: LocalFoodRequest) -> ContentStrategyBrief`

- [ ] **Step 1: Write the failing test**

```python
from interior_content_skill.core.agents.analyzer import build_local_food_strategy_brief
from interior_content_skill.core.schemas import LocalFoodRequest


def test_build_local_food_strategy_brief_defaults_to_difference_seed_plus_story_boost():
    req = LocalFoodRequest(
        product_name="贵州刺梨果干",
        product_category="果干",
        origin_place="贵州",
        target_audience="年轻游客",
        primary_goal="种草引流",
        secondary_goal="地方故事增强",
        selling_scene="游客伴手礼",
        user_note="想让外地游客愿意带走",
        image_paths=["product.jpg", "package.jpg", "origin.jpg"],
    )
    brief = build_local_food_strategy_brief(req)
    assert brief.chosen_template == "difference_seed"
    assert brief.supporting_template == "story_boost"
    assert "贵州在地感" in brief.key_points


def test_build_local_food_strategy_brief_switches_to_gift_scene_for_explicit_gift_need():
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_local_food_analyzer.py::test_build_local_food_strategy_brief_defaults_to_difference_seed_plus_story_boost tests/core/test_local_food_analyzer.py::test_build_local_food_strategy_brief_switches_to_gift_scene_for_explicit_gift_need -v`
Expected: FAIL because `build_local_food_strategy_brief` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from interior_content_skill.core.schemas import ContentStrategyBrief, LocalFoodRequest


def build_local_food_strategy_brief(request: LocalFoodRequest) -> ContentStrategyBrief:
    is_gift = "送礼" in (request.selling_scene or "") or "送礼" in (request.user_note or "") or "伴手礼" in (request.selling_scene or "")
    chosen_template = "gift_scene" if is_gift and request.product_category in {"茶", "礼盒", "果干", "米酒"} else "difference_seed"

    key_points = [request.origin_place + "在地感"]
    if request.product_category == "果干":
        key_points.append("风味差异")
    if request.selling_scene:
        key_points.append(request.selling_scene)
    if "伴手礼" in (request.selling_scene or ""):
        key_points.append("伴手礼属性")

    suggested_visual_order = ["产品图", "包装图"]
    if len(request.image_paths) >= 3:
        suggested_visual_order.append("产地图")

    return ContentStrategyBrief(
        product_name=request.product_name,
        product_category=request.product_category,
        target_audience=request.target_audience,
        primary_goal=request.primary_goal,
        secondary_goal=request.secondary_goal,
        chosen_template=chosen_template,
        supporting_template="story_boost",
        key_points=key_points,
        avoid_points=["夸大疗效", "泛泛健康宣称", "硬广式口播"],
        suggested_visual_order=suggested_visual_order,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_local_food_analyzer.py::test_build_local_food_strategy_brief_defaults_to_difference_seed_plus_story_boost tests/core/test_local_food_analyzer.py::test_build_local_food_strategy_brief_switches_to_gift_scene_for_explicit_gift_need -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add interior_content_skill/core/agents/analyzer.py interior_content_skill/core/agents/strategy_brief.py tests/core/test_local_food_analyzer.py
git commit -m "feat: add local food strategy brief analysis"
```

### Task 4: Implement template planning for multi-platform content skeletons

**Files:**
- Modify: `interior_content_skill/core/agents/prompter.py`
- Test: `tests/core/test_local_food_prompter.py`

**Interfaces:**
- Consumes: `ContentStrategyBrief`
- Produces:
  - `build_local_food_content_plan(brief: ContentStrategyBrief) -> dict[str, list[str]]`

- [ ] **Step 1: Write the failing test**

```python
from interior_content_skill.core.agents.prompter import build_local_food_content_plan
from interior_content_skill.core.schemas import ContentStrategyBrief


def test_build_local_food_content_plan_returns_platform_skeletons():
    brief = ContentStrategyBrief(
        product_name="贵州刺梨果干",
        product_category="果干",
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
    assert plan["douyin"][0] == "强钩子"
    assert plan["moments"][-1] == "轻推荐"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_local_food_prompter.py -v`
Expected: FAIL because `build_local_food_content_plan` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def build_local_food_content_plan(brief):
    if brief.chosen_template == "difference_seed":
        return {
            "xiaohongshu": ["钩子", "差异点定义", "具体体感", "适合谁", "轻CTA", "地方故事增强"],
            "douyin": ["强钩子", "快速卖点", "在地感点题", "CTA"],
            "moments": ["一句推荐", "地方亮点", "轻推荐"],
            "hero": ["封面标题", "主卖点短句"],
        }
    return {
        "xiaohongshu": ["场景钩子", "礼感来源", "适合送谁", "送礼后的感受", "行动引导", "地方故事增强"],
        "douyin": ["礼物痛点钩子", "礼感亮点", "适合谁送", "CTA"],
        "moments": ["送礼推荐", "地方感", "轻推荐"],
        "hero": ["封面标题", "礼盒短句"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_local_food_prompter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add interior_content_skill/core/agents/prompter.py tests/core/test_local_food_prompter.py
git commit -m "feat: add local food multi-platform content planner"
```

### Task 5: Implement multi-platform content pack generation

**Files:**
- Modify: `interior_content_skill/core/agents/copywriter.py`
- Test: `tests/core/test_local_food_copywriter.py`

**Interfaces:**
- Consumes: `LocalFoodRequest`, `ContentStrategyBrief`, `build_local_food_content_plan()`
- Produces:
  - `generate_local_food_content_pack(request: LocalFoodRequest, brief: ContentStrategyBrief, content_plan: dict[str, list[str]]) -> GeneratedContentPack`

- [ ] **Step 1: Write the failing test**

```python
from interior_content_skill.core.agents.copywriter import generate_local_food_content_pack
from interior_content_skill.core.schemas import ContentStrategyBrief, LocalFoodRequest


def test_generate_local_food_content_pack_contains_all_expected_outputs():
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
    pack = generate_local_food_content_pack(req, brief, content_plan)
    assert "贵州刺梨果干" in pack.xiaohongshu_post
    assert "贵州" in pack.story_enhancement
    assert pack.hero_title
    assert len(pack.visual_card_suggestions) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_local_food_copywriter.py -v`
Expected: FAIL because `generate_local_food_content_pack` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from interior_content_skill.core.schemas import GeneratedContentPack


def generate_local_food_content_pack(request, brief, content_plan):
    story_enhancement = f"在{request.origin_place}，很多人记住{request.product_name}，不是因为它只是特产，而是因为它带着很鲜明的地方味道。"
    xiaohongshu_post = (
        f"别再把{request.product_name}当普通{request.product_category}了。\n"
        f"这类来自{request.origin_place}的{request.product_category}，更适合做{request.selling_scene or '尝鲜选择'}。\n"
        f"如果你也在找一份更有地方感的选择，这个真的值得试试。"
    )
    douyin_script = (
        f"来{request.origin_place}别只会随手买零食，{request.product_name}这种更像能带走的地方味道。\n"
        f"它的重点不是普通{request.product_category}，而是更有地方感、更适合{request.target_audience}。"
    )
    moments_copy = f"这次看到一个挺适合{request.selling_scene or '带回去'}的{request.product_name}，有点地方特色，不是那种很泛的东西。"
    hero_title = f"来{request.origin_place}，这份{request.product_name}值得带走"
    visual_card_suggestions = [
        "第一张图：产品近景突出质感",
        "第二张图：包装图突出伴手礼属性",
        "第三张图：产地图或原料图补地方感",
    ]
    return GeneratedContentPack(
        xiaohongshu_post=xiaohongshu_post,
        douyin_script=douyin_script,
        moments_copy=moments_copy,
        hero_title=hero_title,
        story_enhancement=story_enhancement,
        visual_card_suggestions=visual_card_suggestions,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_local_food_copywriter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add interior_content_skill/core/agents/copywriter.py tests/core/test_local_food_copywriter.py
git commit -m "feat: generate local food multi-platform content pack"
```

### Task 6: Reframe generator as visual asset suggester

**Files:**
- Modify: `interior_content_skill/core/agents/generator.py`
- Test: `tests/core/test_local_food_copywriter.py`

**Interfaces:**
- Consumes: `ContentStrategyBrief`
- Produces:
  - `suggest_local_food_visual_assets(brief: ContentStrategyBrief) -> list[str]`

- [ ] **Step 1: Write the failing test**

```python
from interior_content_skill.core.agents.generator import suggest_local_food_visual_assets
from interior_content_skill.core.schemas import ContentStrategyBrief


def test_suggest_local_food_visual_assets_returns_ordered_card_guidance():
    brief = ContentStrategyBrief(
        product_name="贵州刺梨果干",
        product_category="果干",
        target_audience="年轻游客",
        primary_goal="种草引流",
        secondary_goal="地方故事增强",
        chosen_template="difference_seed",
        supporting_template="story_boost",
        key_points=["贵州在地感", "酸香差异", "伴手礼属性"],
        avoid_points=["夸大疗效"],
        suggested_visual_order=["产品图", "包装图", "产地图"],
    )
    suggestions = suggest_local_food_visual_assets(brief)
    assert suggestions[0].startswith("第一张图")
    assert "产地图" in suggestions[-1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_local_food_copywriter.py::test_suggest_local_food_visual_assets_returns_ordered_card_guidance -v`
Expected: FAIL because `suggest_local_food_visual_assets` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def suggest_local_food_visual_assets(brief):
    labels = ["第一张图", "第二张图", "第三张图", "第四张图"]
    return [f"{labels[idx]}：建议使用{item}" for idx, item in enumerate(brief.suggested_visual_order)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_local_food_copywriter.py::test_suggest_local_food_visual_assets_returns_ordered_card_guidance -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add interior_content_skill/core/agents/generator.py tests/core/test_local_food_copywriter.py
git commit -m "feat: add local food visual asset suggestions"
```

### Task 7: Wire the new local-food flow through the orchestrator

**Files:**
- Modify: `interior_content_skill/core/orchestrator.py`
- Test: `tests/core/test_local_food_copywriter.py`

**Interfaces:**
- Consumes:
  - `build_local_food_strategy_brief()`
  - `build_local_food_content_plan()`
  - `suggest_local_food_visual_assets()`
  - `generate_local_food_content_pack()`
- Produces:
  - `run_local_food_pipeline(request: LocalFoodRequest) -> dict`

- [ ] **Step 1: Write the failing test**

```python
from interior_content_skill.core.orchestrator import run_local_food_pipeline
from interior_content_skill.core.schemas import LocalFoodRequest


def test_run_local_food_pipeline_returns_brief_and_generated_pack():
    req = LocalFoodRequest(
        product_name="贵州刺梨果干",
        product_category="果干",
        origin_place="贵州",
        target_audience="年轻游客",
        primary_goal="种草引流",
        secondary_goal="地方故事增强",
        selling_scene="游客伴手礼",
        user_note="想做成愿意带走的伴手礼内容",
        image_paths=["product.jpg", "package.jpg", "origin.jpg"],
    )
    result = run_local_food_pipeline(req)
    assert result["strategy_brief"].chosen_template == "difference_seed"
    assert "generated_pack" in result
    assert result["generated_pack"].hero_title
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_local_food_copywriter.py::test_run_local_food_pipeline_returns_brief_and_generated_pack -v`
Expected: FAIL because `run_local_food_pipeline` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def run_local_food_pipeline(request):
    brief = build_local_food_strategy_brief(request)
    content_plan = build_local_food_content_plan(brief)
    visual_suggestions = suggest_local_food_visual_assets(brief)
    generated_pack = generate_local_food_content_pack(request, brief, content_plan)
    generated_pack.visual_card_suggestions = visual_suggestions
    return {
        "strategy_brief": brief,
        "content_plan": content_plan,
        "generated_pack": generated_pack,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_local_food_copywriter.py::test_run_local_food_pipeline_returns_brief_and_generated_pack -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add interior_content_skill/core/orchestrator.py tests/core/test_local_food_copywriter.py
git commit -m "feat: wire local food pipeline through orchestrator"
```

### Task 8: Expose the new request and response shape in the API

**Files:**
- Modify: `interior_content_skill/server/main.py`
- Test: `tests/server/test_local_food_generate_api.py`

**Interfaces:**
- Consumes: `run_local_food_pipeline()`
- Produces:
  - `POST /api/generate-local-food`
  - SSE events: `task_identified`, `template_matched`, `content_generated`, `done`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from interior_content_skill.server.main import app


def test_generate_local_food_api_returns_strategy_and_generated_pack():
    client = TestClient(app)
    payload = {
        "product_name": "贵州刺梨果干",
        "product_category": "果干",
        "origin_place": "贵州",
        "target_audience": "年轻游客",
        "primary_goal": "种草引流",
        "secondary_goal": "地方故事增强",
        "target_platforms": ["xiaohongshu", "douyin", "moments"],
        "selling_scene": "游客伴手礼",
        "user_note": "想做成游客愿意带走的内容",
        "image_paths": ["product.jpg", "package.jpg", "origin.jpg"],
    }
    response = client.post("/api/generate-local-food", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["strategy_brief"]["chosen_template"] == "difference_seed"
    assert data["generated_pack"]["hero_title"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/server/test_local_food_generate_api.py -v`
Expected: FAIL with 404 or route-not-found.

- [ ] **Step 3: Write minimal implementation**

```python
@app.post("/api/generate-local-food")
def generate_local_food(request: LocalFoodRequest):
    result = run_local_food_pipeline(request)
    return {
        "strategy_brief": result["strategy_brief"].model_dump(),
        "content_plan": result["content_plan"],
        "generated_pack": result["generated_pack"].model_dump(),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/server/test_local_food_generate_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add interior_content_skill/server/main.py tests/server/test_local_food_generate_api.py
git commit -m "feat: add local food generate api"
```

### Task 9: Update the web demo for local-food input and explainable output

**Files:**
- Modify: `interior_content_skill/web/src/App.*`
- Modify: `interior_content_skill/web/src/components/*` (exact paths after inspection)
- Test: manual smoke test documented in README (frontend unit tests optional if absent in project)

**Interfaces:**
- Consumes: `POST /api/generate-local-food`
- Produces:
  - Local-food form fields
  - Strategy identification panel
  - Template matched panel
  - Multi-platform content tabs

- [ ] **Step 1: Write the failing test**

```text
Manual expectation checklist:
1. Form shows product_name, product_category, origin_place, target_audience, selling_scene, user_note, image upload.
2. Submit sends payload to /api/generate-local-food.
3. Result page shows 主传播任务 / 次传播任务 / 命中模板 / 推荐表达重点.
4. Result page shows 小红书 / 抖音 / 朋友圈 / 故事增强 results.
```

- [ ] **Step 2: Run app and verify current UI fails the checklist**

Run:
```bash
cd interior_content_skill/web
./node_modules/.bin/vite
```
Expected: Current UI still shows house-layout inputs and cannot submit local-food payload.

- [ ] **Step 3: Write minimal implementation**

```tsx
// Replace house-layout oriented form state with:
const initialForm = {
  product_name: "",
  product_category: "果干",
  origin_place: "贵州",
  target_audience: "年轻游客",
  primary_goal: "种草引流",
  secondary_goal: "地方故事增强",
  target_platforms: ["xiaohongshu", "douyin", "moments"],
  selling_scene: "游客伴手礼",
  user_note: "",
  image_paths: [],
};

// On submit POST to /api/generate-local-food and render:
// strategy_brief.chosen_template
// strategy_brief.supporting_template
// strategy_brief.key_points
// generated_pack.xiaohongshu_post / douyin_script / moments_copy / story_enhancement
```

- [ ] **Step 4: Run app and verify the checklist passes**

Run:
```bash
cd interior_content_skill/web
./node_modules/.bin/vite
```
Expected: Form and result structure align with local-food content generation.

- [ ] **Step 5: Commit**

```bash
git add interior_content_skill/web/src
git commit -m "feat: adapt web demo for local food content strategy"
```

### Task 10: Update docs and add validation guidance

**Files:**
- Modify: `README.md`
- Modify: `interior_content_skill/README.md`
- Optionally modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- Consumes: completed pipeline behavior
- Produces:
  - Updated product description
  - Updated demo instructions
  - Updated evaluation guidance for A/B comparison

- [ ] **Step 1: Write the failing doc checklist**

```text
README must explain:
1. Product is now 乡土代言人 for local food merchants.
2. v1 focus is 种草引流优先 + 地方故事增强.
3. Demo flow uses 贵州刺梨果干 example.
4. Route /api/generate-local-food and expected outputs.
5. A/B comparison guidance against raw writing.
```

- [ ] **Step 2: Verify the current docs fail the checklist**

Run: inspect README sections manually.
Expected: Current docs still describe home-interior generation and house-layout inputs.

- [ ] **Step 3: Write minimal documentation updates**

```markdown
## 项目简介
乡土代言人是一个面向地方食品特产商家的 AI 内容策略助理。

## 第一版聚焦
- 食品类特产
- 种草引流优先
- 地方故事增强

## Demo 示例
推荐使用“贵州刺梨果干 / 游客伴手礼”作为主案例。

## 验证方式
将系统输出与商家原始裸写、普通大模型裸写做结构与地方性对比。
```

- [ ] **Step 4: Verify the doc checklist passes**

Run: manually re-read modified docs.
Expected: All five checklist items present.

- [ ] **Step 5: Commit**

```bash
git add README.md interior_content_skill/README.md docs/ARCHITECTURE.md
git commit -m "docs: update project docs for xiangtu dayanyanren"
```

## Self-Review

### Spec coverage
- 用户定位、主目标、模板库、可解释展示、多平台内容包、技术边界、demo 流程，均已映射到任务 1–10。
- 语音转写、平台发布、复杂视频生成、多租户被明确排除，未进入任务，符合 spec。

### Placeholder scan
- 没有 `TODO` / `TBD` / “实现细节略”。
- 手工测试任务使用明确 checklist，避免“写点测试”式空话。

### Type consistency
- `LocalFoodRequest`, `ContentStrategyBrief`, `GeneratedContentPack` 在任务中前后一致。
- 模板名统一为 `difference_seed`, `gift_scene`, `local_story_seed`, `story_boost`。

---
