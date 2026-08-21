import json
import tempfile
import unittest
from pathlib import Path

from search_engine.objects import load_object_terms
from search_engine.text import normalize_text


class ObjectParserTests(unittest.TestCase):
    def test_normalizes_vietnamese_d_stroke(self):
        self.assertEqual(normalize_text("Người đi xe đạp"), "nguoi di xe dap")

    def test_parses_official_parallel_arrays_and_applies_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "001.json"
            path.write_text(
                json.dumps(
                    {
                        "detection_scores": ["0.91", "0.30", "0.10"],
                        "detection_class_entities": ["Human face", "Bicycle", "Noise"],
                    }
                ),
                encoding="utf-8",
            )
            bag = load_object_terms(path, min_score=0.25)
            self.assertEqual(bag, {"human face": 0.91, "bicycle": 0.30})


if __name__ == "__main__":
    unittest.main()
