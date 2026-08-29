"""
爆款DNA库加载器 · 乡礼 Spark v1

从 data/ 目录下的 JSON 文件加载所有内置DNA。
DNA数据与代码分离，方便运营人员直接修改/新增DNA配置。

6个内置DNA，覆盖95%以上地方特产小红书笔记场景。
融合规则：主DNA 70% + 两个辅助DNA各15%
DNA权重由analyzer Agent计算。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DNA 类型别名
# ---------------------------------------------------------------------------
DnaDefinition = dict[str, Any]

# ---------------------------------------------------------------------------
# 数据目录：data/ 与本文件同级
# ---------------------------------------------------------------------------
_DNA_DATA_DIR = Path(__file__).resolve().parent / "data"

# ---------------------------------------------------------------------------
# 惰性加载缓存（启动时首次访问加载一次，后续直接用内存dict）
# ---------------------------------------------------------------------------
_library: dict[str, DnaDefinition] | None = None


def _load_library() -> dict[str, DnaDefinition]:
    """从 data/*.json 加载所有DNA到内存。"""
    global _library
    if _library is not None:
        return _library

    library: dict[str, DnaDefinition] = {}
    if not _DNA_DATA_DIR.is_dir():
        logger.error("DNA数据目录不存在: %s", _DNA_DATA_DIR)
        _library = library
        return _library

    for json_file in sorted(_DNA_DATA_DIR.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                dna = json.load(f)
            dna_id = dna.get("id")
            if not dna_id:
                logger.warning("跳过无效DNA文件（缺少id字段）: %s", json_file.name)
                continue
            library[dna_id] = dna
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("加载DNA文件失败 %s: %s", json_file.name, e)

    _library = library
    logger.info("已加载 %d 个内置DNA", len(library))
    return _library


def reload_library() -> dict[str, DnaDefinition]:
    """强制重新加载DNA库（热更新用），返回新的库。"""
    global _library
    _library = None
    return _load_library()


# ---------------------------------------------------------------------------
# 对外 API
# ---------------------------------------------------------------------------

def get_all_dna_ids() -> list[str]:
    """返回所有内置DNA ID列表。"""
    return list(_load_library().keys())


def get_dna(dna_id: str) -> DnaDefinition:
    """根据ID获取单个DNA定义，不存在则抛出 KeyError。"""
    library = _load_library()
    return library[dna_id]


def list_dnas() -> list[DnaDefinition]:
    """返回所有DNA定义列表。"""
    return list(_load_library().values())


def match_dnas_by_keywords(text: str) -> list[tuple[str, int]]:
    """
    基于关键词粗匹配，返回 [(dna_id, 命中次数)] 按命中数降序。

    这是规则兜底用的轻量匹配器，analyzer 会先用LLM精匹配，
    LLM失败时退回此规则匹配。
    """
    scores: dict[str, int] = {}
    text_lower = text.lower()

    for dna_id, dna in _load_library().items():
        keywords = dna.get("matching_keywords", [])
        count = sum(1 for kw in keywords if kw and kw.lower() in text_lower)
        if count > 0:
            scores[dna_id] = count

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def pick_default_dnas() -> list[tuple[str, float]]:
    """
    完全无信息时的默认DNA组合：闺蜜旅游分享 + 本地人推荐 + 送礼攻略。
    返回 [(dna_id, weight)]，权重和为1.0。
    """
    return [
        ("bestie_travel_share", 0.5),
        ("local_recommend", 0.3),
        ("gift_guide", 0.2),
    ]
