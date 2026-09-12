import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "instagram_matchday.py"
spec = importlib.util.spec_from_file_location("instagram_matchday_single", MODULE_PATH)
instagram_matchday = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(instagram_matchday)


class InstagramSingleMatchImpactTests(unittest.TestCase):
    def test_single_current_round_match_prioritizes_its_table_impact(self):
        insights = {
            "snapshots": [
                {
                    "round": 26,
                    "table": [
                        {"team": "Athletico-PR", "points": 45, "position": 3},
                        {"team": "Coritiba", "points": 30, "position": 14},
                    ],
                },
                {
                    "round": 27,
                    "table": [
                        {"team": "Athletico-PR", "points": 46, "position": 3},
                        {"team": "Coritiba", "points": 31, "position": 14},
                    ],
                },
            ],
            "rounds": [{"round": 27}],
        }
        matches = [{
            "round": 27,
            "home": "Coritiba",
            "away": "Athletico-PR",
            "score": "3 x 3",
        }]

        spotlight = instagram_matchday.matchday_spotlight(insights, matches)

        self.assertEqual(spotlight["kind"], "single_match_impact")
        self.assertEqual(spotlight["label"], "IMPACTO DO JOGO")
        self.assertEqual(spotlight["team"], "Athletico-PR")
        self.assertIn("Athletico-PR chegou a 46 pts e segue em 3º", spotlight["text"])
        self.assertIn("Coritiba 3 x 3 Athletico-PR", spotlight["caption"])

    def test_multiple_matches_do_not_trigger_single_match_rule(self):
        insights = {
            "snapshots": [
                {"round": 26, "table": []},
                {"round": 27, "table": []},
            ],
            "rounds": [{"round": 27}],
        }
        matches = [
            {"round": 27, "home": "A", "away": "B", "score": "1 x 0"},
            {"round": 27, "home": "C", "away": "D", "score": "2 x 2"},
        ]

        self.assertIsNone(instagram_matchday.single_match_impact_spotlight(insights, matches))


if __name__ == "__main__":
    unittest.main()
