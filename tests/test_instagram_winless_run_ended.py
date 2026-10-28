import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement
import instagram_schedule


def sample_insights(results=("V", "E", "D", "E", "V")):
    games = []
    for round_number, result in zip(range(28, 33), results):
        games.append({
            "round": round_number,
            "opponent": "Rival" if round_number < 32 else "Botafogo",
            "venue": "Casa",
            "score": "1 x 1" if result == "E" else "0 x 1" if result == "D" else "1 x 0",
            "result": result,
        })
    return {
        "team_profiles": {
            "internacional": {
                "team": "Internacional",
                "current": {"position": 16},
                "last_five": games,
            }
        },
        "snapshots": [{"table": []}],
    }


def current_match():
    return {"round": 32, "home": "Internacional", "away": "Botafogo", "score": "3 x 0"}


class WinlessRunEndedSpotlightTests(unittest.TestCase):
    def test_detects_exact_three_match_drought_ended_by_win(self):
        spotlight = instagram_editorial.winless_run_ended_spotlight(
            sample_insights(), [current_match()]
        )

        self.assertEqual(spotlight["kind"], "winless_run_ended")
        self.assertEqual(spotlight["label"], "FIM DO JEJUM")
        self.assertEqual(spotlight["winless_matches"], 3)
        self.assertFalse(spotlight["at_least"])
        self.assertEqual(
            spotlight["text"],
            "Internacional • venceu após 3 jogos sem vitória",
        )
        self.assertIn("bateu o Botafogo por 3 x 0", spotlight["caption"])

    def test_uses_honest_lower_bound_when_older_win_is_outside_window(self):
        spotlight = instagram_editorial.winless_run_ended_spotlight(
            sample_insights(("E", "D", "E", "D", "V")), [current_match()]
        )

        self.assertEqual(spotlight["winless_matches"], 4)
        self.assertTrue(spotlight["at_least"])
        self.assertIn("pelo menos 4 jogos", spotlight["text"])
        self.assertIn("pelo menos 4 jogos", spotlight["caption"])

    def test_ignores_short_drought_and_profile_without_current_win(self):
        self.assertIsNone(
            instagram_editorial.winless_run_ended_spotlight(
                sample_insights(("D", "V", "E", "D", "V")), [current_match()]
            )
        )
        self.assertIsNone(
            instagram_editorial.winless_run_ended_spotlight(
                sample_insights(("V", "E", "D", "E", "E")), [current_match()]
            )
        )

    def test_major_table_event_keeps_priority(self):
        leader = {"kind": "leader", "label": "NOVO LÍDER", "text": "Palmeiras", "caption": ""}
        with patch.object(
            instagram_editorial.instagram_matchday,
            "matchday_spotlight",
            return_value=leader,
        ):
            spotlight = instagram_editorial.editorial_spotlight(
                sample_insights(), [current_match()]
            )

        self.assertIs(spotlight, leader)

    def test_single_match_block_uses_drought_story_before_generic_impact(self):
        block = {"round": 32, "matches": [current_match()]}
        with (
            patch.object(instagram_editorial, "multi_goal_scorer_spotlight", return_value=None),
            patch.object(instagram_editorial, "collective_attack_spotlight", return_value=None),
            patch.object(instagram_editorial, "bounce_back_spotlight", return_value=None),
        ):
            spotlight = instagram_schedule.block_spotlight(sample_insights(), block)

        self.assertEqual(spotlight["kind"], "winless_run_ended")

    def test_contextual_question_names_team(self):
        question = instagram_engagement.engagement_question({
            "kind": "winless_run_ended",
            "team": "Internacional",
        })
        self.assertEqual(question, "Essa vitória vira a chave do Internacional?")


if __name__ == "__main__":
    unittest.main()
