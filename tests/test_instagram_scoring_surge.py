import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement


def data(current_goals=34, current_matches=10):
    history = [
        {"round": 19, "matches": 10, "goals": 23},
        {"round": 20, "matches": 10, "goals": 25},
        {"round": 21, "matches": 10, "goals": 24},
        {"round": 22, "matches": 10, "goals": 26},
        {"round": 23, "matches": 10, "goals": 22},
    ]
    current = {"round": 24, "matches": current_matches, "goals": current_goals}
    return {"rounds": history + [current]}


class ScoringSurgeTests(unittest.TestCase):
    def test_detects_round_well_above_recent_scoring_rate(self):
        spotlight = instagram_editorial.scoring_surge_spotlight(data())
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "scoring_surge")
        self.assertEqual(spotlight["label"], "RODADA OFENSIVA")
        self.assertIn("3.4 gols/jogo", spotlight["text"])
        self.assertGreaterEqual(spotlight["lift"], 0.35)

    def test_requires_enough_current_matches(self):
        self.assertIsNone(instagram_editorial.scoring_surge_spotlight(data(18, 4)))

    def test_ignores_normal_scoring_round(self):
        self.assertIsNone(instagram_editorial.scoring_surge_spotlight(data(26, 10)))

    def test_engagement_question_is_contextual(self):
        spotlight = instagram_editorial.scoring_surge_spotlight(data())
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Esse ritmo de gols se mantém até o fim da rodada?",
        )


if __name__ == "__main__":
    unittest.main()
