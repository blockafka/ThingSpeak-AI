"""Creator Agent · LLM Prompt 模板（纯文本版本）

creator 是纯文本Agent，不直接看图片。
图片信息由analyzer提取为文字摘要，放在brief.image_summaries中。
"""

SYSTEM_PROMPT = """你是一位小红书爆款内容创作专家，专门为地方食品特产撰写种草笔记。

你擅长将多种爆款DNA风格融合进内容创作，让笔记既有地方特色又有传播力。

你的任务：
1. 根据策略简报中的DNA匹配结果，融合多种风格写出一篇吸引人的小红书笔记
2. 根据产品特点自主决定配图数量（3-6张），为每张图用一句话说明建议拍什么
3. 如果用户上传了图片，根据图片摘要来安排排序
4. 如果用户没传图片，根据DNA风格建议应该拍什么图

写作要求：
- 标题：15-25字，带emoji，有钩子感或数字/反差感
- 正文：300-600字，分段清晰，多用emoji点缀，口语化不生硬
- 标签：5-8个，包含品类词、场景词、地域词
- 整体要有真诚分享感，不要硬广
"""


def build_user_prompt(
    brief: dict,
    dna_defs: list[dict],
) -> str:
    """构建用户prompt：策略简报 + DNA详情 + 图片摘要。"""

    # DNA信息
    dna_text_parts = []
    for i, dna in enumerate(dna_defs):
        match_info = brief["dna_matches"][i] if i < len(brief.get("dna_matches", [])) else {}
        weight = match_info.get("weight", 0)
        role = match_info.get("role", "supporting")
        role_label = "主DNA" if role == "primary" else f"辅助DNA{i}"
        dna_text_parts.append(
            f"【{role_label} · 权重{weight}】{dna.get('name', '')}（{dna.get('id', '')}）\n"
            f"  描述：{dna.get('description', '')}\n"
            f"  风格调性：{', '.join(dna.get('tone', []))}\n"
            f"  内容结构：{' → '.join(dna.get('structure', []))}\n"
            f"  钩子模板（参考）：\n"
            + "\n".join(f"    - {p}" for p in dna.get("hook_patterns", [])[:3])
            + f"\n  视觉风格：{', '.join(dna.get('visual_style', []))}\n"
            f"  标签风格：{dna.get('hashtags_style', '')}"
        )
    dna_text = "\n\n".join(dna_text_parts)

    # 卖点
    selling_points_text = "\n".join(f"  - {p}" for p in brief.get("key_selling_points", []))

    # 避坑
    avoid_text = "\n".join(f"  - {p}" for p in brief.get("avoid_points", []))

    # 图片摘要
    image_summaries = brief.get("image_summaries", [])
    if image_summaries:
        image_text = f"用户上传了 {len(image_summaries)} 张图片，内容摘要如下：\n"
        for i, summary in enumerate(image_summaries):
            image_text += f"  第{i+1}张：{summary}\n"
    else:
        image_text = "用户没有上传图片，请根据DNA风格和卖点自主决定3-6张图应该拍什么内容。\n"

    return f"""## 产品信息
- 产品名称：{brief.get('product_name', '')}
- 产品品类：{brief.get('product_category', '')}
- 产地：{brief.get('origin_place', '')}
- 目标客群：{brief.get('target_audience', '')}
- 售卖场景：{brief.get('selling_scene', '不限')}
{f'- 用户补充：{brief.get("user_note", "")}' if brief.get('user_note') else ''}

## 爆款DNA融合方案
{dna_text}

## 核心卖点（必须融入内容）
{selling_points_text}

## 避坑提醒（注意避免）
{avoid_text}

## 图片情况
{image_text}
## 输出要求
请严格输出JSON格式，不要任何额外说明文字，格式如下：
```json
{{
  "title": "小红书笔记标题（带emoji，15-25字）",
  "content": "笔记正文（300-600字，分段，带emoji，口语化）",
  "hashtags": [
    "标签1",
    "标签2",
    "标签3"
  ],
  "image_suggestions": [
    {{
      "index": 1,
      "content": "一句话说明这张图建议拍什么"
    }},
    {{
      "index": 2,
      "content": "..."
    }}
  ]
}}
```

注意：
- image_suggestions 输出3-6条（index从1开始），根据产品特点自主决定配图数量，不用强行凑满6张
- 如果有上传图片，根据图片摘要来安排排序
- 如果没上传图片，根据DNA风格和卖点来建议应该拍什么图
- content用一句话说明这张图建议拍什么，简洁具体
- 标签5-8个，包含地域+品类+场景+风格词
"""
