"""爆款DNA库 · 6个内置写作基因，覆盖95%以上特产小红书场景。

DNA以JSON配置形式存放在 data/ 目录，代码与数据分离，
运营可直接修改/新增DNA文件实现热插拔。
"""

from .library import (
    DnaDefinition,
    get_all_dna_ids,
    get_dna,
    list_dnas,
    match_dnas_by_keywords,
    pick_default_dnas,
    reload_library,
)

__all__ = [
    "DnaDefinition",
    "get_all_dna_ids",
    "get_dna",
    "list_dnas",
    "match_dnas_by_keywords",
    "pick_default_dnas",
    "reload_library",
]
