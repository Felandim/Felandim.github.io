import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_daily
import instagram_editorial
import instagram_engagement
import instagram_schedule


def sample_insights():
    teams = [
        "Flamengo", "Palmeiras", "Cruzeiro", "Athletico-PR", "Fluminense",
        "Atlético-MG", "Bahia", "Botafogo", "Bragantino", "Chapecoense",
        "Corinthians", "Coritiba", "Grêmio", "Internacional", "Mirassol",
        "Remo", "Santos", "São Paulo", "Vasco", "Vitória",
    ]
    table = [
        {"team": team, "position": index, "points": 70 - index, "wins": 20 - index // 4,
         "gd": 30 - index, "gf": 50 - index, "ga": 20 + index}
        for index, team in enumerate(teams, 1)
    ]
    return {
        "season": 2026,
        "snapshots": [{"round": 30, "table": table}, {"round": 31, "table": table}],
        "rounds": [{
            "round": 31, "matches": 10, "goals": 23, "leader": "Flamengo",
            "leader_changed": False, "g4_in": [], "g4_out": [], "z4_in": [], "z4_out": [],
            "biggest_rise": {"teams": [], "places": 0},
            "biggest_fall": {"teams": [], "places": 0},
            "biggest_win": {"winner": "Flamengo", "home": "Bahia", "away": "Flamengo", "score": "0 x 3", "margin": 3},
        }],
    }


class CollectiveAttackTests(unittest.TestCase):
    def setUp(self):
        self.match = {
            "url": "https://example.com/bahia-flamengo",
            "round": 31,
            "home": "Bahia",
            "away": "Flamengo",
            "score": "0 x 3",
        }
        self.scorers = {"matches": {self.match["url"]: {
            "home": [],
            "away": [
                {"name": "Lucas Paquetá", "goals": 1},
                {"name": "Plata", "goals": 1},
                {"name": "Jorginho", "goals": 1},
            ],
        }}}

    def test_detects_three_distinct_scorers(self):
        spotlight = instagram_editorial.collective_attack_spotlight([self.match], self.scorers)
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "collective_attack")
        self.assertEqual(spotlight["label"], "ATAQUE COLETIVO")
        self.assertEqual(spotlight["text"], "Flamengo • 3 gols, 3 autores")
        self.assertEqual(spotlight["scorers"], ["Lucas Paquetá", "Plata", "Jorginho"])
        self.assertIn("Lucas Paquetá, Plata e Jorginho marcaram pelo Flamengo", spotlight["caption"])

    def test_ignores_own_goals_duplicates_and_incomplete_coverage(self):
        scorers = self.scorers["matches"][self.match["url"]]["away"]
        scorers.extend([
            {"name": "Plata", "goals": 1},
            {"name": "Gol contra", "goals": 1, "own_goal": True},
        ])
        spotlight = instagram_editorial.collective_attack_spotlight([self.match], self.scorers)
        self.assertEqual(spotlight["scorer_count"], 3)
        self.scorers["matches"][self.match["url"]]["away"] = scorers[:2]
        self.assertIsNone(instagram_editorial.collective_attack_spotlight([self.match], self.scorers))

    def test_multi_goal_player_keeps_priority(self):
        self.match["score"] = "0 x 4"
        self.scorers["matches"][self.match["url"]]["away"][0]["goals"] = 2
        spotlight = instagram_editorial.editorial_spotlight(sample_insights(), [self.match], self.scorers)
        self.assertEqual(spotlight["kind"], "multi_goal_scorer")

    def test_schedule_caption_and_question_use_collective_context(self):
        spotlight = instagram_schedule.block_spotlight(
            sample_insights(), {"matches": [self.match], "round": 31}, self.scorers
        )
        caption = instagram_editorial.build_caption(sample_insights(), [self.match], self.scorers)
        self.assertEqual(spotlight["kind"], "collective_attack")
        self.assertTrue(caption.startswith("Ataque coletivo: Lucas Paquetá, Plata e Jorginho"))
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Qual desses nomes pode decidir de novo pelo Flamengo: Lucas Paquetá, Plata ou Jorginho?",
        )
        self.assertLessEqual(len(caption), 2200)

    def test_real_round_31_data_finds_flamengo(self):
        matches = json.loads((ROOT / "data/serie_a_2026.json").read_text(encoding="utf-8"))["matches"]
        match = next(item for item in matches if int(item["round"]) == 31 and item["home"] == "Bahia")
        spotlight = instagram_editorial.collective_attack_spotlight([match], instagram_daily.load_scorers())
        self.assertIsNotNone(spotlight)
        self.assertEqual((spotlight["team"], spotlight["team_goals"], spotlight["scorer_count"]), ("Flamengo", 3, 3))


if __name__ == "__main__":
    unittest.main()
