"""乡礼 Spark 主编排器（两Agent架构 · B方案）

串联 v1 主流程：
  1. analyzer — 多模态策略分析（看图+文字 → DNA匹配+卖点+图片摘要）
  2. creator  — 纯文本内容生成（策略简报 → 小红书笔记+视觉建议）

B方案：图片只在analyzer阶段看多模态一次，提取文字摘要后传给creator，
creator纯文本生成，省一次多模态调用，链路更清晰。
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from .agents.analyzer import analyze_request
from .agents.creator import create_content
from .schemas import GenerateResult, LocalFoodRequest

logger = logging.getLogger(__name__)


async def run_pipeline(request: LocalFoodRequest) -> GenerateResult:
    """串行运行两Agent主流程（无进度回调版本）。"""
    brief = await analyze_request(request)
    return await create_content(brief)


async def run_pipeline_sse(request: LocalFoodRequest) -> AsyncIterator[dict]:
    """SSE版本：真正的流式推送，每一步进度实时yield。

    事件格式：
        {"event": "progress", "data": {"step": "...", "status": "...", ...}}
        {"event": "result", "data": {...}}
    """
    # Step 1: 策略分析
    yield {
        "event": "progress",
        "data": {
            "step": "analyzing",
            "status": "start",
            "message": "正在分析产品，匹配爆款DNA...",
        },
    }
    brief = await analyze_request(request)
    yield {
        "event": "progress",
        "data": {
            "step": "analyzing",
            "status": "done",
            "dna_matches": [m.model_dump() for m in brief.dna_matches],
            "key_selling_points": brief.key_selling_points,
            "image_summaries": brief.image_summaries,
        },
    }

    # Step 2: 内容创作
    yield {
        "event": "progress",
        "data": {
            "step": "creating",
            "status": "start",
            "message": "正在生成小红书笔记...",
        },
    }
    result = await create_content(brief)
    yield {
        "event": "progress",
        "data": {
            "step": "creating",
            "status": "done",
        },
    }

    # 完成
    yield {
        "event": "progress",
        "data": {
            "step": "completed",
            "status": "done",
            "message": "生成完成！",
        },
    }

    # 最终结果
    yield {"event": "result", "data": result.model_dump()}
