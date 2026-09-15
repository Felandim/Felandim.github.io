import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import instagram_editorial
import instagram_engagement


class InstagramAwayDominanceTests(unittest.TestCase):
    def test_detects_strong_away_win_share(self):
        matches = [
            {"score": "0 x 1"},
            {"score": "1 x 2"},
            {"score": "0 x 2"},
            {"score": "2 x 0"},
        ]
        spotlight = instagram_editorial.away_dominance_spotlight(matches)
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "away_dominance")
        self.assertEqual(spotlight["away_wins"], 3)
        self.assertEqual(spotlight["matches"], 4)
        self.assertEqual(spotlight["text"], "3 vitórias fora em 4 jogos • 75% do dia")

    def test_requires_four_matches_and_seventy_five_percent(self):
        self.assertIsNone(instagram_editorial.away_dominance_spotlight([
            {"score": "0 x 1"}, {"score": "1 x 2"}, {"score": "0 x 2"},
        ]))
        self.assertIsNone(instagram_editorial.away_dominance_spotlight([
            {"score": "0 x 1"}, {"score": "1 x 2"}, {"score": "2 x 0"}, {"score": "1 x 1"},
        ]))

    def test_goal_fest_keeps_priority_over_away_dominance(self):
        matches = [
            {"score": "2 x 4", "home": "A", "away": "B"},
            {"score": "0 x 1", "home": "C", "away": "D"},
            {"score": "1 x 2", "home": "E", "away": "F"},
            {"score": "2 x 0", "home": "G", "away": "H"},
        ]
        self.assertEqual(instagram_editorial.high_scoring_match_spotlight(matches)["kind"], "goal_fest")
        self.assertEqual(instagram_editorial.away_dominance_spotlight(matches)["kind"], "away_dominance")

    def test_engagement_question_is_contextual(self):
        spotlight = {"kind": "away_dominance"}
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Na próxima rodada, os mandantes retomam a vantagem?",
        )


if __name__ == "__main__":
    unittest.main()
