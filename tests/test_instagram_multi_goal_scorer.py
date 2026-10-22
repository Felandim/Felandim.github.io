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


def sample_insights(leader_changed=False):
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
            "leader_changed": leader_changed, "g4_in": [], "g4_out": [],
            "z4_in": [], "z4_out": [], "biggest_rise": {"teams": [], "places": 0},
            "biggest_fall": {"teams": [], "places": 0},
            "biggest_win": {"winner": "Flamengo", "home": "Bahia", "away": "Flamengo", "score": "0 x 3", "margin": 3},
        }],
    }


class MultiGoalScorerTests(unittest.TestCase):
    def setUp(self):
        self.match = {
            "url": "https://example.com/gremio-cruzeiro",
            "round": 31,
            "home": "Grêmio",
            "away": "Cruzeiro",
            "score": "2 x 4",
        }
        self.scorers = {"matches": {self.match["url"]: {
            "home": [{"name": "Atacante do Grêmio", "goals": 1}],
            "away": [
                {"name": "Kaio Jorge", "goals": 3},
                {"name": "Zagueiro rival", "goals": 1, "own_goal": True},
            ],
        }}}

    def test_detects_hat_trick_and_ignores_own_goal(self):
        spotlight = instagram_editorial.multi_goal_scorer_spotlight([self.match], self.scorers)
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "multi_goal_scorer")
        self.assertEqual(spotlight["label"], "HAT-TRICK")
        self.assertEqual(spotlight["player"], "Kaio Jorge")
        self.assertEqual(spotlight["text"], "Kaio Jorge • 3 gols pelo Cruzeiro")
        self.assertIn("Grêmio 2 x 4 Cruzeiro", spotlight["caption"])

    def test_detects_brace_and_missing_scorers_falls_back(self):
        self.scorers["matches"][self.match["url"]]["away"][0]["goals"] = 2
        spotlight = instagram_editorial.multi_goal_scorer_spotlight([self.match], self.scorers)
        self.assertEqual(spotlight["label"], "DOIS DELE")
        self.assertIn("marcou 2 vezes", spotlight["caption"])
        self.assertIsNone(instagram_editorial.multi_goal_scorer_spotlight([self.match], {"matches": {}}))

    def test_player_story_beats_goal_fest_but_not_a_new_leader(self):
        other = {"round": 31, "home": "Flamengo", "away": "Bahia", "score": "1 x 0"}
        matches = [self.match, other]
        spotlight = instagram_editorial.editorial_spotlight(sample_insights(), matches, self.scorers)
        self.assertEqual(spotlight["kind"], "multi_goal_scorer")
        leader = instagram_editorial.editorial_spotlight(sample_insights(leader_changed=True), matches, self.scorers)
        self.assertEqual(leader["kind"], "leader")

    def test_caption_question_and_schedule_use_player_context(self):
        spotlight = instagram_schedule.block_spotlight(
            sample_insights(), {"matches": [self.match], "round": 31}, self.scorers
        )
        caption = instagram_editorial.build_caption(sample_insights(), [self.match], self.scorers)
        self.assertEqual(spotlight["kind"], "multi_goal_scorer")
        self.assertTrue(caption.startswith("Hat-trick: Kaio Jorge marcou 3 vezes"))
        self.assertEqual(instagram_engagement.engagement_question(spotlight), "Kaio Jorge repete a dose na próxima rodada?")
        self.assertLessEqual(len(caption), 2200)

    def test_real_round_31_data_finds_kaio_jorge(self):
        matches = [
            match for match in json.loads((ROOT / "data/serie_a_2026.json").read_text(encoding="utf-8"))["matches"]
            if int(match["round"]) == 31
        ]
        spotlight = instagram_editorial.multi_goal_scorer_spotlight(matches, instagram_daily.load_scorers())
        self.assertIsNotNone(spotlight)
        self.assertEqual((spotlight["player"], spotlight["goals"], spotlight["team"]), ("Kaio Jorge", 3, "Cruzeiro"))

    def test_zero_gap_hook_uses_natural_copy(self):
        data = sample_insights()
        data["snapshots"][-1]["table"][3]["points"] = 51
        data["snapshots"][-1]["table"][4]["points"] = 51
        self.assertEqual(instagram_daily.table_hook(data), "4º e 5º estão empatados em pontos")


if __name__ == "__main__":
    unittest.main()
