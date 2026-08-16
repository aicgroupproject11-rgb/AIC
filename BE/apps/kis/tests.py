from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse


class KISSearchViewTestCase(SimpleTestCase):

    def test_rejects_empty_query(self):
        response = self.client.post(reverse("kis-search"),data={"query": "",},content_type="application/json",)

        self.assertEqual(response.status_code,400,)


    def test_rejects_invalid_top_k_over_100(self):
        response = self.client.post(reverse("kis-search"),data={"query": "test","top_k": 101,},content_type="application/json",)

        self.assertEqual(response.status_code,400,)


    @patch("apps.kis.views.search_kis")
    def test_kis_search_view(self,mock_search_kis,):
        mock_search_kis.return_value = [
{
                "rank": 1,
                "video_id": "L21_V001",
                "frame_id": 531,
                "score": 0.82,
            },
            {
                "rank": 2,
                "video_id": "L22_V003",
                "frame_id": 888,
                "score": 0.79,
            },
        ]

        query = "query mẫu"
        top_k = 2

        response = self.client.post(
            reverse("kis-search"),
            data={
                "query": query,
                "top_k": top_k,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200,)

        self.assertEqual(response.json(),{"query": query,"count": 2,"results": mock_search_kis.return_value,},)

        mock_search_kis.assert_called_once_with(query=query,top_k=top_k,)

