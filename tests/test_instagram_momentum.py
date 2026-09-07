import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "instagram_matchday.py"
spec = importlib.util.spec_from_file_location("instagram_matchday", MODULE_PATH)
instagram_matchday = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(instagram_matchday)

TEAMS = [
    "Palmeiras", "Flamengo", "Bahia", "São Paulo", "Corinthians", "Santos",
    "Botafogo", "Cruzeiro", "Fluminense", "Grêmio", "Atlético-MG", "Athletico-PR",
    "Bragantino", "Internacional", "Mirassol", "Vitória", "Vasco", "Coritiba",
    "Chapecoense", "Remo",
]


def table(order):
    return [
        {"team": team, "points": 100 - index * 5, "position": index + 1}
        for index, team in enumerate(order)
    ]


def insights_with_orders(orders):
    snapshots = [{"round": 20 + i, "table": table(order)} for i, order in enumerate(orders)]
    latest_round = snapshots[-1]["round"]
    return {
        "season": 2026,
        "snapshots": snapshots,
        "rounds": [{
            "round": latest_round,
            "matches": 10,
            "goals": 24,
            "leader": snapshots[-1]["table"][0]["team"],
            "leader_changed": False,
            "g4_in": [], "g4_out": [], "z4_in": [], "z4_out": [],
            "biggest_win": None,
            "biggest_rise": {"teams": [], "places": 0},
            "biggest_fall": {"teams": [], "places": 0},
        }],
    }


class InstagramMomentumTests(unittest.TestCase):
    def test_detects_team_climbing_every_recent_round(self):
        # Corinthians: 8º -> 7º -> 6º -> 4º.
        orders = []
        for position in (8, 7, 6, 4):
            order = [team for team in TEAMS if team != "Corinthians"]
            order.insert(position - 1, "Corinthians")
            orders.append(order)

        spotlight = instagram_matchday.sustained_climb_spotlight(insights_with_orders(orders))
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "sustained_climb")
        self.assertEqual(spotlight["team"], "Corinthians")
        self.assertEqual(spotlight["gain"], 4)
        self.assertIn("8º para 4º", spotlight["caption"])

    def test_ignores_one_round_jump_without_sustained_climb(self):
        orders = []
        for position in (8, 8, 7, 4):
            order = [team for team in TEAMS if team != "Corinthians"]
            order.insert(position - 1, "Corinthians")
            orders.append(order)

        self.assertIsNone(instagram_matchday.sustained_climb_spotlight(insights_with_orders(orders)))

    def test_does_not_override_high_priority_editorial_event(self):
        orders = []
        for position in (8, 7, 6, 4):
            order = [team for team in TEAMS if team != "Corinthians"]
            order.insert(position - 1, "Corinthians")
            orders.append(order)
        data = insights_with_orders(orders)
        data["rounds"][-1]["leader_changed"] = True

        spotlight = instagram_matchday.matchday_spotlight(data, [])
        self.assertEqual(spotlight["kind"], "leader")

    def test_caption_includes_sustained_climb_context(self):
        orders = []
        for position in (8, 7, 6, 4):
            order = [team for team in TEAMS if team != "Corinthians"]
            order.insert(position - 1, "Corinthians")
            orders.append(order)

        caption = instagram_matchday.build_caption(insights_with_orders(orders), [])
        self.assertIn("Arrancada na tabela:", caption)
        self.assertLessEqual(len(caption), 2200)


if __name__ == "__main__":
    unittest.main()
