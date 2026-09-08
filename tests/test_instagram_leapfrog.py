import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

matchday_spec = importlib.util.spec_from_file_location("instagram_matchday", SCRIPTS / "instagram_matchday.py")
instagram_matchday = importlib.util.module_from_spec(matchday_spec)
assert matchday_spec.loader is not None
matchday_spec.loader.exec_module(instagram_matchday)

engagement_spec = importlib.util.spec_from_file_location("instagram_engagement", SCRIPTS / "instagram_engagement.py")
instagram_engagement = importlib.util.module_from_spec(engagement_spec)
assert engagement_spec.loader is not None
engagement_spec.loader.exec_module(instagram_engagement)

TEAMS = [
    "Palmeiras", "Flamengo", "Bahia", "São Paulo", "Santos", "Corinthians",
    "Botafogo", "Cruzeiro", "Fluminense", "Grêmio", "Atlético-MG", "Athletico-PR",
    "Bragantino", "Internacional", "Mirassol", "Vitória", "Vasco", "Coritiba",
    "Chapecoense", "Remo",
]


def table(order):
    return [
        {"team": team, "points": 50 - index * 2, "position": index + 1}
        for index, team in enumerate(order)
    ]


def insights_after_leapfrog():
    previous = list(TEAMS)
    current = list(TEAMS)
    current[4], current[5] = current[5], current[4]
    return {
        "season": 2026,
        "snapshots": [
            {"round": 23, "table": table(previous)},
            {"round": 24, "table": table(current)},
        ],
        "rounds": [{
            "round": 24,
            "matches": 10,
            "goals": 22,
            "leader": "Palmeiras",
            "leader_changed": False,
            "g4_in": [], "g4_out": [], "z4_in": [], "z4_out": [],
            "biggest_rise": {"teams": ["Corinthians"], "places": 1},
            "biggest_fall": {"teams": ["Santos"], "places": 1},
            "biggest_win": None,
        }],
    }


class InstagramLeapfrogTests(unittest.TestCase):
    def test_detects_winner_that_overtakes_direct_opponent(self):
        matches = [{
            "round": 24, "home": "Corinthians", "away": "Santos", "score": "2 x 0",
        }]
        spotlight = instagram_matchday.direct_leapfrog_spotlight(insights_after_leapfrog(), matches)

        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "direct_leapfrog")
        self.assertEqual(spotlight["winner"], "Corinthians")
        self.assertEqual(spotlight["loser"], "Santos")
        self.assertEqual(spotlight["winner_from"], 6)
        self.assertEqual(spotlight["winner_to"], 5)

    def test_ignores_win_without_table_overtake(self):
        data = insights_after_leapfrog()
        data["snapshots"][-1]["table"] = table(TEAMS)
        matches = [{
            "round": 24, "home": "Corinthians", "away": "Santos", "score": "2 x 0",
        }]
        self.assertIsNone(instagram_matchday.direct_leapfrog_spotlight(data, matches))

    def test_leapfrog_replaces_generic_pressure_but_not_major_event(self):
        data = insights_after_leapfrog()
        matches = [{
            "round": 24, "home": "Corinthians", "away": "Santos", "score": "2 x 0",
        }]
        self.assertEqual(instagram_matchday.matchday_spotlight(data, matches)["kind"], "direct_leapfrog")

        data["rounds"][-1]["leader_changed"] = True
        self.assertEqual(instagram_matchday.matchday_spotlight(data, matches)["kind"], "leader")

    def test_caption_and_question_are_contextual(self):
        data = insights_after_leapfrog()
        matches = [{
            "round": 24, "home": "Corinthians", "away": "Santos", "score": "2 x 0",
        }]
        spotlight = instagram_matchday.matchday_spotlight(data, matches)
        caption = instagram_matchday.build_caption(data, matches)

        self.assertIn("Ultrapassagem direta: Corinthians começou a rodada em 6º", caption)
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Corinthians consegue se manter à frente na próxima rodada?",
        )


if __name__ == "__main__":
    unittest.main()
