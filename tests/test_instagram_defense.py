import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

editorial_spec = importlib.util.spec_from_file_location("instagram_editorial", SCRIPTS / "instagram_editorial.py")
instagram_editorial = importlib.util.module_from_spec(editorial_spec)
assert editorial_spec.loader is not None
editorial_spec.loader.exec_module(instagram_editorial)

engagement_spec = importlib.util.spec_from_file_location("instagram_engagement", SCRIPTS / "instagram_engagement.py")
instagram_engagement = importlib.util.module_from_spec(engagement_spec)
assert engagement_spec.loader is not None
engagement_spec.loader.exec_module(instagram_engagement)


def defensive_insights(points_gain=7, goals_against_gain=0):
    teams = [
        "Palmeiras", "Flamengo", "Bahia", "São Paulo", "Corinthians", "Santos",
        "Botafogo", "Cruzeiro", "Fluminense", "Grêmio", "Atlético-MG", "Athletico-PR",
        "Bragantino", "Internacional", "Mirassol", "Vitória", "Vasco", "Coritiba",
        "Chapecoense", "Remo",
    ]

    def table(round_offset):
        rows = []
        for index, team in enumerate(teams):
            base_points = 55 - index * 3
            points = base_points + round_offset * 2
            ga = 20 + index + round_offset
            if team == "Palmeiras":
                points = 55 + (points_gain if round_offset == 3 else round(round_offset * points_gain / 3))
                ga = 18 + (goals_against_gain if round_offset == 3 else 0)
            rows.append({
                "team": team,
                "points": points,
                "position": index + 1,
                "ga": ga,
            })
        return rows

    return {
        "season": 2026,
        "snapshots": [
            {"round": 21, "table": table(0)},
            {"round": 22, "table": table(1)},
            {"round": 23, "table": table(2)},
            {"round": 24, "table": table(3)},
        ],
        "rounds": [{
            "round": 24,
            "matches": 10,
            "goals": 21,
            "leader": "Palmeiras",
            "leader_changed": False,
            "g4_in": [], "g4_out": [], "z4_in": [], "z4_out": [],
            "biggest_rise": {"teams": [], "places": 0},
            "biggest_fall": {"teams": [], "places": 0},
            "biggest_win": {"winner": "Empate", "home": "", "away": "", "score": "", "margin": 0},
        }],
    }


class InstagramDefenseTests(unittest.TestCase):
    def test_detects_three_round_defensive_streak_with_results(self):
        spotlight = instagram_editorial.defensive_streak_spotlight(defensive_insights())
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "defensive_streak")
        self.assertEqual(spotlight["team"], "Palmeiras")
        self.assertEqual(spotlight["points"], 7)
        self.assertEqual(spotlight["text"], "Palmeiras • 3 rodadas sem sofrer gol • 7 pts")

    def test_requires_clean_sheet_and_at_least_seven_points(self):
        self.assertIsNone(instagram_editorial.defensive_streak_spotlight(
            defensive_insights(goals_against_gain=1)
        ))
        self.assertIsNone(instagram_editorial.defensive_streak_spotlight(
            defensive_insights(points_gain=6)
        ))

    def test_editorial_uses_streak_as_fallback_not_over_strong_event(self):
        generic = {"kind": "goals", "label": "NÚMERO DA RODADA", "text": "21 gols", "caption": ""}
        with patch.object(instagram_editorial.instagram_matchday, "matchday_spotlight", return_value=generic):
            spotlight = instagram_editorial.editorial_spotlight(defensive_insights(), [])
        self.assertEqual(spotlight["kind"], "defensive_streak")

        strong = {"kind": "leader", "label": "NOVO LÍDER", "text": "Palmeiras assumiu a ponta", "caption": ""}
        with patch.object(instagram_editorial.instagram_matchday, "matchday_spotlight", return_value=strong):
            spotlight = instagram_editorial.editorial_spotlight(defensive_insights(), [])
        self.assertEqual(spotlight["kind"], "leader")

    def test_defensive_streak_has_contextual_engagement_question(self):
        spotlight = instagram_editorial.defensive_streak_spotlight(defensive_insights())
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Quem consegue furar a defesa do Palmeiras?",
        )


if __name__ == "__main__":
    unittest.main()
