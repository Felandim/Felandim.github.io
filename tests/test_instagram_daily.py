import importlib.util
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "instagram_daily.py"
spec = importlib.util.spec_from_file_location("instagram_daily", MODULE_PATH)
instagram_daily = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(instagram_daily)


def sample_insights(matches=10, snapshots=1):
    teams = [
        "Palmeiras", "Flamengo", "Bahia", "São Paulo", "Corinthians",
        "Santos", "Botafogo", "Cruzeiro", "Fluminense", "Grêmio",
        "Atlético-MG", "Athletico-PR", "Bragantino", "Internacional",
        "Mirassol", "Vitória", "Vasco", "Coritiba", "Chapecoense", "Remo",
    ]
    latest_table = [
        {"team": team, "points": 50 - i * 2, "position": i + 1}
        for i, team in enumerate(teams)
    ]

    if snapshots >= 6:
        base_table = [dict(row) for row in latest_table]
        for row in base_table:
            row["points"] -= 8
        base_table[0]["points"] = latest_table[0]["points"] - 13
        snapshots_data = [{"round": 19, "table": base_table}]
        for round_number in range(20, 24):
            snapshots_data.append({"round": round_number, "table": base_table})
        snapshots_data.append({"round": 24, "table": latest_table})
    elif snapshots >= 2:
        previous_table = [dict(row) for row in latest_table]
        previous_table[2]["position"], previous_table[3]["position"] = 4, 3
        snapshots_data = [
            {"round": 23, "table": previous_table},
            {"round": 24, "table": latest_table},
        ]
    else:
        snapshots_data = [{"round": 24, "table": latest_table}]

    return {
        "season": 2026,
        "snapshots": snapshots_data,
        "rounds": [{
            "round": 24,
            "matches": matches,
            "goals": 31,
            "leader": "Palmeiras",
            "leader_changed": False,
            "g4_in": [],
            "g4_out": [],
            "z4_in": [],
            "z4_out": [],
            "biggest_rise": {"teams": ["Vasco"], "places": 3},
            "biggest_fall": {"teams": ["Grêmio"], "places": 2},
            "biggest_win": {
                "winner": "Palmeiras", "home": "Palmeiras",
                "away": "Santos", "score": "4 x 0", "margin": 4,
            },
        }],
    }


class InstagramDailyTests(unittest.TestCase):
    def test_caption_contains_summary(self):
        caption = instagram_daily.build_caption(sample_insights())
        self.assertIn("Líder: Palmeiras", caption)
        self.assertIn("G4: Palmeiras, Flamengo, Bahia, São Paulo", caption)
        self.assertIn("Z4: Vasco, Coritiba, Chapecoense, Remo", caption)
        self.assertLessEqual(len(caption), 2200)

    def test_partial_round_is_identified(self):
        self.assertIn("(parcial)", instagram_daily.build_caption(sample_insights(matches=4)))

    def test_position_movements_compare_last_two_snapshots(self):
        movements = instagram_daily.position_movements(sample_insights(snapshots=2))
        self.assertEqual(movements["Bahia"], 1)
        self.assertEqual(movements["São Paulo"], -1)
        self.assertEqual(movements["Palmeiras"], 0)

    def test_movement_label_is_compact(self):
        self.assertEqual(instagram_daily.movement_label(2), "▲2")
        self.assertEqual(instagram_daily.movement_label(-3), "▼3")
        self.assertEqual(instagram_daily.movement_label(0), "•")

    def test_five_round_form_finds_best_team(self):
        form = instagram_daily.five_round_form(sample_insights(snapshots=6))
        self.assertIsNotNone(form)
        self.assertEqual(form["teams"], ["Palmeiras"])
        self.assertEqual(form["points"], 13)
        self.assertEqual(form["from_round"], 19)
        self.assertEqual(form["to_round"], 24)

    def test_caption_includes_five_round_form(self):
        self.assertIn("Em alta: Palmeiras somou 13 pontos nas últimas 5 rodadas.", instagram_daily.build_caption(sample_insights(snapshots=6)))

    def test_table_hook_prioritizes_close_title_race_on_tie(self):
        self.assertEqual(instagram_daily.table_hook(sample_insights()), "Liderança separada por 2 pontos")

    def test_table_hook_highlights_tighter_g4_cutoff(self):
        insights = sample_insights()
        table = insights["snapshots"][-1]["table"]
        table[0]["points"], table[1]["points"] = 55, 50
        table[3]["points"], table[4]["points"] = 44, 43
        table[15]["points"], table[16]["points"] = 20, 17
        self.assertEqual(instagram_daily.table_hook(insights), "Só 1 ponto separa o G4 do 5º")

    def test_table_hook_highlights_tighter_z4_cutoff(self):
        insights = sample_insights()
        table = insights["snapshots"][-1]["table"]
        table[0]["points"], table[1]["points"] = 55, 50
        table[3]["points"], table[4]["points"] = 44, 42
        table[15]["points"], table[16]["points"] = 20, 20
        self.assertEqual(instagram_daily.table_hook(insights), "Só 0 pontos separa permanência e Z4")

    def test_round_spotlight_prioritizes_new_leader(self):
        insights = sample_insights(snapshots=6)
        latest = insights["rounds"][-1]
        latest["leader"], latest["leader_changed"] = "Flamengo", True
        latest["g4_in"], latest["g4_out"] = ["Corinthians"], ["São Paulo"]
        spotlight = instagram_daily.round_spotlight(insights)
        self.assertEqual(spotlight["label"], "NOVO LÍDER")
        self.assertEqual(spotlight["text"], "Flamengo assumiu a ponta")

    def test_round_spotlight_highlights_g4_change(self):
        insights = sample_insights(snapshots=6)
        latest = insights["rounds"][-1]
        latest["g4_in"], latest["g4_out"] = ["Corinthians"], ["São Paulo"]
        spotlight = instagram_daily.round_spotlight(insights)
        self.assertEqual(spotlight["label"], "MUDANÇA NO G4")
        self.assertIn("Corinthians entrou", spotlight["text"])
        self.assertIn("São Paulo saiu", spotlight["text"])
        self.assertIn("Mudou o G4", instagram_daily.build_caption(insights))

    def test_round_spotlight_falls_back_to_biggest_win(self):
        spotlight = instagram_daily.round_spotlight(sample_insights())
        self.assertEqual(spotlight["label"], "DESTAQUE DA RODADA")
        self.assertEqual(spotlight["text"], "Palmeiras 4 x 0 Santos")

    def test_caption_starts_with_dynamic_hook(self):
        self.assertTrue(instagram_daily.build_caption(sample_insights()).startswith("Liderança separada por 2 pontos."))

    def test_render_creates_instagram_portrait(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "daily.png"
            now = datetime(2026, 8, 23, 10, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
            instagram_daily.render_card(sample_insights(snapshots=2), output, now=now)
            self.assertTrue(output.exists())
            with instagram_daily.Image.open(output) as image:
                self.assertEqual(image.size, (1080, 1350))


if __name__ == "__main__":
    unittest.main()
