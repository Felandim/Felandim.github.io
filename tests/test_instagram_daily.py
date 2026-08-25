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

    snapshots_data = []
    if snapshots >= 6:
        base_table = [dict(row) for row in latest_table]
        for row in base_table:
            row["points"] -= 8
        # Palmeiras foi o melhor no recorte, com 13 pontos ganhos.
        base_table[0]["points"] = latest_table[0]["points"] - 13
        snapshots_data.append({"round": 19, "table": base_table})
        for round_number in range(20, 24):
            snapshots_data.append({"round": round_number, "table": base_table})
        snapshots_data.append({"round": 24, "table": latest_table})
    else:
        snapshots_data = [{"round": 24, "table": latest_table}]

    return {
        "season": 2026,
        "snapshots": snapshots_data,
        "rounds": [{
            "round": 24,
            "matches": matches,
            "goals": 31,
            "biggest_rise": {"teams": ["Vasco"], "places": 3},
            "biggest_fall": {"teams": ["Grêmio"], "places": 2},
            "biggest_win": {
                "winner": "Palmeiras", "home": "Palmeiras",
                "away": "Santos", "score": "4 x 0",
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
        caption = instagram_daily.build_caption(sample_insights(matches=4))
        self.assertIn("(parcial)", caption)

    def test_five_round_form_finds_best_team(self):
        form = instagram_daily.five_round_form(sample_insights(snapshots=6))
        self.assertIsNotNone(form)
        self.assertEqual(form["teams"], ["Palmeiras"])
        self.assertEqual(form["points"], 13)
        self.assertEqual(form["from_round"], 19)
        self.assertEqual(form["to_round"], 24)

    def test_caption_includes_five_round_form(self):
        caption = instagram_daily.build_caption(sample_insights(snapshots=6))
        self.assertIn("Em alta: Palmeiras somou 13 pontos nas últimas 5 rodadas.", caption)

    def test_render_creates_instagram_portrait(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "daily.png"
            now = datetime(2026, 8, 23, 10, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
            instagram_daily.render_card(sample_insights(snapshots=6), output, now=now)
            self.assertTrue(output.exists())
            with instagram_daily.Image.open(output) as image:
                self.assertEqual(image.size, (1080, 1350))


if __name__ == "__main__":
    unittest.main()
