"""Analyzer prompt templates for per-dimension DNA selection."""

from __future__ import annotations

from ...dnas import FRAGMENT_TYPES

SYSTEM_PROMPT = """你是小红书内容策略分析师，专门为地方食品商家选择可组合的细粒度 DNA 片段。

你的任务：
1. 结合产品文字和图片，理解产品、客群和使用场景
2. 从每个维度的候选池中恰好选择 1 个 DNA 片段
3. 为每个选择写一句简短理由
4. 提炼 3-5 条核心卖点、2-3 条避坑提醒和 3-6 条视觉方向

必须覆盖这 6 个维度：scene、valuePromise、hook、structure、tone、visualStyle。
只能选择候选池中已有的 fragmentId，不要创造新的 ID。
输出必须是严格 JSON，不要添加任何额外说明文字。
"""


def build_user_prompt(
    product_info: dict,
    candidate_pools: dict[str, list[dict]],
    has_images: bool,
) -> str:
    """Build one compact prompt containing six Top-10 candidate pools."""
    product_text = (
        f"产品名称：{product_info.get('product_name', '')}\n"
        f"产品品类：{product_info.get('product_category', '')}\n"
        f"产地：{product_info.get('origin_place', '')}\n"
        f"目标客群：{product_info.get('target_audience', '')}\n"
    )
    if product_info.get("selling_scene"):
        product_text += f"售卖场景：{product_info['selling_scene']}\n"
    if product_info.get("user_note"):
        product_text += f"用户补充：{product_info['user_note']}\n"

    image_note = (
        "用户上传了产品图片，请观察产品、包装、环境和质感。"
        if has_images
        else "用户没有上传图片，请仅根据文字信息分析。"
    )

    pool_parts: list[str] = []
    for fragment_type in FRAGMENT_TYPES:
        lines = [f"### {fragment_type} 候选（按 score 降序）"]
        for fragment in candidate_pools.get(fragment_type, []):
            lines.append(
                f"- {fragment['fragmentId']} | {fragment['value']}"
                f" | score={fragment['score']:.2f} | state={fragment['state']}"
            )
        pool_parts.append("\n".join(lines))

    return f"""## 产品信息
{product_text}
## 图片情况
{image_note}

## 六个维度的候选 DNA（每个维度取一个）
{chr(10).join(pool_parts)}

## 输出要求
请严格输出 JSON，格式如下：
{{
  "selectedFragments": [
    {{"type": "scene", "fragmentId": "scene_001", "reason": "选择理由"}},
    {{"type": "valuePromise", "fragmentId": "valuePromise_001", "reason": "选择理由"}},
    {{"type": "hook", "fragmentId": "hook_001", "reason": "选择理由"}},
    {{"type": "structure", "fragmentId": "structure_001", "reason": "选择理由"}},
    {{"type": "tone", "fragmentId": "tone_001", "reason": "选择理由"}},
    {{"type": "visualStyle", "fragmentId": "visualStyle_001", "reason": "选择理由"}}
  ],
  "image_summaries": [],
  "key_selling_points": ["卖点1", "卖点2", "卖点3"],
  "avoid_points": ["避坑1", "避坑2"],
  "suggested_visual_directions": ["第1张图应该拍什么", "第2张图应该拍什么"]
}}

注意：
- selectedFragments 必须恰好 6 条，每个 type 恰好出现一次
- fragmentId 必须来自对应维度候选池
- 不要返回 score、value、version，这些由系统根据 ID 补全
- 没有图片时 image_summaries 必须为空数组
"""
