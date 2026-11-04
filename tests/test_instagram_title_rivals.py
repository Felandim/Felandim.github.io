import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement


def sample_insights(gap=3, leader_changed=False):
    teams = ["Flamengo", "Palmeiras"] + [f"Time {number}" for number in range(3, 21)]
    table = [
        {"team": team, "position": position, "points": 73 - (gap if position == 2 else position - 1)}
        for position, team in enumerate(teams, start=1)
    ]
    table[0]["points"] = 73
    table[1]["points"] = 73 - gap
    return {
        "season": 2026,
        "snapshots": [{"round": 34, "table": table}],
        "rounds": [{
            "round": 34,
            "matches": 8,
            "goals": 19,
            "leader": "Flamengo",
            "leader_changed": leader_changed,
            "g4_in": [], "g4_out": [], "z4_in": [], "z4_out": [],
            "biggest_win": None,
        }],
        "team_profiles": {},
    }


MATCHES = [
    {"round": 34, "home": "Flamengo", "away": "Grêmio", "score": "2 x 0"},
    {"round": 34, "home": "Palmeiras", "away": "Remo", "score": "1 x 0"},
]


class InstagramTitleRivalsTests(unittest.TestCase):
    def test_detects_wins_by_leader_and_runner_up(self):
        spotlight = instagram_editorial.title_rivals_win_spotlight(sample_insights(), MATCHES)

        self.assertEqual(spotlight["kind"], "title_rivals_win")
        self.assertEqual(spotlight["label"], "CORRIDA ACESA")
        self.assertEqual(spotlight["leader"], "Flamengo")
        self.assertEqual(spotlight["runner_up"], "Palmeiras")
        self.assertIn("3 pontos separam os dois", spotlight["text"])
        self.assertIn("Flamengo 2 x 0 Grêmio", spotlight["caption"])
        self.assertIn("Palmeiras 1 x 0 Remo", spotlight["caption"])

    def test_handles_points_tie_naturally(self):
        spotlight = instagram_editorial.title_rivals_win_spotlight(sample_insights(gap=0), MATCHES)

        self.assertIn("seguem empatados em pontos", spotlight["text"])
        self.assertNotIn("0 pontos", spotlight["text"])

    def test_requires_both_wins_and_a_close_race(self):
        one_draw = [MATCHES[0], {**MATCHES[1], "score": "1 x 1"}]
        self.assertIsNone(instagram_editorial.title_rivals_win_spotlight(sample_insights(), one_draw))
        self.assertIsNone(instagram_editorial.title_rivals_win_spotlight(sample_insights(gap=7), MATCHES))

    def test_major_table_event_keeps_priority(self):
        spotlight = instagram_editorial.editorial_spotlight(
            sample_insights(leader_changed=True), MATCHES
        )
        self.assertEqual(spotlight["kind"], "leader")

    def test_editorial_priority_and_question_create_a_two_team_story(self):
        generic = {"kind": "form", "label": "FORMA", "text": "", "caption": ""}
        with (
            patch.object(instagram_editorial.instagram_matchday, "matchday_spotlight", return_value=generic),
            patch.object(instagram_editorial, "derby_day_spotlight", return_value=None),
            patch.object(instagram_editorial, "multi_goal_scorer_spotlight", return_value=None),
            patch.object(instagram_editorial, "collective_attack_spotlight", return_value=None),
            patch.object(instagram_editorial, "rout_wave_spotlight", return_value=None),
            patch.object(instagram_editorial, "high_scoring_match_spotlight", return_value=None),
        ):
            spotlight = instagram_editorial.editorial_spotlight(sample_insights(), MATCHES)

        self.assertEqual(spotlight["kind"], "title_rivals_win")
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Quem chega mais forte à próxima rodada: Flamengo ou Palmeiras?",
        )


if __name__ == "__main__":
    unittest.main()
