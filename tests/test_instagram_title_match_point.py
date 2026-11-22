import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement


def sample_insights(leader_points=80, runner_up_points=74, round_number=36):
    teams = ["Flamengo", "Palmeiras"] + [f"Time {number:02d}" for number in range(3, 21)]
    current = []
    for position, team in enumerate(teams, 1):
        points = leader_points if position == 1 else runner_up_points if position == 2 else 70 - position
        current.append({
            "team": team,
            "position": position,
            "points": points,
            "played": 36,
        })
    previous = [{**row, "points": max(0, row["points"] - 1), "played": 35} for row in current]
    return {
        "season": 2026,
        "snapshots": [
            {"round": round_number - 1, "table": previous},
            {"round": round_number, "table": current},
        ],
        "rounds": [{"round": round_number, "matches": 3}],
    }


MATCHES = [{"round": 36, "home": "Bahia", "away": "Coritiba", "score": "0 x 1"}]


class InstagramTitleMatchPointTests(unittest.TestCase):
    def test_calculates_points_needed_without_assuming_tiebreakers(self):
        spotlight = instagram_editorial.title_match_point_spotlight(sample_insights(), MATCHES)

        self.assertEqual(spotlight["kind"], "title_match_point")
        self.assertEqual(spotlight["label"], "TÍTULO À VISTA")
        self.assertEqual(spotlight["team"], "Flamengo")
        self.assertEqual(spotlight["points_needed"], 1)
        self.assertEqual(spotlight["rival"], "Palmeiras")
        self.assertEqual(spotlight["rival_maximum"], 80)
        self.assertIn("1 ponto garante o título sem desempate", spotlight["text"])
        self.assertIn("sem depender dos critérios de desempate", spotlight["caption"])

    def test_avoids_distant_or_already_clinched_scenarios(self):
        self.assertIsNone(
            instagram_editorial.title_match_point_spotlight(
                sample_insights(leader_points=76, runner_up_points=74), MATCHES
            )
        )
        self.assertIsNone(
            instagram_editorial.title_match_point_spotlight(
                sample_insights(leader_points=81, runner_up_points=74), MATCHES
            )
        )

    def test_avoids_reusing_current_table_for_an_old_queued_block(self):
        old_matches = [{**MATCHES[0], "round": 35}]
        self.assertIsNone(
            instagram_editorial.title_match_point_spotlight(sample_insights(), old_matches)
        )

    def test_requires_enough_remaining_points_for_the_leader(self):
        data = sample_insights()
        data["snapshots"][-1]["table"][0]["played"] = 38
        self.assertIsNone(
            instagram_editorial.title_match_point_spotlight(data, MATCHES)
        )

    def test_match_point_outweighs_an_ordinary_table_event_but_not_a_clinch(self):
        with patch.object(
            instagram_editorial.instagram_matchday,
            "matchday_spotlight",
            return_value={"kind": "leader", "label": "NOVA LIDERANÇA", "text": "outro fato"},
        ), patch.object(instagram_editorial, "clinched_status_spotlight", return_value=None):
            spotlight = instagram_editorial.editorial_spotlight(sample_insights(), MATCHES)
        self.assertEqual(spotlight["kind"], "title_match_point")

        clinched = {"kind": "champion_clinched", "team": "Flamengo"}
        with patch.object(instagram_editorial, "clinched_status_spotlight", return_value=clinched):
            spotlight = instagram_editorial.editorial_spotlight(sample_insights(), MATCHES)
        self.assertIs(spotlight, clinched)

    def test_adds_a_specific_engagement_question(self):
        spotlight = instagram_editorial.title_match_point_spotlight(sample_insights(), MATCHES)
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "O Flamengo confirma o título na próxima rodada?",
        )


if __name__ == "__main__":
    unittest.main()
