from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .exceptions import IndexBuildError


REQUIRED_COLUMNS = {
    "keyframe_id",
    "collection_id",
    "video_id",
    "frame_number",
    "timestamp_ms",
    "image_path",
    "video_path",
}


@dataclass(frozen=True)
class ManifestRecord:
    keyframe_id: str
    collection_id: str
    video_id: str
    keyframe_number: int
    clip_vector_index: int
    frame_number: int
    timestamp_ms: int
    image_path: str
    video_path: str

    def result_dict(self) -> dict:
        return {
            "keyframe_id": self.keyframe_id,
            "collection_id": self.collection_id,
            "video_id": self.video_id,
            "frame_number": self.frame_number,
            "timestamp_ms": self.timestamp_ms,
            "image_path": self.image_path,
            "video_path": self.video_path or f"videos/{self.video_id}.mp4",
        }


def load_manifest(path: Path | str) -> list[ManifestRecord]:
    path = Path(path)
    if not path.is_file():
        raise IndexBuildError(f"Không tìm thấy manifest: {path}")

    records: list[ManifestRecord] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise IndexBuildError(f"manifest thiếu cột: {', '.join(sorted(missing))}")
        per_video_position: dict[str, int] = {}
        for line_number, row in enumerate(reader, start=2):
            try:
                video_id = row["video_id"].strip()
                fallback_position = per_video_position.get(video_id, 0)
                keyframe_number = int(row.get("keyframe_number") or _number_from_id(row["keyframe_id"]))
                clip_vector_index = int(row.get("clip_vector_index") or fallback_position)
                record = ManifestRecord(
                    keyframe_id=row["keyframe_id"].strip(),
                    collection_id=row["collection_id"].strip().upper(),
                    video_id=video_id,
                    keyframe_number=keyframe_number,
                    clip_vector_index=clip_vector_index,
                    frame_number=int(row["frame_number"]),
                    timestamp_ms=int(row["timestamp_ms"]),
                    image_path=_safe_relative_path(row["image_path"]),
                    video_path=_safe_relative_path(row["video_path"]) if row["video_path"].strip() else "",
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise IndexBuildError(f"manifest không hợp lệ tại dòng {line_number}: {exc}") from exc
            if not record.keyframe_id or record.keyframe_id in seen_ids:
                raise IndexBuildError(f"keyframe_id trống hoặc trùng tại dòng {line_number}: {record.keyframe_id}")
            seen_ids.add(record.keyframe_id)
            records.append(record)
            per_video_position[video_id] = fallback_position + 1
    if not records:
        raise IndexBuildError("manifest không có keyframe")
    return records


def group_by_video(records: list[ManifestRecord]) -> dict[str, list[tuple[int, ManifestRecord]]]:
    grouped: dict[str, list[tuple[int, ManifestRecord]]] = {}
    for global_position, record in enumerate(records):
        grouped.setdefault(record.video_id, []).append((global_position, record))
    return grouped


def _number_from_id(keyframe_id: str) -> int:
    try:
        return int(keyframe_id.rsplit("_", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"không suy ra được keyframe_number từ {keyframe_id!r}") from exc


def _safe_relative_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/").lstrip("/")
    path = Path(normalized)
    if ".." in path.parts:
        raise ValueError(f"đường dẫn không an toàn: {value!r}")
    return path.as_posix()
