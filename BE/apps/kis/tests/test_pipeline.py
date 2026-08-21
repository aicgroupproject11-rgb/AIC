from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.kis.pipeline import process_fe_command
from apps.kis.services import InvalidSearchRequest


class KisPipelineTests(SimpleTestCase):
    @override_settings(
        KIS_SEARCH_FUNCTION="apps.kis.tests.test_pipeline.fake_search"
    )
    @patch("apps.kis.tests.test_pipeline.fake_search")
    def test_query_is_parsed_before_search(self, mock_search):
        mock_search.return_value = []

        parsed, results = process_fe_command(
            query="red shirt #L21",
            collection_ids=[],
            top_k=20,
        )

        self.assertEqual(parsed["keys"], ["red", "shirt"])
        self.assertEqual(parsed["effective_collection_ids"], ["L21"])
        self.assertEqual(results, [])
        mock_search.assert_called_once_with(
            query="red shirt",
            collection_ids=["L21"],
            top_k=20,
        )

    def test_query_cannot_only_have_collection_tag(self):
        with self.assertRaises(InvalidSearchRequest):
            process_fe_command("#L21", [], 20)


def fake_search(*, query, collection_ids, top_k):
    return []
