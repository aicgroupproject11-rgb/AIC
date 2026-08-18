from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent

DIRS = {
    "keyframes": ROOT / "keyframes",
    "map-keyframes": ROOT / "map-keyframes",
    "media-info": ROOT / "media-info",
    "objects": ROOT / "objects",
    "clip-features-32": ROOT / "clip-features-32",
}


def get_keyframe_videos():
    root = DIRS["keyframes"]
    return {
        p.name
        for p in root.iterdir()
        if p.is_dir()
    }


def get_map_videos():
    root = DIRS["map-keyframes"]
    return {
        p.stem
        for p in root.glob("*.csv")
    }


def get_media_videos():
    root = DIRS["media-info"]
    return {
        p.stem
        for p in root.glob("*.json")
    }


def get_object_videos():
    root = DIRS["objects"]
    return {
        p.name
        for p in root.iterdir()
        if p.is_dir()
    }


def get_clip_videos():
    root = DIRS["clip-features-32"]
    return {
        p.stem
        for p in root.glob("*.npy")
    }


def print_comparison(data):
    print("\n========== AIC DATASET SCAN ==========\n")

    for name, ids in data.items():
        print(f"{name:20} {len(ids):>6} videos")

    print("\n========== CROSS SOURCE ==========\n")

    all_ids = set().union(*data.values())

    print(f"TOTAL UNIQUE VIDEO IDs: {len(all_ids)}")

    print("\nMissing source:")
    found_problem = False

    for video_id in sorted(all_ids):
        missing = [
            name
            for name, ids in data.items()
            if video_id not in ids
        ]

        if missing:
            found_problem = True
            print(f"  {video_id}: missing {', '.join(missing)}")

    if not found_problem:
        print("  None")

    print("\n========== COLLECTION SUMMARY ==========\n")

    collections = Counter()

    for video_id in all_ids:
        if "_V" in video_id:
            collection = video_id.split("_V", 1)[0]
            collections[collection] += 1

    for collection, count in sorted(collections.items()):
        print(f"{collection:10} {count:>6} videos")

def count_keyframes(video_id):
    folder = DIRS["keyframes"] / video_id

    if not folder.exists():
        return 0

    return sum(
        1
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )


def count_map_records(video_id):
    csv_file = DIRS["map-keyframes"] / f"{video_id}.csv"

    if not csv_file.exists():
        return 0

    with csv_file.open("r", encoding="utf-8-sig") as f:
        return max(sum(1 for _ in f) - 1, 0)


def count_clip_vectors(video_id):
    import numpy as np

    npy_file = DIRS["clip-features-32"] / f"{video_id}.npy"

    if not npy_file.exists():
        return 0

    arr = np.load(npy_file, mmap_mode="r")

    if arr.ndim != 2:
        return -1

    return arr.shape[0]

def validate_keyframe_counts(video_ids):
    print("\n========== KEYFRAME COUNT VALIDATION ==========\n")

    errors = []

    for video_id in sorted(video_ids):
        images = count_keyframes(video_id)
        mappings = count_map_records(video_id)
        clips = count_clip_vectors(video_id)

        if not (images == mappings == clips):
            errors.append(
                (video_id, images, mappings, clips)
            )

    print(f"Checked videos: {len(video_ids)}")
    print(f"Count mismatches: {len(errors)}")

    if errors:
        print("\nMISMATCHES:\n")

        for video_id, images, mappings, clips in errors:
            print(
                f"{video_id}: "
                f"images={images}, "
                f"map={mappings}, "
                f"clip={clips}"
            )
    else:
        print("All videos have matching image/map/CLIP counts.")

import csv


def validate_image_mapping(video_ids):
    print("\n========== IMAGE ↔ MAP VALIDATION ==========\n")

    errors = []

    for video_id in sorted(video_ids):
        folder = DIRS["keyframes"] / video_id
        csv_file = DIRS["map-keyframes"] / f"{video_id}.csv"

        expected = []

        with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                n = int(row["n"])
                expected.append(n)

        actual = sorted(
            int(p.stem)
            for p in folder.iterdir()
            if p.is_file()
            and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
            and p.stem.isdigit()
        )

        if expected != actual:
            errors.append({
                "video_id": video_id,
                "expected_first": expected[:5],
                "actual_first": actual[:5],
                "expected_last": expected[-5:],
                "actual_last": actual[-5:],
            })

    print(f"Checked videos: {len(video_ids)}")
    print(f"Mapping mismatches: {len(errors)}")

    if errors:
        print("\nMISMATCHES:\n")

        for error in errors[:50]:
            print(error)
    else:
        print("All image filenames match map-keyframes n values.")


def main():
    for name, path in DIRS.items():
        if not path.exists():
            print(f"[ERROR] Missing directory: {path}")
            return

    data = {
        "keyframes": get_keyframe_videos(),
        "map-keyframes": get_map_videos(),
        "media-info": get_media_videos(),
        "objects": get_object_videos(),
        "clip-features-32": get_clip_videos(),
    }

    print_comparison(data)
    validate_keyframe_counts(data["keyframes"])
    validate_image_mapping(data["keyframes"])


if __name__ == "__main__":
    main()
