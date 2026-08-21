import unittest

from search_engine.query_analyzer import analyze_query, best_term_match


class QueryAnalyzerTests(unittest.TestCase):
    def test_builds_vietnamese_ngram_candidates(self):
        analysis = analyze_query("Tìm người đi xe đạp")

        self.assertEqual(analysis.normalized, "tim nguoi di xe dap")
        self.assertIn("xe dap", analysis.candidates)

    def test_matches_a_small_typo_but_rejects_short_fuzzy_tokens(self):
        typo = analyze_query("bicyclle")

        self.assertGreaterEqual(best_term_match(typo.candidates, "bicycle"), 0.80)
        self.assertEqual(best_term_match(("tri",), "traffic"), 0.0)

    def test_recovers_common_unfinished_telex(self):
        analysis = analyze_query("nguowif ddi xe ddapj")

        self.assertIn("nguoi di xe dap", analysis.candidates)
        self.assertIn("xe dap", analysis.candidates)


if __name__ == "__main__":
    unittest.main()
