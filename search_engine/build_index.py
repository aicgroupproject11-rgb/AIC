import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search_engine.manifest import load_manifest, resolve_image_path
from search_engine.embedding import get_encoder
from search_engine.indexer import build_index
import numpy as np


def main():
    df = load_manifest()
    print(f"Reading {len(df)} keyframe from  manifest.csv")

    encoder = get_encoder()

    vectors, ids, collection_ids = [], [], []
    for i, (_, row) in enumerate(df.iterrows()):
        image_path = resolve_image_path(row["image_path"])
        try:
            vec = encoder.encode_image(image_path)
        except FileNotFoundError:
            print(f"Missing image: {image_path}")
            continue

        vectors.append(vec)
        ids.append(row["keyframe_id"])
        collection_ids.append(row["collection_id"])

        if (i + 1) % 100 == 0:
            print(f" encode {i + 1}/{len(df)}")

    full_vectors = np.stack(vectors)
    idx = build_index(ids, collection_ids, full_vectors)
    idx.save()

    print(f"\nCOMPLETE: build index for {len(ids)} keyframe.")
    print(f"Saved at: search_engine/data/search_index/")


if __name__ == "__main__":
    main()