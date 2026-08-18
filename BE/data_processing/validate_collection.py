from pathlib import Path
import csv
import json
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parent

MANIFEST = ROOT / "manifest.csv"
COLLECTION = ROOT / "collection.json"


def load_manifest():
    mapping = defaultdict(set)

    with MANIFEST.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            collection_id = row["collection_id"]
            video_id = row["video_id"]

            mapping[collection_id].add(video_id)

    return mapping


def load_collection():
    with COLLECTION.open(
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    return data


def validate_collection():
    manifest_mapping = load_manifest()
    data = load_collection()

    collections = data.get("collections", [])

    print("\n========== COLLECTION VALIDATION ==========\n")

    # --------------------------------------------------
    # 1. Check collection_id duplicates
    # --------------------------------------------------

    collection_ids = [
        item.get("collection_id")
        for item in collections
    ]

    duplicate_collections = [
        collection_id
        for collection_id, count
        in Counter(collection_ids).items()
        if count > 1
    ]

    # --------------------------------------------------
    # 2. Check video_id duplicates inside JSON
    # --------------------------------------------------

    all_json_videos = []

    for item in collections:
        videos = item.get("videos", [])
        all_json_videos.extend(videos)

    duplicate_videos = [
        video_id
        for video_id, count
        in Counter(all_json_videos).items()
        if count > 1
    ]

    # --------------------------------------------------
    # 3. Compare collection IDs
    # --------------------------------------------------

    manifest_collections = set(manifest_mapping.keys())
    json_collections = set(collection_ids)

    missing_collections = sorted(
        manifest_collections - json_collections
    )

    extra_collections = sorted(
        json_collections - manifest_collections
    )

    # --------------------------------------------------
    # 4. Compare videos
    # --------------------------------------------------

    manifest_videos = {
        video_id
        for videos in manifest_mapping.values()
        for video_id in videos
    }

    json_videos = set(all_json_videos)

    missing_videos = sorted(
        manifest_videos - json_videos
    )

    extra_videos = sorted(
        json_videos - manifest_videos
    )

    # --------------------------------------------------
    # 5. Compare videos per collection
    # --------------------------------------------------

    json_mapping = {
        item["collection_id"]: set(item.get("videos", []))
        for item in collections
    }

    collection_mismatches = []

    for collection_id in sorted(
        manifest_collections | json_collections
    ):
        expected = manifest_mapping.get(
            collection_id,
            set()
        )

        actual = json_mapping.get(
            collection_id,
            set()
        )

        if expected != actual:
            collection_mismatches.append({
                "collection_id": collection_id,
                "missing": sorted(expected - actual),
                "extra": sorted(actual - expected),
            })

    # --------------------------------------------------
    # Result
    # --------------------------------------------------

    print(f"Collections: {len(json_collections)}")
    print(f"Videos in collection.json: {len(all_json_videos)}")
    print(f"Unique videos: {len(json_videos)}")

    print(
        f"\nDuplicate collection_id: "
        f"{len(duplicate_collections)}"
    )

    print(
        f"Duplicate video_id: "
        f"{len(duplicate_videos)}"
    )

    print(
        f"Missing collections: "
        f"{len(missing_collections)}"
    )

    print(
        f"Extra collections: "
        f"{len(extra_collections)}"
    )

    print(
        f"Missing videos: "
        f"{len(missing_videos)}"
    )

    print(
        f"Extra videos: "
        f"{len(extra_videos)}"
    )

    print(
        f"Collection mismatches: "
        f"{len(collection_mismatches)}"
    )

    print("\n========== RESULT ==========\n")

    if not any([
        duplicate_collections,
        duplicate_videos,
        missing_collections,
        extra_collections,
        missing_videos,
        extra_videos,
        collection_mismatches,
    ]):
        print("COLLECTION VALIDATION: PASS")

    else:
        print("COLLECTION VALIDATION: FAIL")

        if duplicate_collections:
            print("\nDuplicate collection IDs:")
            print(duplicate_collections)

        if duplicate_videos:
            print("\nDuplicate video IDs:")
            print(duplicate_videos)

        if missing_collections:
            print("\nMissing collections:")
            print(missing_collections)

        if extra_collections:
            print("\nExtra collections:")
            print(extra_collections)

        if missing_videos:
            print("\nMissing videos:")
            print(missing_videos[:50])

        if extra_videos:
            print("\nExtra videos:")
            print(extra_videos[:50])

        if collection_mismatches:
            print("\nCollection mismatches:")

            for mismatch in collection_mismatches[:20]:
                print(mismatch)


if __name__ == "__main__":
    validate_collection()