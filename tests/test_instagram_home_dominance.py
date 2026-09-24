import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement


class InstagramHomeDominanceTests(unittest.TestCase):
    def test_detects_home_dominance_at_seventy_five_percent(self):
        matches = [
            {"score": "2 x 0"},
            {"score": "1 x 0"},
            {"score": "3 x 1"},
            {"score": "1 x 1"},
        ]
        spotlight = instagram_editorial.home_dominance_spotlight(matches)
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "home_dominance")
        self.assertEqual(spotlight["home_wins"], 3)
        self.assertEqual(spotlight["share"], 0.75)
        self.assertIn("75%", spotlight["text"])

    def test_ignores_small_sample_and_weaker_home_edge(self):
        self.assertIsNone(instagram_editorial.home_dominance_spotlight([
            {"score": "1 x 0"}, {"score": "2 x 0"}, {"score": "3 x 1"},
        ]))
        self.assertIsNone(instagram_editorial.home_dominance_spotlight([
            {"score": "1 x 0"}, {"score": "2 x 0"}, {"score": "1 x 1"}, {"score": "0 x 1"},
        ]))

    def test_engagement_question_is_contextual(self):
        question = instagram_engagement.engagement_question({"kind": "home_dominance"})
        self.assertEqual(question, "Na próxima rodada, quem consegue quebrar a força dos mandantes?")


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
        self.assertEqual(spotlight["label"], "RODADA TRAVADA")

    def test_ignores_small_sample_and_normal_scoring_rate(self):
        self.assertIsNone(instagram_editorial.scoring_drought_spotlight(self._insights(current_goals=4, current_matches=3)))
        self.assertIsNone(instagram_editorial.scoring_drought_spotlight(self._insights(current_goals=11, current_matches=5)))

    def test_scoring_drought_engagement_question_is_contextual(self):
        question = instagram_engagement.engagement_question({"kind": "scoring_drought"})
        self.assertEqual(question, "A rodada destrava ou termina com cara de jogo amarrado?")


if __name__ == "__main__":
    unittest.main()
