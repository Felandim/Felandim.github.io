import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "instagram_daily.py"
spec = importlib.util.spec_from_file_location("instagram_daily", MODULE_PATH)
instagram_daily = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(instagram_daily)


def sample_insights():
    teams = [
        "Palmeiras", "Flamengo", "Bahia", "São Paulo", "Corinthians",
        "Santos", "Botafogo", "Cruzeiro", "Fluminense", "Grêmio",
        "Atlético-MG", "Athletico-PR", "Bragantino", "Internacional",
        "Mirassol", "Vitória", "Vasco", "Coritiba", "Chapecoense", "Remo",
    ]
    points = [55, 50, 46, 44, 43, 42, 41, 35, 34, 33, 32, 31, 30, 29, 28, 25, 20, 17, 14, 11]
    table = [
        {"team": team, "points": point, "position": index + 1}
        for index, (team, point) in enumerate(zip(teams, points))
    ]
    return {
        "season": 2026,
        "snapshots": [{"round": 24, "table": table}],
        "rounds": [{
            "round": 24,
            "matches": 10,
            "goals": 25,
            "leader": "Palmeiras",
            "leader_changed": False,
            "g4_in": [], "g4_out": [], "z4_in": [], "z4_out": [],
            "biggest_rise": {"teams": [], "places": 0},
            "biggest_fall": {"teams": [], "places": 0},
            "biggest_win": None,
        }],
    }


class InstagramClusterTests(unittest.TestCase):
    def test_boundary_cluster_detects_crowded_g4_battle(self):
        cluster = instagram_daily.boundary_cluster(sample_insights())
        self.assertIsNotNone(cluster)
        self.assertEqual(cluster["kind"], "g4_cluster")
        self.assertEqual(cluster["count"], 4)
        self.assertEqual(cluster["spread"], 3)
        self.assertEqual(cluster["label"], "G4 EMBOLADO")

    def test_cluster_is_spotlight_before_individual_pressure(self):
        spotlight = instagram_daily.round_spotlight(sample_insights())
        self.assertEqual(spotlight["kind"], "g4_cluster")
        self.assertEqual(spotlight["text"], "4 times em até 3 pontos do 4º")

    def test_caption_explains_crowded_battle(self):
        caption = instagram_daily.build_caption(sample_insights())
        self.assertIn("G4 embolado: 4 times estão em uma faixa de 3 pontos a partir do 4º colocado.", caption)


if __name__ == "__main__":
    unittest.main()
