from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent

KEYFRAMES = ROOT / "keyframes"
MAP_KEYFRAMES = ROOT / "map-keyframes"

OUTPUT = ROOT / "manifest.csv"


def get_collection_id(video_id):
    return video_id.split("_V", 1)[0]


def build_manifest():
    rows = []

    video_dirs = sorted(
        p for p in KEYFRAMES.iterdir()
        if p.is_dir()
    )

    for video_dir in video_dirs:
        video_id = video_dir.name
        collection_id = get_collection_id(video_id)

        map_file = MAP_KEYFRAMES / f"{video_id}.csv"

        if not map_file.exists():
            print(f"[ERROR] Missing map: {video_id}")
            continue

        with map_file.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:
            reader = csv.DictReader(f)

            for row in reader:
                n = int(row["n"])
                frame_idx = int(row["frame_idx"])
                pts_time = float(row["pts_time"])

                image_candidates = [
                    video_dir / f"{n:03d}.jpg",
                    video_dir / f"{n:03d}.jpeg",
                    video_dir / f"{n:03d}.png",
                ]

                image_path = next(
                    (p for p in image_candidates if p.exists()),
                    None
                )

                if image_path is None:
                    print(
                        f"[ERROR] Missing image: "
                        f"{video_id} n={n}"
                    )
                    continue

                keyframe_id = (
                    f"{video_id}_{n:06d}"
                )

                rows.append({
                    "keyframe_id": keyframe_id,
                    "collection_id": collection_id,
                    "video_id": video_id,
                    "frame_number": frame_idx,
                    "timestamp_ms": round(pts_time * 1000),
                    "image_path": image_path.relative_to(ROOT).as_posix(),
                    "video_path": "",
                })

    fieldnames = [
        "keyframe_id",
        "collection_id",
        "video_id",
        "frame_number",
        "timestamp_ms",
        "image_path",
        "video_path",
    ]

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    print()
    print("========== MANIFEST ==========")
    print(f"Videos: {len(video_dirs)}")
    print(f"Keyframes: {len(rows)}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    build_manifest()