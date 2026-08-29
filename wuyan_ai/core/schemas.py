"""
接口契约 (Pydantic Schemas) — 乡礼 Spark v1

所有 Agent / 模块之间的数据传递必须使用这里定义的类型。
v1仅聚焦小红书单平台特产笔记生成。

数据流（两Agent架构）：
    LocalFoodRequest
        → analyzer 多模态策略分析  → DnaStrategyBrief（DNA匹配+卖点+图片摘要）
        → creator 纯文本内容生成   → XiaohongshuPost + list[ImageSuggestion]
        → orchestrator 编排       → GenerateResult
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ============================================================
# 共享常量
# ============================================================

# 笔记配图序数标签（最多9张，足够覆盖小红书单条笔记上限）
IMAGE_SUGGESTION_LABELS: list[str] = [
    "第1张", "第2张", "第3张", "第4张", "第5张",
    "第6张", "第7张", "第8张", "第9张",
]
MAX_IMAGE_SUGGESTIONS = 9

# DNA角色
DnaRole = Literal["primary", "supporting"]


# ============================================================
# 用户输入（前端 → 后端入口）
# ============================================================
class LocalFoodRequest(BaseModel):
    """用户输入：6个字段 + 可选图片。"""
    product_name: str = Field(..., description="产品名称，如'贵州刺梨果干'")
    product_category: str = Field(..., description="产品品类，如'果干'")
    origin_place: str = Field(..., description="产地，如'贵州贵阳'")
    target_audience: str = Field(..., description="目标客群，如'来贵州旅游的年轻女生'")
    selling_scene: Optional[str] = Field(None, description="售卖场景，如'游客伴手礼'")
    user_note: Optional[str] = Field(None, description="用户补充备注/卖点")
    image_paths: list[str] = Field(default_factory=list, description="本地图片路径列表（最多6张）")


# ============================================================
# DNA匹配结果
# ============================================================
class DnaMatch(BaseModel):
    """单个DNA匹配结果。"""
    dna_id: str = Field(..., description="DNA ID，如'gift_guide'")
    dna_name: str = Field(..., description="DNA显示名称，如'送礼实用攻略风'")
    role: DnaRole = Field(..., description="primary=主DNA，supporting=辅助DNA")
    weight: float = Field(..., description="融合权重，0-1，所有DNA权重和为1.0")
    reason: str = Field("", description="匹配理由，用于路演模式展示")


# ============================================================
# 策略简报（analyzer输出 → 下游所有Agent的输入）
# ============================================================
class DnaStrategyBrief(BaseModel):
    """传播策略简报：DNA匹配结果 + 核心卖点 + 避坑点 + 视觉建议。"""
    product_name: str
    product_category: str
    origin_place: str
    target_audience: str
    selling_scene: Optional[str] = None
    user_note: Optional[str] = None

    # DNA匹配结果（主1 + 辅2，权重和=1.0）
    dna_matches: list[DnaMatch] = Field(default_factory=list)

    # 核心卖点（3-5条）
    key_selling_points: list[str] = Field(default_factory=list)

    # 避坑点（2-3条）
    avoid_points: list[str] = Field(default_factory=list)

    # 用户上传图片的内容摘要（analyzer多模态识别产出，creator用）
    image_summaries: list[str] = Field(default_factory=list, description="每张图片的内容摘要，按上传顺序")

    # 建议的视觉卡片内容方向（3-6个，给creator参考，具体数量由AI判断）
    suggested_visual_directions: list[str] = Field(default_factory=list)


# ============================================================
# 笔记配图建议（creator输出）
# ============================================================
class ImageSuggestion(BaseModel):
    """单张笔记配图建议。"""
    index: int = Field(..., ge=1, description="第几张图，从1开始")
    content: str = Field(..., description="配图内容建议，一句话说明拍什么")


# ============================================================
# 小红书笔记（copywriter输出）
# ============================================================
class XiaohongshuPost(BaseModel):
    """完整的小红书笔记。"""
    title: str = Field(..., description="笔记标题")
    content: str = Field(..., description="笔记正文（含emoji和换行）")
    hashtags: list[str] = Field(default_factory=list, description="话题标签列表")


# ============================================================
# 最终结果（orchestrator输出 → 前端展示）
# ============================================================
class GenerateResult(BaseModel):
    """生成结果：小红书笔记 + 视觉建议 + DNA匹配信息（路演模式用）。"""
    post: XiaohongshuPost
    image_suggestions: list[ImageSuggestion] = Field(default_factory=list)
    dna_matches: list[DnaMatch] = Field(default_factory=list, description="DNA匹配结果，路演模式展示")
    key_selling_points: list[str] = Field(default_factory=list, description="核心卖点，路演模式展示")
