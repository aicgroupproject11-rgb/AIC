from pathlib import Path
import csv
from collections import Counter

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.csv"


def main():
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    print("\n========== MANIFEST VALIDATION ==========\n")

    print(f"Rows: {len(rows):,}")

    keyframe_ids = [r["keyframe_id"] for r in rows]
    image_paths = [r["image_path"] for r in rows]

    duplicate_keyframes = [
        x for x, count in Counter(keyframe_ids).items()
        if count > 1
    ]

    duplicate_images = [
        x for x, count in Counter(image_paths).items()
        if count > 1
    ]

    missing_images = []
    invalid_timestamps = []
    invalid_frames = []
    invalid_collections = []

    for row in rows:
        image_path = ROOT / row["image_path"]

        if not image_path.exists():
            missing_images.append(row["image_path"])

        try:
            timestamp = int(row["timestamp_ms"])
            if timestamp < 0:
                invalid_timestamps.append(row["keyframe_id"])
        except ValueError:
            invalid_timestamps.append(row["keyframe_id"])

        try:
            frame = int(row["frame_number"])
            if frame < 0:
                invalid_frames.append(row["keyframe_id"])
        except ValueError:
            invalid_frames.append(row["keyframe_id"])

        expected_collection = row["video_id"].split("_V", 1)[0]

        if row["collection_id"] != expected_collection:
            invalid_collections.append(row["keyframe_id"])

    video_ids = {r["video_id"] for r in rows}
    collection_ids = {r["collection_id"] for r in rows}

    print(f"Videos: {len(video_ids):,}")
    print(f"Collections: {len(collection_ids):,}")

    print(f"\nDuplicate keyframe_id: {len(duplicate_keyframes):,}")
    print(f"Duplicate image_path:  {len(duplicate_images):,}")
    print(f"Missing images:        {len(missing_images):,}")
    print(f"Invalid timestamps:    {len(invalid_timestamps):,}")
    print(f"Invalid frame numbers: {len(invalid_frames):,}")
    print(f"Invalid collections:   {len(invalid_collections):,}")

    print("\n========== RESULT ==========\n")

    if not any([
        duplicate_keyframes,
        duplicate_images,
        missing_images,
        invalid_timestamps,
        invalid_frames,
        invalid_collections,
    ]):
        print("MANIFEST VALIDATION: PASS")
    else:
        print("MANIFEST VALIDATION: FAIL")

        if duplicate_keyframes:
            print("\nDuplicate keyframe IDs:")
            print(duplicate_keyframes[:20])

        if duplicate_images:
            print("\nDuplicate image paths:")
            print(duplicate_images[:20])

        if missing_images:
            print("\nMissing images:")
            print(missing_images[:20])

        if invalid_timestamps:
            print("\nInvalid timestamps:")
            print(invalid_timestamps[:20])

        if invalid_frames:
            print("\nInvalid frame numbers:")
            print(invalid_frames[:20])

        if invalid_collections:
            print("\nInvalid collections:")
            print(invalid_collections[:20])


if __name__ == "__main__":
    main()