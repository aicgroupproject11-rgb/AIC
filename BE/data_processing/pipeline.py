from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
REQUIRED_SOURCES = ("keyframes", "map-keyframes", "media-info", "objects", "clip-features-32")


@dataclass(frozen=True)
class DatasetReport:
    data_root: str
    source_video_counts: dict[str, int]
    collections: dict[str, int]
    common_video_count: int
    missing_by_source: dict[str, list[str]]
    errors: list[str]

    @property
    def valid(self) -> bool:
        return not self.errors and not any(self.missing_by_source.values())

    def to_dict(self) -> dict:
        result = asdict(self)
        result["valid"] = self.valid
        return result


def scan_dataset(data_root: Path | str, *, deep: bool = False) -> DatasetReport:
    data_root = Path(data_root).resolve()
    sources = {
        "keyframes": _directory_ids(data_root / "keyframes"),
        "map-keyframes": _file_ids(data_root / "map-keyframes", ".csv"),
        "media-info": _file_ids(data_root / "media-info", ".json"),
        "objects": _directory_ids(data_root / "objects"),
        "clip-features-32": _file_ids(data_root / "clip-features-32", ".npy"),
    }
    errors = [f"Thiếu thư mục: {data_root / source}" for source in REQUIRED_SOURCES if not (data_root / source).is_dir()]
    all_ids = set().union(*sources.values()) if sources else set()
    missing = {
        source: sorted(all_ids - video_ids)
        for source, video_ids in sources.items()
        if all_ids - video_ids
    }
    collections = Counter(_collection_id(video_id) for video_id in all_ids)
    common = set.intersection(*sources.values()) if sources and all(sources.values()) else set()
    if not all_ids:
        errors.append("Không tìm thấy video_id nào trong data-root")
    elif not common:
        errors.append("Không có video_id nào xuất hiện đầy đủ ở mọi nguồn bắt buộc")

    if deep:
        for video_id in sorted(common):
            errors.extend(_validate_video(data_root, video_id))
    return DatasetReport(
        data_root=str(data_root),
        source_video_counts={key: len(value) for key, value in sources.items()},
        collections=dict(sorted(collections.items())),
        common_video_count=len(common),
        missing_by_source=missing,
        errors=errors,
    )


def build_manifest(
    data_root: Path | str,
    output_path: Path | str | None = None,
) -> dict:
    data_root = Path(data_root).resolve()
    output_path = Path(output_path or data_root / "manifest.csv").resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "keyframe_id",
        "collection_id",
        "video_id",
        "keyframe_number",
        "clip_vector_index",
        "frame_number",
        "timestamp_ms",
        "image_path",
        "video_path",
    ]
    video_count = 0
    keyframe_count = 0
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for video_dir in sorted((data_root / "keyframes").iterdir()):
            if not video_dir.is_dir():
                continue
            video_id = video_dir.name
            map_file = data_root / "map-keyframes" / f"{video_id}.csv"
            clip_file = data_root / "clip-features-32" / f"{video_id}.npy"
            if not map_file.is_file() or not clip_file.is_file():
                raise ValueError(f"{video_id}: thiếu map-keyframes hoặc clip-features-32")
            video_count += 1
            with map_file.open("r", encoding="utf-8-sig", newline="") as mapping:
                reader = csv.DictReader(mapping)
                required = {"n", "frame_idx", "pts_time"}
                if required - set(reader.fieldnames or []):
                    raise ValueError(f"{map_file}: thiếu cột {sorted(required - set(reader.fieldnames or []))}")
                for vector_index, row in enumerate(reader):
                    keyframe_number = int(row["n"])
                    image = _resolve_image(video_dir, keyframe_number)
                    if image is None:
                        raise ValueError(f"{video_id}: thiếu ảnh keyframe n={keyframe_number}")
                    video_file = data_root / "videos" / f"{video_id}.mp4"
                    writer.writerow(
                        {
                            "keyframe_id": f"{video_id}_{keyframe_number:06d}",
                            "collection_id": _collection_id(video_id),
                            "video_id": video_id,
                            "keyframe_number": keyframe_number,
                            "clip_vector_index": vector_index,
                            "frame_number": int(row["frame_idx"]),
                            "timestamp_ms": round(float(row["pts_time"]) * 1000),
                            "image_path": image.relative_to(data_root).as_posix(),
                            "video_path": video_file.relative_to(data_root).as_posix() if video_file.is_file() else "",
                        }
                    )
                    keyframe_count += 1
    return {"videos": video_count, "keyframes": keyframe_count, "output": str(output_path)}


def build_collection(manifest_path: Path | str, output_path: Path | str | None = None) -> dict:
    manifest_path = Path(manifest_path).resolve()
    output_path = Path(output_path or manifest_path.with_name("collection.json")).resolve()
    collections: dict[str, set[str]] = {}
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            collections.setdefault(row["collection_id"], set()).add(row["video_id"])
    payload = {
        "collections": [
            {"collection_id": key, "videos": sorted(value)}
            for key, value in sorted(collections.items())
        ]
    }
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return {"collections": len(collections), "output": str(output_path)}


def _validate_video(data_root: Path, video_id: str) -> list[str]:
    errors = []
    images = [path for path in (data_root / "keyframes" / video_id).iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS]
    with (data_root / "map-keyframes" / f"{video_id}.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        mapping = list(csv.DictReader(handle))
    try:
        import numpy as np

        features = np.load(data_root / "clip-features-32" / f"{video_id}.npy", mmap_mode="r")
        feature_count = features.shape[0] if features.ndim == 2 else -1
    except ImportError:
        feature_count = len(mapping)
    if len(images) != len(mapping) or len(mapping) != feature_count:
        errors.append(
            f"{video_id}: keyframes={len(images)}, map={len(mapping)}, clip={feature_count}"
        )
    expected = [int(row["n"]) for row in mapping]
    actual = sorted(int(path.stem) for path in images if path.stem.isdigit())
    if expected != actual:
        errors.append(f"{video_id}: tên ảnh không khớp cột n trong map-keyframes")
    return errors


def _resolve_image(video_dir: Path, keyframe_number: int) -> Path | None:
    for width in (3, 4, 6):
        for extension in IMAGE_EXTENSIONS:
            candidate = video_dir / f"{keyframe_number:0{width}d}{extension}"
            if candidate.is_file():
                return candidate
    return None


def _directory_ids(path: Path) -> set[str]:
    return {item.name for item in path.iterdir() if item.is_dir()} if path.is_dir() else set()


def _file_ids(path: Path, suffix: str) -> set[str]:
    return {item.stem for item in path.glob(f"*{suffix}")} if path.is_dir() else set()


def _collection_id(video_id: str) -> str:
    if "_V" not in video_id:
        raise ValueError(f"video_id không đúng dạng Lxx_Vxxx: {video_id}")
    return video_id.split("_V", 1)[0]
