"""Fine-grained DNA fragment library.

The MVP keeps one JSON array per fragment dimension. The files contain seeded
mock data only; extraction, staging-cache promotion, publication tracking and
score updates are deliberately outside this module.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

FragmentType = Literal[
    "scene",
    "valuePromise",
    "hook",
    "structure",
    "tone",
    "visualStyle",
]

FRAGMENT_TYPES: tuple[FragmentType, ...] = (
    "scene",
    "valuePromise",
    "hook",
    "structure",
    "tone",
    "visualStyle",
)

FragmentDefinition = dict[str, Any]
DnaFragment = FragmentDefinition

_DATA_DIR = Path(__file__).resolve().parent / "fragments"
_TYPE_FILES: dict[FragmentType, str] = {
    "scene": "scene.json",
    "valuePromise": "value_promise.json",
    "hook": "hook.json",
    "structure": "structure.json",
    "tone": "tone.json",
    "visualStyle": "visual_style.json",
}

_library: dict[FragmentType, list[FragmentDefinition]] | None = None


def _validate_fragment(fragment: Any, expected_type: FragmentType, source: Path) -> FragmentDefinition:
    if not isinstance(fragment, dict):
        raise ValueError(f"{source.name} contains a non-object fragment")

    required = ("fragmentId", "type", "value", "state", "score", "version")
    missing = [key for key in required if key not in fragment]
    if missing:
        raise ValueError(f"{source.name} fragment missing fields: {', '.join(missing)}")
    if fragment["type"] != expected_type:
        raise ValueError(
            f"{source.name} has type {fragment['type']!r}, expected {expected_type!r}"
        )
    if not isinstance(fragment["fragmentId"], str) or not fragment["fragmentId"]:
        raise ValueError(f"{source.name} has an invalid fragmentId")
    if not isinstance(fragment["value"], str) or not fragment["value"].strip():
        raise ValueError(f"{source.name} has an empty value")
    if not isinstance(fragment["score"], (int, float)) or not 0 <= fragment["score"] <= 1:
        raise ValueError(f"{source.name} has an invalid score")
    if fragment["state"] not in {"candidate", "rising", "stable", "watching", "retired"}:
        raise ValueError(f"{source.name} has an invalid state")
    if "evidenceIds" in fragment and not isinstance(fragment["evidenceIds"], list):
        raise ValueError(f"{source.name} evidenceIds must be a list")
    return fragment


def _load_library() -> dict[FragmentType, list[FragmentDefinition]]:
    global _library
    if _library is not None:
        return _library

    if not _DATA_DIR.is_dir():
        raise RuntimeError(f"DNA fragment directory does not exist: {_DATA_DIR}")

    library: dict[FragmentType, list[FragmentDefinition]] = {}
    seen_ids: set[str] = set()
    for fragment_type in FRAGMENT_TYPES:
        source = _DATA_DIR / _TYPE_FILES[fragment_type]
        if not source.is_file():
            raise RuntimeError(f"DNA fragment file does not exist: {source}")
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unable to load DNA fragment file {source}: {exc}") from exc
        if not isinstance(payload, list):
            raise ValueError(f"{source.name} must contain a JSON array")

        fragments = []
        for raw in payload:
            fragment = _validate_fragment(raw, fragment_type, source)
            fragment_id = fragment["fragmentId"]
            if fragment_id in seen_ids:
                raise ValueError(f"Duplicate fragmentId: {fragment_id}")
            seen_ids.add(fragment_id)
            fragments.append(fragment)
        library[fragment_type] = fragments

    _library = library
    logger.info(
        "Loaded %d fine-grained DNA fragments across %d dimensions",
        sum(len(items) for items in library.values()),
        len(library),
    )
    return _library


def reload_library() -> dict[FragmentType, list[FragmentDefinition]]:
    """Force a reload of the JSON fragment library."""
    global _library
    _library = None
    return _load_library()


def list_fragments(fragment_type: FragmentType | None = None) -> list[FragmentDefinition]:
    """Return all fragments, optionally limited to one dimension."""
    library = _load_library()
    if fragment_type is not None and fragment_type not in FRAGMENT_TYPES:
        raise ValueError(f"Unknown fragment type: {fragment_type}")
    if fragment_type is not None:
        return copy.deepcopy(library[fragment_type])
    return copy.deepcopy([fragment for items in library.values() for fragment in items])


def get_fragment(fragment_id: str) -> FragmentDefinition:
    """Return a fragment by ID or raise ``KeyError``."""
    for fragment in list_fragments():
        if fragment["fragmentId"] == fragment_id:
            return fragment
    raise KeyError(fragment_id)


def get_top_fragments(
    fragment_type: FragmentType,
    limit: int = 10,
) -> list[FragmentDefinition]:
    """Return the highest-scoring non-retired fragments in one dimension."""
    if fragment_type not in FRAGMENT_TYPES:
        raise ValueError(f"Unknown fragment type: {fragment_type}")
    if limit < 0:
        raise ValueError("limit must be non-negative")

    fragments = [
        fragment
        for fragment in list_fragments(fragment_type)
        if fragment.get("state") != "retired"
    ]
    fragments.sort(key=lambda item: (-float(item["score"]), item["fragmentId"]))
    return fragments[:limit]


def get_top_fragments_by_type(limit: int = 10) -> dict[FragmentType, list[FragmentDefinition]]:
    """Return a Top-K candidate pool for every required dimension."""
    if limit < 0:
        raise ValueError("limit must be non-negative")
    return {
        fragment_type: get_top_fragments(fragment_type, limit=limit)
        for fragment_type in FRAGMENT_TYPES
    }
