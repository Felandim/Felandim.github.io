import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement
import instagram_schedule


def sample_insights(current_pedro=21, previous_pedro=19):
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
        "snapshots": [{"round": 31, "table": table}, {"round": 32, "table": table}],
        "rounds": [{
            "round": 32, "matches": 10, "goals": 20, "leader": "Flamengo",
            "leader_changed": False, "g4_in": [], "g4_out": [], "z4_in": [], "z4_out": [],
            "biggest_rise": {"teams": [], "places": 0}, "biggest_fall": {"teams": [], "places": 0},
            "biggest_win": {"winner": "Flamengo", "home": "Flamengo", "away": "Bahia", "score": "1 x 0", "margin": 1},
        }],
        "scorers": [
            {"round": 31, "ranking": [
                {"name": "Viveros", "team": "Athletico-PR", "goals": 21},
                {"name": "Pedro", "team": "Flamengo", "goals": previous_pedro},
            ]},
            {"round": 32, "ranking": sorted([
                {"name": "Viveros", "team": "Athletico-PR", "goals": 21},
                {"name": "Pedro", "team": "Flamengo", "goals": current_pedro},
            ], key=lambda row: (-row["goals"], row["name"]))},
        ],
    }


class ScorerRaceTests(unittest.TestCase):
    def setUp(self):
        self.match = {
            "url": "https://example.com/flamengo-bahia", "round": 32,
            "home": "Flamengo", "away": "Bahia", "score": "1 x 0",
        }
        self.scorers = {"matches": {self.match["url"]: {
            "home": [{"name": "Pedro", "goals": 1}], "away": [],
        }}}

    def test_detects_new_tie_at_top_of_scorer_race(self):
        spotlight = instagram_editorial.scorer_race_spotlight(
            sample_insights(current_pedro=21, previous_pedro=20), [self.match], self.scorers
        )
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "scorer_race")
        self.assertEqual(spotlight["label"], "ARTILHARIA EMPATADA")
        self.assertEqual(spotlight["rivals"], ["Viveros"])
        self.assertIn("mesma marca de Viveros", spotlight["caption"])

    def test_detects_scorer_one_goal_from_lead(self):
        spotlight = instagram_editorial.scorer_race_spotlight(
            sample_insights(current_pedro=20, previous_pedro=19), [self.match], self.scorers
        )
        self.assertEqual(spotlight["label"], "NA COLA DO ARTILHEIRO")
        self.assertEqual(spotlight["gap"], 1)
        self.assertIn("ficou a um de Viveros", spotlight["caption"])

    def test_new_sole_leader_names_closest_challenger(self):
        spotlight = instagram_editorial.scorer_race_spotlight(
            sample_insights(current_pedro=22, previous_pedro=20), [self.match], self.scorers
        )
        self.assertEqual(spotlight["label"], "NOVO ARTILHEIRO")
        self.assertEqual(spotlight["rivals"], ["Viveros"])
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Quem termina como artilheiro: Pedro ou Viveros?",
        )

    def test_ignores_own_goal_and_players_outside_the_race(self):
        self.scorers["matches"][self.match["url"]]["home"][0]["own_goal"] = True
        self.assertIsNone(instagram_editorial.scorer_race_spotlight(sample_insights(), [self.match], self.scorers))
        self.scorers["matches"][self.match["url"]]["home"] = [{"name": "Reserva", "goals": 1}]
        self.assertIsNone(instagram_editorial.scorer_race_spotlight(sample_insights(), [self.match], self.scorers))

    def test_single_match_block_uses_race_copy_and_question(self):
        insights = sample_insights(current_pedro=20, previous_pedro=19)
        block = {"matches": [self.match], "round": 32}
        spotlight = instagram_schedule.block_spotlight(insights, block, self.scorers)
        self.assertEqual(spotlight["kind"], "scorer_race")
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Quem termina como artilheiro: Pedro ou Viveros?",
        )

    def test_multi_goal_story_keeps_priority(self):
        self.match["score"] = "2 x 0"
        self.scorers["matches"][self.match["url"]]["home"][0]["goals"] = 2
        spotlight = instagram_editorial.editorial_spotlight(sample_insights(), [self.match], self.scorers)
        self.assertEqual(spotlight["kind"], "multi_goal_scorer")


if __name__ == "__main__":
    unittest.main()
