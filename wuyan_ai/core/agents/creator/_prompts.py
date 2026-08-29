"""Creator prompt templates driven by the selected DNA fragments."""

from __future__ import annotations

_TYPE_LABELS = {
    "scene": "场景",
    "valuePromise": "价值承诺",
    "hook": "开头钩子",
    "structure": "内容结构",
    "tone": "表达语气",
    "visualStyle": "视觉风格",
}

SYSTEM_PROMPT = """你是一位小红书地方食品内容创作专家。

你会收到一组已经选好的细粒度 DNA 片段。请把它们组合成一篇自然、具体、可信的小红书笔记：
1. scene 决定内容场景，valuePromise 决定用户能得到什么
2. hook 决定开头吸引力，structure 决定正文推进顺序
3. tone 决定说话方式，visualStyle 决定配图顺序和画面

不要逐条解释 DNA，也不要写成模板说明；直接把策略融入内容。

写作要求：
- 标题：15-25字，带 emoji，有钩子感或数字/反差感
- 正文：300-600字，分段清晰，多用 emoji 点缀，口语化不生硬
- 标签：5-8个，包含品类词、场景词、地域词
- 整体有真诚分享感，不要硬广，不要虚构产品事实
"""


def build_user_prompt(
    brief: dict,
    fragments: list[dict],
) -> str:
    """Build the creator prompt from the six selected fragment definitions."""
    fragment_lines = []
    for fragment in fragments:
        label = _TYPE_LABELS.get(fragment.get("type", ""), fragment.get("type", "DNA"))
        fragment_lines.append(
            f"- {label}（{fragment.get('type', '')}）: {fragment.get('value', '')}"
        )
    dna_text = "\n".join(fragment_lines) or "（没有选中的 DNA 片段，请使用通用但具体的地方特产写法）"

    selling_points_text = "\n".join(
        f"  - {point}" for point in brief.get("key_selling_points", [])
    ) or "  - 结合产品信息提炼真实卖点"
    avoid_text = "\n".join(
        f"  - {point}" for point in brief.get("avoid_points", [])
    ) or "  - 避免夸大宣传和空泛形容"

    image_summaries = brief.get("image_summaries", [])
    if image_summaries:
        image_text = f"用户上传了 {len(image_summaries)} 张图片，摘要如下：\n"
        image_text += "\n".join(
            f"  第{i + 1}张：{summary}"
            for i, summary in enumerate(image_summaries)
        )
    else:
        image_text = "用户没有上传图片，请根据 visualStyle 和卖点建议应该拍什么。"

    return f"""## 产品信息
- 产品名称：{brief.get('product_name', '')}
- 产品品类：{brief.get('product_category', '')}
- 产地：{brief.get('origin_place', '')}
- 目标客群：{brief.get('target_audience', '')}
- 售卖场景：{brief.get('selling_scene', '不限')}
{f"- 用户补充：{brief.get('user_note', '')}" if brief.get('user_note') else ''}

## 本次选中的细粒度 DNA
{dna_text}

## 核心卖点（必须融入内容）
{selling_points_text}

## 避坑提醒（注意避免）
{avoid_text}

## 图片情况
{image_text}

## 输出要求
请严格输出 JSON，不要任何额外说明文字：
{{
  "title": "小红书笔记标题（带 emoji，15-25字）",
  "content": "笔记正文（300-600字，分段，带 emoji，口语化）",
  "hashtags": ["标签1", "标签2", "标签3"],
  "image_suggestions": [
    {{"index": 1, "content": "一句话说明这张图建议拍什么"}},
    {{"index": 2, "content": "一句话说明这张图建议拍什么"}}
  ]
}}

注意：image_suggestions 输出 3-6 条；标签输出 5-8 个；不得编造用户没有提供的功效、价格或资质。
"""
