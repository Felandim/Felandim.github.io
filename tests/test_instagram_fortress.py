import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement
import instagram_schedule


def sample_insights(points=18, wins=6):
    return {
        "team_profiles": {
            "forte": {
                "team": "Forte FC",
                "home": {"played": 9, "points": points, "wins": wins},
                "last_five": [{
                    "round": 35,
                    "opponent": "Visitante",
                    "venue": "Casa",
                    "score": "1 x 2",
                    "result": "D",
                }],
            }
        },
        "snapshots": [{"table": []}],
    }


def away_win(score="1 x 2"):
    return {
        "round": 35,
        "home": "Forte FC",
        "away": "Visitante",
        "score": score,
    }


class FortressBreachedSpotlightTests(unittest.TestCase):
    def test_highlights_away_win_against_strong_home_record(self):
        spotlight = instagram_editorial.fortress_breached_spotlight(
            sample_insights(), [away_win()]
        )

        self.assertEqual(spotlight["kind"], "fortress_breached")
        self.assertEqual(spotlight["label"], "FORTALEZA INVADIDA")
        self.assertEqual(spotlight["winner"], "Visitante")
        self.assertEqual(spotlight["home_ppg"], 2.25)
        self.assertIn("6 vitórias em 8 jogos em casa", spotlight["text"])
        self.assertIn("18 pontos em 8 partidas", spotlight["caption"])

    def test_requires_away_win_and_a_genuinely_strong_prior_record(self):
        self.assertIsNone(
            instagram_editorial.fortress_breached_spotlight(
                sample_insights(), [away_win("2 x 1")]
            )
        )
        self.assertIsNone(
            instagram_editorial.fortress_breached_spotlight(
                sample_insights(points=14, wins=5), [away_win()]
            )
        )

    def test_editorial_selection_keeps_table_events_ahead(self):
        leader = {"kind": "leader", "label": "NOVO LÍDER", "text": "outro fato"}
        with patch.object(
            instagram_editorial.instagram_matchday,
            "matchday_spotlight",
            return_value=leader,
        ):
            spotlight = instagram_editorial.editorial_spotlight(
                sample_insights(), [away_win()]
            )
        self.assertIs(spotlight, leader)

    def test_single_match_block_uses_fortress_story_before_generic_impact(self):
        block = {"round": 35, "matches": [away_win()]}
        with (
            patch.object(instagram_editorial, "multi_goal_scorer_spotlight", return_value=None),
            patch.object(instagram_editorial, "collective_attack_spotlight", return_value=None),
            patch.object(instagram_editorial, "bounce_back_spotlight", return_value=None),
            patch.object(instagram_editorial, "winless_run_ended_spotlight", return_value=None),
            patch.object(instagram_editorial, "unbeaten_run_spotlight", return_value=None),
        ):
            spotlight = instagram_schedule.block_spotlight(sample_insights(), block)
        self.assertEqual(spotlight["kind"], "fortress_breached")

    def test_question_names_the_winning_visitor(self):
        self.assertEqual(
            instagram_engagement.engagement_question({
                "kind": "fortress_breached",
                "winner": "Visitante",
            }),
            "Essa vitória fora muda o patamar do Visitante?",
        )


if __name__ == "__main__":
    unittest.main()
