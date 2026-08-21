from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .text import normalize_text


def load_object_terms(
    object_file: Path,
    *,
    min_score: float = 0.25,
    max_terms: int = 20,
) -> dict[str, float]:
    """Read one official AIC object JSON file into a compact weighted bag.

    The official files contain parallel ``detection_scores`` and
    ``detection_class_entities`` arrays. A small compatibility path also accepts
    lists/dicts from common YOLO exporters so a class can enrich the dataset.
    """
    if not object_file.is_file():
        return {}
    with object_file.open("r", encoding="utf-8-sig") as handle:
        raw = json.load(handle)

    weighted: dict[str, float] = defaultdict(float)
    if isinstance(raw, dict) and isinstance(raw.get("detection_class_entities"), list):
        names = raw["detection_class_entities"]
        scores = raw.get("detection_scores", [1.0] * len(names))
        for name, score in zip(names, scores):
            _add_term(weighted, name, score, min_score)
    else:
        for item in _walk_detections(raw):
            name = item.get("entity") or item.get("class_name") or item.get("label") or item.get("name")
            score = item.get("score", item.get("confidence", 1.0))
            _add_term(weighted, name, score, min_score)

    ordered = sorted(weighted.items(), key=lambda item: (-item[1], item[0]))
    return dict(ordered[:max_terms])


def resolve_object_file(data_root: Path, video_id: str, keyframe_number: int) -> Path:
    folder = data_root / "objects" / video_id
    for width in (3, 4, 6):
        candidate = folder / f"{keyframe_number:0{width}d}.json"
        if candidate.is_file():
            return candidate
    return folder / f"{keyframe_number:03d}.json"


def build_vocabulary(bags: Iterable[dict[str, float]]) -> tuple[list[str], dict[str, int]]:
    vocabulary = sorted({term for bag in bags for term in bag})
    return vocabulary, {term: index for index, term in enumerate(vocabulary)}


def _add_term(target: dict[str, float], name: object, score: object, min_score: float) -> None:
    if not isinstance(name, str):
        return
    term = normalize_text(name)
    if not term:
        return
    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        return
    if numeric_score >= min_score:
        target[term] = max(target[term], min(1.0, numeric_score))


def _walk_detections(value: object):
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
    elif isinstance(value, dict):
        for key in ("detections", "objects", "predictions", "results"):
            nested = value.get(key)
            if isinstance(nested, list):
                yield from _walk_detections(nested)
