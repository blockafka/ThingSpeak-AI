"""Analyzer Agent · LLM Prompt 模板（多模态版本）"""

SYSTEM_PROMPT = """你是小红书爆款内容策略分析师，专门帮助地方特产商家匹配最优的爆款DNA写作风格。

你可以看到用户上传的产品图片和文字信息。你的任务：
1. 先仔细观察每张图片，描述每张图的核心内容（产品、包装、场景、质感等）
2. 从候选DNA中选出最适合这款产品的3个DNA（1个主DNA + 2个辅助DNA）
3. 为每个DNA分配融合权重（所有权重之和 = 1.0）
4. 提炼3-5条核心卖点
5. 列出2-3条避坑提醒
6. 根据产品特点自主判断，给出3-6条视觉卡片内容方向建议

选择DNA的判断标准：
- 主DNA：最匹配产品+客群+场景的核心风格（权重 0.5-0.7）
- 辅助DNA1：补充维度，增强内容丰富度（权重 0.15-0.25）
- 辅助DNA2：差异化角度，增加内容层次（权重 0.1-0.2）

输出必须是严格的JSON格式，不要任何额外说明文字。
"""


def build_user_prompt(
    product_info: dict,
    candidate_dnas: list[dict],
    has_images: bool,
) -> str:
    """构建用户prompt：产品信息 + 候选DNA列表 + 图片说明。"""
    dna_list_text = "\n".join(
        f"- [{dna['id']}] {dna['name']}\n"
        f"  描述：{dna.get('description', '')}\n"
        f"  风格：{', '.join(dna.get('tone', []))}\n"
        f"  关键词：{', '.join(dna.get('matching_keywords', []))}"
        for dna in candidate_dnas
    )

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

    if has_images:
        image_note = "用户上传了产品图片，你可以在多模态输入中看到它们。请仔细观察每张图片的内容、质感、包装、场景等信息，将图片信息融入你的分析。\n"
    else:
        image_note = "用户没有上传图片，请仅根据文字信息进行分析。\n"

    return f"""## 产品信息
{product_text}
## 图片情况
{image_note}
## 候选DNA列表（共{len(candidate_dnas)}个）
{dna_list_text}

## 输出要求
请严格输出JSON，格式如下：
```json
{{
  "image_summaries": [
    "第1张图的内容摘要（一句话，说清图里是什么）",
    "第2张图的内容摘要"
  ],
  "dna_matches": [
    {{
      "dna_id": "主DNA的id",
      "role": "primary",
      "weight": 0.6,
      "reason": "为什么选这个做主DNA"
    }},
    {{
      "dna_id": "辅助DNA1的id",
      "role": "supporting",
      "weight": 0.25,
      "reason": "为什么选这个做辅助"
    }},
    {{
      "dna_id": "辅助DNA2的id",
      "role": "supporting",
      "weight": 0.15,
      "reason": "为什么选这个做辅助"
    }}
  ],
  "key_selling_points": [
    "卖点1",
    "卖点2",
    "卖点3"
  ],
  "avoid_points": [
    "避坑1",
    "避坑2"
  ],
  "suggested_visual_directions": [
    "第1张图方向",
    "第2张图方向",
    "第3张图方向"
  ]
}}
```

注意：
- image_summaries：按图片顺序，每张一句话摘要。如果没有图片则返回空数组
- dna_id必须从候选列表中选择，不能凭空捏造
- 3个DNA权重之和必须等于1.0
- key_selling_points 3-5条，每条简短有力
- avoid_points 2-3条
- suggested_visual_directions 3-6条，根据产品特点自主决定数量，每条描述一张图应该放什么内容
"""
