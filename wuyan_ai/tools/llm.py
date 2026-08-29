"""
统一 LLM 调用层（Anthropic 兼容协议 / 豆包 doubao-seed-2-1-turbo-260628）

全队共用：analyzer / prompter / copywriter 等 Agent 通过此模块调 LLM，
避免每个 Agent 自建 client / 各自维护 retry & auth。

约定：
- chat()              纯文本对话
- chat_with_images()  多模态：user 同时含 text + base64 图片
- 内置 3 次重试 + 指数退避，调用方无需额外处理重试

配置从项目根目录 .env 文件读取，环境变量：LLM_MODEL / LLM_BASE_URL / LLM_API_KEY 等。
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv

# 从项目根目录的 .env 文件加载配置（tools/ 在包内，往上两级是项目根）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

# ---- 配置（从环境变量读取） ----
LLM_MODEL = os.getenv("LLM_MODEL", "doubao-seed-2-1-turbo-260628")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/compatible/v1/messages")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
DEFAULT_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
DEFAULT_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120"))

# ---- HTTP 客户端单例（复用连接池） ----
_client: httpx.AsyncClient | None = None


def _get_client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    """惰性单例：全局复用 httpx.AsyncClient 连接池，避免每次调用重建 TCP/TLS。"""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=timeout, trust_env=False)
    return _client


# ---------------------------------------------------------------
# 对外 API
# ---------------------------------------------------------------

async def chat(
    *,
    system: str | None = None,
    user: str,
    model: str = LLM_MODEL,
    temperature: float = 0.7,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """纯文本对话，返回 assistant 的文本回复。"""
    messages = [{"role": "user", "content": user}]
    return await _call_anthropic(
        messages=messages,
        system=system,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


async def chat_with_images(
    *,
    system: str | None = None,
    user_text: str,
    image_urls: list[str],
    model: str = LLM_MODEL,
    temperature: float = 0.7,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """
    多模态对话。image_urls 元素支持：
    - http(s):// 开头的网络图片 URL
    - data:image/...;base64,... 格式的 base64 data URI
    """
    content: list[dict] = [{"type": "text", "text": user_text}]
    for url in image_urls:
        content.append(_build_image_block(url))

    messages = [{"role": "user", "content": content}]
    return await _call_anthropic(
        messages=messages,
        system=system,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


# ---------------------------------------------------------------
# Anthropic 兼容协议实现
# ---------------------------------------------------------------

async def _call_anthropic(
    *,
    messages: list[dict],
    system: str | None,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> str:
    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        payload["system"] = system

    client = _get_client(timeout=timeout)

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = await client.post(
                LLM_BASE_URL,
                headers={
                    "x-api-key": LLM_API_KEY,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            # Anthropic 格式：content[0].text
            content_blocks = data.get("content", [])
            if content_blocks and isinstance(content_blocks, list):
                return content_blocks[0].get("text", "")
            # 兼容部分平台返回 text 字段
            if isinstance(data.get("content"), str):
                return data["content"]

            logger.error("无法解析 LLM 响应格式: %s", data)
            raise ValueError("LLM 响应格式异常")

        except httpx.HTTPStatusError as e:
            # 429 / 5xx：指数退避重试
            if attempt < MAX_RETRIES and e.response.status_code in (429, 500, 502, 503, 504):
                retry_after = e.response.headers.get("retry-after")
                delay = (
                    float(retry_after)
                    if retry_after and _is_float(retry_after)
                    else (2.0 * (2 ** attempt))
                )
                delay = min(delay, 30.0)
                logger.warning(
                    "LLM HTTP %s 错误，第 %d 次重试（等待 %.1fs）",
                    e.response.status_code, attempt + 1, delay,
                )
                await asyncio.sleep(delay)
                continue
            logger.error("LLM 调用失败（HTTP %s）: %s", e.response.status_code, e.response.text)
            raise

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            if attempt < MAX_RETRIES:
                delay = min(2.0 * (2 ** attempt), 30.0)
                logger.warning("LLM 网络错误，第 %d 次重试: %s", attempt + 1, e)
                await asyncio.sleep(delay)
                continue
            logger.error("LLM 网络调用最终失败: %s", e)
            raise


# ---------------------------------------------------------------
# 通用工具：LLM 响应 JSON 解析
# ---------------------------------------------------------------

def extract_json_from_llm_response(text: str) -> dict:
    """从LLM响应文本中提取JSON。

    支持：
    - 纯JSON字符串
    - ```json ... ``` 代码块包裹
    - ``` ... ``` 无语言标识的代码块

    自动清洗LLM常见的JSON问题：控制字符、首尾多余文字等。
    """
    json_str = text.strip()

    # 提取 markdown 代码块
    if "```" in json_str:
        lines = json_str.split("\n")
        json_lines = []
        in_code = False
        for line in lines:
            if line.startswith("```"):
                if in_code:
                    break  # 遇到结束标记，停止
                in_code = True
                continue
            if in_code:
                json_lines.append(line)
        if json_lines:
            json_str = "\n".join(json_lines).strip()

    if not json_str:
        raise ValueError("LLM响应中未找到JSON内容")

    # 清洗控制字符（LLM有时会在字符串里混入原始控制字符导致json.loads失败）
    # 先清洗绝对非法的控制字符（< 0x20 且不是 \t \n \r）
    json_str = _sanitize_control_chars(json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 如果还是失败，用 strict=False 再试一次（允许字符串内的控制字符）
        try:
            return json.loads(json_str, strict=False)
        except json.JSONDecodeError:
            # 最后尝试：从文本中提取第一个完整的JSON对象
            return _extract_first_json_object(json_str)


def _sanitize_control_chars(s: str) -> str:
    """移除JSON字符串中绝对非法的控制字符（保留\\t\\n\\r）。"""
    result = []
    for ch in s:
        code = ord(ch)
        if code < 0x20 and code not in (0x09, 0x0A, 0x0D):
            continue
        result.append(ch)
    return "".join(result)


def _extract_first_json_object(s: str) -> dict:
    """从脏文本中提取第一个完整的JSON对象（通过括号匹配）。"""
    start = s.find("{")
    if start == -1:
        raise ValueError("未找到JSON对象")

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(s)):
        ch = s[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                json_str = s[start:i+1]
                return json.loads(json_str, strict=False)

    raise ValueError("JSON对象不完整")


def normalize_list_field(val, max_len: int | None = None, transform=None) -> list[str]:
    """规范化列表字段：确保是列表 + 过滤空值 + strip + 可选截断 + 可选转换。"""
    if not isinstance(val, list):
        return []
    result = []
    for item in val:
        if item is None:
            continue
        s = str(item).strip()
        if not s:
            continue
        if transform:
            s = transform(s)
        result.append(s)
    if max_len is not None:
        result = result[:max_len]
    return result


# ---------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------

_DATA_URI_RE = re.compile(r"^data:image/(\w+);base64,(.+)$", re.IGNORECASE)


def _build_image_block(image_source: str) -> dict:
    """将 http URL 或 data URI 转为 Anthropic 格式的 image content block。"""
    # data:URI 格式
    m = _DATA_URI_RE.match(image_source)
    if m:
        media_type = f"image/{m.group(1).lower()}"
        b64_data = m.group(2)
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64_data,
            },
        }

    # http URL：Anthropic 不直接支持 URL，这里先返回 URL 格式（兼容部分中转平台）
    # 如需严格 Anthropic 格式，调用方应先下载图片再转 base64
    return {
        "type": "image",
        "source": {
            "type": "url",
            "url": image_source,
        },
    }


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False
