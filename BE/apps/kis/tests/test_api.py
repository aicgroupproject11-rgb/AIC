from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from apps.kis.services import SearchServiceUnavailable


SAMPLE_RESULT = {
    "rank": 1,
    "keyframe_id": "L21_V001_000001",
    "collection_id": "L21",
    "video_id": "L21_V001",
    "frame_number": 531,
    "timestamp_ms": 17700,
    "image_path": "keyframes/L21_V001/000001.jpg",
    "video_path": "videos/L21_V001.mp4",
    "score": 0.82,
}


class KisSearchApiTests(SimpleTestCase):
    def test_rejects_empty_query(self):
        response = self.client.post(
            reverse("kis-search"),
            data={"query": ""},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_top_k_over_100(self):
        response = self.client.post(
            reverse("kis-search"),
            data={"query": "test", "top_k": 101},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("apps.kis.views.process_fe_command")
    def test_search_returns_results(self, mock_process):
        mock_process.return_value = (
            {
                "keys": ["red", "shirt"],
                "effective_collection_ids": ["L21"],
            },
            [SAMPLE_RESULT],
        )

        response = self.client.post(
            reverse("kis-search"),
            data={"query": "red shirt #L21", "top_k": 20},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["frame_id"], 531)

    @patch("apps.kis.views.process_fe_command")
    def test_search_returns_503_when_engine_is_missing(self, mock_process):
        mock_process.side_effect = SearchServiceUnavailable("missing index")

        response = self.client.post(
            reverse("kis-search"),
            data={"query": "bicycle"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 503)
