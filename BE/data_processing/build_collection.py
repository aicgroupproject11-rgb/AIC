from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parent

MANIFEST = ROOT / "manifest.csv"
OUTPUT = ROOT / "collection.json"


def build_collection():
    collections = {}

    with MANIFEST.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            collection_id = row["collection_id"]
            video_id = row["video_id"]

            if collection_id not in collections:
                collections[collection_id] = set()

            collections[collection_id].add(video_id)

    data = {
        "collections": [
            {
                "collection_id": collection_id,
                "videos": sorted(videos)
            }
            for collection_id, videos
            in sorted(collections.items())
        ]
    }

    with OUTPUT.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("========== COLLECTION ==========")
    print(f"Collections: {len(data['collections'])}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    build_collection()