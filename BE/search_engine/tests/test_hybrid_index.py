import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from search_engine.builder import BuildOptions, build_search_index
from search_engine.indexer import HybridSearchIndex
from search_engine.kis import inspect


class FakeEncoder:
    def encode_texts(self, prompts):
        vectors = np.zeros((len(prompts), 4), dtype=np.float32)
        for index in range(len(prompts)):
            vectors[index, index % 4] = 1.0
        return vectors

    def encode_text(self, text):
        if "bicycle" in text.lower() or "xe đạp" in text.lower():
            return np.asarray([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
        return np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32)


class HybridIndexTests(unittest.TestCase):
    def test_routes_to_domain_tree_and_reranks_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_root = root / "data"
            index_root = root / "index"
            (data_root / "clip-features-32").mkdir(parents=True)
            (data_root / "objects" / "L21_V001").mkdir(parents=True)
            np.save(
                data_root / "clip-features-32" / "L21_V001.npy",
                np.asarray([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float32),
            )
            for number, entities in (
                (1, ["Person"]),
                (2, ["Person", "Bicycle"]),
            ):
                (data_root / "objects" / "L21_V001" / f"{number:03d}.json").write_text(
                    json.dumps(
                        {
                            "detection_scores": ["0.9"] * len(entities),
                            "detection_class_entities": entities,
                        }
                    ),
                    encoding="utf-8",
                )
            with (data_root / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
                fields = [
                    "keyframe_id", "collection_id", "video_id", "keyframe_number",
                    "clip_vector_index", "frame_number", "timestamp_ms", "image_path", "video_path",
                ]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for position in range(2):
                    writer.writerow(
                        {
                            "keyframe_id": f"L21_V001_{position + 1:06d}",
                            "collection_id": "L21",
                            "video_id": "L21_V001",
                            "keyframe_number": position + 1,
                            "clip_vector_index": position,
                            "frame_number": position * 90,
                            "timestamp_ms": position * 3000,
                            "image_path": f"keyframes/L21_V001/{position + 1:03d}.jpg",
                            "video_path": "",
                        }
                    )

            build_search_index(
                data_root=data_root,
                index_dir=index_root,
                encoder=FakeEncoder(),
                options=BuildOptions(pca_dimensions=2, pca_sample_size=2, domains_per_frame=1),
            )
            index = HybridSearchIndex.load(index_root)
            query_vector = np.asarray([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
            route = index.router.route("xe đạp", query_vector)
            positions, trace = index.candidates_with_trace(
                index.reduce_query(query_vector), route, ["L21"], 20
            )
            results = index.rerank(query_vector, route, positions, top_k=1)
            self.assertEqual(index.records[results[0].position].keyframe_number, 2)
            self.assertIn("bicycle", results[0].matched_objects)
            person = index.vocabulary.index("person")
            bicycle = index.vocabulary.index("bicycle")
            self.assertLess(index.bow_idf[person], index.bow_idf[bicycle])
            self.assertGreater(trace["unique_candidate_count"], 0)
            self.assertTrue(
                any(
                    tree["tree_key"].startswith("collection_domain:L21:")
                    and tree["entry_count"] > 0
                    for tree in trace["trees"]
                )
            )
            with (
                patch("search_engine.kis.get_index", return_value=index),
                patch("search_engine.kis.get_encoder", return_value=FakeEncoder()),
            ):
                inspection = inspect(
                    query="nguowif ddi xe ddapj",
                    collection_ids=["L21"],
                    top_k=10,
                )
            self.assertEqual(
                inspection["routing"]["selected_domains"][0],
                "transport",
            )
            self.assertEqual(inspection["index"]["format_version"], 2)
            self.assertTrue(inspection["candidate_trace"]["trees"])
            index.close()


if __name__ == "__main__":
    unittest.main()
