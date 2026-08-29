"""FastAPI server: 乡礼 Spark 地方特产小红书笔记生成。

启动方式：
    uvicorn wuyan_ai.server.main:app --reload --port 8000

主要接口：
    POST /api/generate       — 主生成接口（SSE 流式进度推送）
    POST /api/generate/sync  — 同步生成接口（返回 JSON，方便调试）
    GET  /api/health         — 健康检查
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# 项目根（server/main.py → 上两级是 wuyan_ai 包 → 上三级是项目根）
SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

from ..core.orchestrator import run_pipeline, run_pipeline_sse
from ..core.schemas import LocalFoodRequest

logger = logging.getLogger(__name__)

app = FastAPI(title="乡礼 Spark API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传图片临时目录
UPLOAD_DIR = Path(tempfile.gettempdir()) / "wuyan_ai_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_IMAGES = 3


# ============================================================
# 工具函数
# ============================================================

def _parse_optional(value: str | None) -> str | None:
    """表单可选字段：空字符串转 None。"""
    if value is None:
        return None
    s = value.strip()
    return s if s else None


async def _save_uploaded_images(images: list[UploadFile] | None) -> list[str]:
    """保存上传的图片到临时目录，返回本地路径列表。"""
    if not images:
        return []

    paths: list[str] = []
    for img in images[:MAX_IMAGES]:
        if not img.filename:
            continue
        # 生成唯一文件名，避免冲突
        ext = Path(img.filename).suffix or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        save_path = UPLOAD_DIR / unique_name

        content = await img.read()
        save_path.write_bytes(content)
        paths.append(str(save_path))

    return paths


def _build_request(
    product_name: str,
    product_category: str,
    origin_place: str,
    target_audience: str,
    selling_scene: str | None,
    user_note: str | None,
    image_paths: list[str],
) -> LocalFoodRequest:
    """从表单字段构造 LocalFoodRequest。"""
    return LocalFoodRequest(
        product_name=product_name.strip(),
        product_category=product_category.strip(),
        origin_place=origin_place.strip(),
        target_audience=target_audience.strip(),
        selling_scene=_parse_optional(selling_scene),
        user_note=_parse_optional(user_note),
        image_paths=image_paths,
    )


# ============================================================
# SSE 主接口
# ============================================================

@app.post("/api/generate")
async def generate_stream(
    product_name: str = Form(...),
    product_category: str = Form(...),
    origin_place: str = Form(...),
    target_audience: str = Form(...),
    selling_scene: str | None = Form(None),
    user_note: str | None = Form(None),
    images: list[UploadFile] | None = File(None),
):
    """生成小红书笔记（SSE 流式推送进度）。

    - 输入：multipart/form-data，文字字段 + 最多3张图片
    - 输出：text/event-stream 流式事件
      - progress 事件：step / status / message / 中间数据
      - result 事件：最终生成结果
    """
    image_paths = await _save_uploaded_images(images)
    request = _build_request(
        product_name, product_category, origin_place,
        target_audience, selling_scene, user_note, image_paths,
    )

    async def event_stream():
        try:
            async for event in run_pipeline_sse(request):
                # SSE 格式：event: xxx\ndata: xxx\n\n
                event_type = event.get("event", "message")
                data = event.get("data", {})
                import json
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except Exception as e:
            import json
            logger.error("生成失败: %s", e)
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# 同步接口（调试用）
# ============================================================

@app.post("/api/generate/sync")
async def generate_sync(
    product_name: str = Form(...),
    product_category: str = Form(...),
    origin_place: str = Form(...),
    target_audience: str = Form(...),
    selling_scene: str | None = Form(None),
    user_note: str | None = Form(None),
    images: list[UploadFile] | None = File(None),
):
    """同步生成接口（返回完整 JSON，方便调试和脚本调用）。"""
    image_paths = await _save_uploaded_images(images)
    request = _build_request(
        product_name, product_category, origin_place,
        target_audience, selling_scene, user_note, image_paths,
    )
    result = await run_pipeline(request)
    return result.model_dump(mode="json")


# ============================================================
# 健康检查
# ============================================================

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "wuyan-ai",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
