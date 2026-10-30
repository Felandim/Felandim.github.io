import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement
import instagram_schedule


def profile(team, unbeaten, wins, position, points):
    return {
        "team": team,
        "current": {"position": position, "points": points},
        "streaks": {"current_unbeaten": unbeaten, "current_wins": wins},
    }


def sample_insights(leader_changed=False):
    table = [
        {"team": name, "position": index + 1, "points": 73 - index}
        for index, name in enumerate([
            "Flamengo", "Palmeiras", "Cruzeiro", "Fluminense", "Athletico-PR",
            "Bahia", "São Paulo", "Botafogo", "Grêmio", "Bragantino", "Santos",
            "Atlético-MG", "Mirassol", "Vasco", "Vitória", "Coritiba",
            "Internacional", "Corinthians", "Remo", "Chapecoense",
        ])
    ]
    return {
        "season": 2026,
        "team_profiles": {
            "flamengo": profile("Flamengo", 9, 4, 1, 73),
            "palmeiras": profile("Palmeiras", 10, 0, 2, 70),
            "cruzeiro": profile("Cruzeiro", 4, 3, 3, 57),
            "gremio": profile("Grêmio", 5, 5, 9, 45),
        },
        "snapshots": [{"round": 33, "table": table}],
        "rounds": [{
            "round": 33,
            "matches": 9,
            "goals": 23,
            "leader": "Flamengo",
            "leader_changed": leader_changed,
            "g4_in": [],
            "g4_out": [],
            "z4_in": [],
            "z4_out": [],
            "biggest_win": None,
        }],
    }


class InstagramUnbeatenRunTests(unittest.TestCase):
    def test_detects_longest_run_renewed_without_a_loss(self):
        matches = [
            {"home": "Santos", "away": "Palmeiras", "score": "0 x 0"},
            {"home": "Vasco", "away": "Flamengo", "score": "1 x 4"},
        ]

        spotlight = instagram_editorial.unbeaten_run_spotlight(sample_insights(), matches)

        self.assertEqual(spotlight["kind"], "unbeaten_run")
        self.assertEqual(spotlight["label"], "SÉRIE INVICTA")
        self.assertEqual(spotlight["team"], "Palmeiras")
        self.assertEqual(spotlight["unbeaten_matches"], 10)
        self.assertIn("10 jogos sem perder", spotlight["text"])
        self.assertIn("2º lugar, com 70 pontos", spotlight["caption"])

    def test_ignores_loss_short_run_and_pure_winning_streak(self):
        self.assertIsNone(instagram_editorial.unbeaten_run_spotlight(
            sample_insights(), [{"home": "Palmeiras", "away": "Santos", "score": "0 x 1"}]
        ))
        self.assertIsNone(instagram_editorial.unbeaten_run_spotlight(
            sample_insights(), [{"home": "Cruzeiro", "away": "Bahia", "score": "1 x 0"}]
        ))
        self.assertIsNone(instagram_editorial.unbeaten_run_spotlight(
            sample_insights(), [{"home": "Grêmio", "away": "Bahia", "score": "2 x 0"}]
        ))

    def test_major_table_event_keeps_priority(self):
        matches = [{"round": 33, "home": "Vasco", "away": "Flamengo", "score": "1 x 4"}]
        spotlight = instagram_editorial.editorial_spotlight(
            sample_insights(leader_changed=True), matches
        )
        self.assertEqual(spotlight["kind"], "leader")

    def test_single_match_block_uses_unbeaten_story_before_generic_impact(self):
        match = {"round": 33, "home": "Vasco", "away": "Flamengo", "score": "1 x 4"}
        block = {"round": 33, "matches": [match]}
        with (
            patch.object(instagram_editorial, "multi_goal_scorer_spotlight", return_value=None),
            patch.object(instagram_editorial, "collective_attack_spotlight", return_value=None),
            patch.object(instagram_editorial, "bounce_back_spotlight", return_value=None),
            patch.object(instagram_editorial, "winless_run_ended_spotlight", return_value=None),
        ):
            spotlight = instagram_schedule.block_spotlight(sample_insights(), block)

        self.assertEqual(spotlight["kind"], "unbeaten_run")
        self.assertEqual(spotlight["team"], "Flamengo")

    def test_editorial_and_question_turn_run_into_a_team_story(self):
        matches = [
            {"round": 33, "home": "Santos", "away": "Palmeiras", "score": "0 x 0"},
            {"round": 33, "home": "Bahia", "away": "São Paulo", "score": "1 x 0"},
        ]
        with patch.object(
            instagram_editorial.instagram_matchday,
            "matchday_spotlight",
            return_value={"kind": "form", "label": "FORMA", "text": "", "caption": ""},
        ):
            spotlight = instagram_editorial.editorial_spotlight(sample_insights(), matches)

        self.assertEqual(spotlight["kind"], "unbeaten_run")
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Quem encerra a invencibilidade do Palmeiras?",
        )


if __name__ == "__main__":
    unittest.main()
