import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement


class InstagramScoringDroughtTests(unittest.TestCase):
    def _insights(self, current_goals=8, current_matches=5):
        history = [
            {"round": round_number, "matches": 10, "goals": goals}
            for round_number, goals in enumerate((26, 28, 24, 30, 27), start=1)
        ]
        return {"rounds": history + [{"round": 6, "matches": current_matches, "goals": current_goals}]}

    def test_detects_material_scoring_drought(self):
        spotlight = instagram_editorial.scoring_drought_spotlight(self._insights())
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "scoring_drought")
        self.assertAlmostEqual(spotlight["rate"], 1.6)
        self.assertGreaterEqual(spotlight["drop"], 0.25)
        self.assertIn("RODADA TRAVADA", spotlight["label"])

    def test_ignores_small_sample_and_normal_scoring_rate(self):
        self.assertIsNone(instagram_editorial.scoring_drought_spotlight(self._insights(current_goals=4, current_matches=3)))
        self.assertIsNone(instagram_editorial.scoring_drought_spotlight(self._insights(current_goals=11, current_matches=5)))

    def test_engagement_question_is_contextual(self):
        question = instagram_engagement.engagement_question({"kind": "scoring_drought"})
        self.assertEqual(question, "A rodada destrava ou termina com cara de jogo amarrado?")


if __name__ == "__main__":
    unittest.main()
