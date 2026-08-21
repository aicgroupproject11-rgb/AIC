import csv
import tempfile
import unittest
from pathlib import Path

from data_processing.pipeline import build_manifest, scan_dataset


class DataPipelineTests(unittest.TestCase):
    def test_builds_explicit_clip_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("keyframes", "map-keyframes", "media-info", "objects", "clip-features-32"):
                (root / name).mkdir()
            (root / "keyframes" / "L21_V001").mkdir()
            (root / "objects" / "L21_V001").mkdir()
            (root / "keyframes" / "L21_V001" / "001.jpg").write_bytes(b"image")
            (root / "clip-features-32" / "L21_V001.npy").write_bytes(b"placeholder")
            (root / "media-info" / "L21_V001.json").write_text("{}", encoding="utf-8")
            with (root / "map-keyframes" / "L21_V001.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["n", "frame_idx", "pts_time"])
                writer.writeheader()
                writer.writerow({"n": 1, "frame_idx": 90, "pts_time": 3.0})

            summary = build_manifest(root)
            with (root / "manifest.csv").open(encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))

            self.assertEqual(summary["keyframes"], 1)
            self.assertEqual(row["keyframe_number"], "1")
            self.assertEqual(row["clip_vector_index"], "0")
            self.assertEqual(row["timestamp_ms"], "3000")

    def test_scan_reports_missing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "keyframes" / "L21_V001").mkdir(parents=True)
            report = scan_dataset(root)
            self.assertFalse(report.valid)
            self.assertTrue(report.errors)


if __name__ == "__main__":
    unittest.main()
