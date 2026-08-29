"""
文生图 API 封装 · 乡礼 Spark

v1阶段定位：**预留接口，不进入主链路**。
乡礼 Spark v1 的图片策略是「用户传图 + LLM排序+图注」，
不依赖AI生图。本模块保留完整接口结构，v2阶段接入生图模型时可直接复用。

通过环境变量 IMAGE_GEN_PROVIDER 切换：
    mock / openai_image
默认 mock，返回占位图 URL，保证代码无断链。

提供：
- text_to_image(prompt, negative_prompt, aspect_ratio) → str
    返回前端可直接 <img src> 的 URL 或本地路径。
    openai_image: 落盘到 <package_root>/data/generated/{uuid}.png，
                  返回 /static/generated/{uuid}.png
"""

from __future__ import annotations

import base64
import logging
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# 包根目录（data/generated 在包内自包含）
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
GENERATED_DIR = PACKAGE_ROOT / "data" / "generated"
HTTP_PREFIX = "/static/generated"

# 占位图URL（v1阶段生图为mock模式，返回占位图）
PLACEHOLDER_IMAGE_URL = "https://placehold.co/1024x1792/f8f8f8/666666?text=Coming+Soon"


# ---------------------------------------------------------------
# 对外 API
# ---------------------------------------------------------------
async def text_to_image(
    prompt: str,
    negative_prompt: str = "",
    aspect_ratio: str = "3:4",
) -> str:
    """
    文生图入口。出错或未配置时返回 placeholder URL，不抛异常。
    """
    provider = (os.getenv("IMAGE_GEN_PROVIDER", "mock") or "mock").lower()

    if provider == "openai_image":
        return await _openai_image(prompt, negative_prompt, aspect_ratio)

    if provider != "mock":
        logger.warning("IMAGE_GEN_PROVIDER=%s 尚未实现，降级到 mock", provider)
    return PLACEHOLDER_IMAGE_URL


# ---------------------------------------------------------------
# OpenAI Image 实现（gpt-image-1 via 中转平台）
# ---------------------------------------------------------------

_client = None


def _get_client():
    """惰性单例：复用 AsyncOpenAI client 避免每次调用新建连接。"""
    global _client
    if _client is None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError("openai 包未安装") from exc

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai-next.com/v1").strip()
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return _client


async def _openai_image(
    prompt: str, negative_prompt: str, aspect_ratio: str
) -> str:
    try:
        client = _get_client()
    except ImportError as exc:
        logger.error("openai 包未安装，降级到 placeholder：%s", exc)
        return PLACEHOLDER_IMAGE_URL

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.warning("OPENAI_API_KEY 未配置，降级到 placeholder")
        return PLACEHOLDER_IMAGE_URL

    model = os.getenv("IMAGE_GEN_MODEL", "gpt-image-1")

    # NOTE: OpenAI images API 不原生支持 negative_prompt 参数。
    # 此处通过文本拼接方式注入，对 gpt-image-1 效果有限但聊胜于无。
    # 待后续切换 SD/Flux 时可使用原生 negative_prompt 参数。
    full_prompt = prompt.strip()
    if negative_prompt.strip():
        full_prompt += f"\n\n避免以下问题：{negative_prompt.strip()}"

    size = _aspect_ratio_to_size(aspect_ratio)

    try:
        response = await client.images.generate(
            model=model,
            prompt=full_prompt,
            n=1,
            size=size,
            response_format="b64_json",
        )

        image_data = response.data[0]

        if hasattr(image_data, "b64_json") and image_data.b64_json:
            image_bytes = base64.b64decode(image_data.b64_json)
            GENERATED_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4().hex}.png"
            file_path = GENERATED_DIR / filename
            file_path.write_bytes(image_bytes)
            return f"{HTTP_PREFIX}/{filename}"
        elif hasattr(image_data, "url") and image_data.url:
            return image_data.url
        else:
            logger.warning("OpenAI Image 未返回有效数据，降级到 placeholder")
            return PLACEHOLDER_IMAGE_URL

    except Exception as exc:
        logger.error("OpenAI Image 调用失败，降级到 placeholder：%s", exc)
        return PLACEHOLDER_IMAGE_URL


def _aspect_ratio_to_size(aspect_ratio: str) -> str:
    """映射为 gpt-image-1 支持的标准 size（仅 1024x1024/1024x1792/1792x1024）。"""
    mapping = {
        "3:4": "1024x1792",
        "9:16": "1024x1792",
        "4:3": "1792x1024",
        "16:9": "1792x1024",
        "1:1": "1024x1024",
    }
    return mapping.get(aspect_ratio, "1024x1024")
