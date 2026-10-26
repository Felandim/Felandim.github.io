import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement
import instagram_schedule


def sample_insights(previous_score="2 x 0", previous_result="D"):
    return {
        "team_profiles": {
            "internacional": {
                "team": "Internacional",
                "current": {"position": 16},
                "last_five": [
                    {
                        "round": 31,
                        "opponent": "Mirassol",
                        "venue": "Fora",
                        "score": previous_score,
                        "result": previous_result,
                    },
                    {
                        "round": 32,
                        "opponent": "Botafogo",
                        "venue": "Casa",
                        "score": "3 x 0",
                        "result": "V",
                    },
                ],
            }
        },
        "snapshots": [{"table": []}],
    }


def current_match(score="3 x 0"):
    return {
        "round": 32,
        "home": "Internacional",
        "away": "Botafogo",
        "score": score,
    }


class BounceBackSpotlightTests(unittest.TestCase):
    def test_highlights_clear_rebound_in_team_score_order(self):
        spotlight = instagram_editorial.bounce_back_spotlight(
            sample_insights(), [current_match()]
        )

        self.assertEqual(spotlight["kind"], "bounce_back")
        self.assertEqual(spotlight["label"], "RESPOSTA IMEDIATA")
        self.assertEqual(spotlight["text"], "Internacional • de 0 x 2 para 3 x 0")
        self.assertIn("Mirassol", spotlight["caption"])
        self.assertIn("Botafogo", spotlight["caption"])

    def test_ignores_narrow_previous_defeat(self):
        self.assertIsNone(
            instagram_editorial.bounce_back_spotlight(
                sample_insights(previous_score="1 x 0"), [current_match()]
            )
        )

    def test_ignores_narrow_current_win(self):
        self.assertIsNone(
            instagram_editorial.bounce_back_spotlight(
                sample_insights(), [current_match(score="1 x 0")]
            )
        )

    def test_editorial_selection_keeps_table_events_ahead(self):
        leader = {"kind": "leader", "label": "NOVO LÍDER", "text": "Palmeiras", "caption": ""}
        with patch.object(instagram_editorial.instagram_matchday, "matchday_spotlight", return_value=leader):
            spotlight = instagram_editorial.editorial_spotlight(
                sample_insights(), [current_match()]
            )

        self.assertIs(spotlight, leader)

    def test_single_match_block_uses_rebound_before_generic_impact(self):
        block = {"round": 32, "matches": [current_match()]}
        with (
            patch.object(instagram_editorial, "multi_goal_scorer_spotlight", return_value=None),
            patch.object(instagram_editorial, "collective_attack_spotlight", return_value=None),
        ):
            spotlight = instagram_schedule.block_spotlight(sample_insights(), block)

        self.assertEqual(spotlight["kind"], "bounce_back")

    def test_contextual_question_names_team(self):
        question = instagram_engagement.engagement_question(
            {"kind": "bounce_back", "team": "Internacional"}
        )
        self.assertEqual(question, "Internacional confirma a reação na próxima rodada?")


if __name__ == "__main__":
    unittest.main()
