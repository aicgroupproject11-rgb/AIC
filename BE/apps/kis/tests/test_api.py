from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse


VALID_RESULT = {
    "rank": 1,
    "keyframe_id": "L21_V001_000125",
    "collection_id": "L21",
    "video_id": "L21_V001",
    "frame_number": 125,
    "timestamp_ms": 5000,
    "image_path": "keyframes/L21/V001/000125.jpg",
    "video_path": "videos/L21/V001.mp4",
    "score": 0.92,
}


class KisSearchApiTests(SimpleTestCase):
    def test_rejects_blank_query(self):
        response = self.client.post(
            reverse("kis-search"),
            data={"query": "   "},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_rejects_top_k_over_100(self):
        response = self.client.post(
            reverse("kis-search"),
            data={"query": "a bicycle", "top_k": 101},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("apps.kis.views.search_kis")
    def test_returns_the_agreed_contract(self, mock_search_kis):
        mock_search_kis.return_value = [VALID_RESULT]

        response = self.client.post(
            reverse("kis-search"),
            data={
                "query": "a man riding a bike",
                "collection_ids": ["L21", "L21"],
                "top_k": 20,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["keyframe_id"], "L21_V001_000125")
        mock_search_kis.assert_called_once_with(
            query="a man riding a bike",
            collection_ids=["L21"],
            top_k=20,
        )

    @patch("apps.kis.views.search_kis")
    def test_rejects_result_that_breaks_the_contract(self, mock_search_kis):
        mock_search_kis.return_value = [{"video_id": "L21_V001"}]

        response = self.client.post(
            reverse("kis-search"),
            data={"query": "a bicycle"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "invalid_search_output")

    @patch("apps.kis.views.search_kis")
    def test_never_returns_more_than_top_k(self, mock_search_kis):
        second_result = {
            **VALID_RESULT,
            "rank": 2,
            "keyframe_id": "L21_V001_000250",
            "frame_number": 250,
            "timestamp_ms": 10000,
        }
        mock_search_kis.return_value = [VALID_RESULT, second_result]

        response = self.client.post(
            reverse("kis-search"),
            data={"query": "a bicycle", "top_k": 1},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_returns_503_while_algorithm_module_is_missing(self):
        response = self.client.post(
            reverse("kis-search"),
            data={"query": "a bicycle"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "search_service_unavailable")
