import unittest
import pandas as pd

from scoring import compute_media_baselines, global_score, genre_score, score_title


class ScoringTests(unittest.TestCase):
    def test_threshold_uses_upper_quartile_not_one_vote_lower_quartile(self):
        data = pd.DataFrame({"rating": [6.0]*8,
                             "vote_count": [1, 1, 1, 2, 5, 9, 9, 100],
                             "genres": ["Drama"]*8})
        self.assertEqual(compute_media_baselines(data)["m"], 9)

    def test_one_vote_is_shrunk_and_large_vote_score_approaches_rating(self):
        self.assertAlmostEqual(global_score(10, 1, 6.3804, 9), 6.74236)
        self.assertAlmostEqual(global_score(8, 1000, 6.3804, 9), 7.9855536174)
        self.assertAlmostEqual(genre_score(6, 5, 6.3804, 9, 6), 6.3804)

    def test_live_scoring_uses_same_media_threshold_and_handles_unrated(self):
        baseline = {"movie": {"C": 6.3804, "m": 9, "genres": {}}}
        title = {"media_type": "movie", "rating": 10, "vote_count": 1, "genres": "Unknown"}
        result = score_title(title, baseline)
        self.assertEqual(result["global_score"], 6.7424)
        self.assertTrue(result["genre_fallback"])
        self.assertEqual(score_title({**title, "vote_count": 0}, baseline)["score_status"], "unrated")


if __name__ == "__main__":
    unittest.main()
