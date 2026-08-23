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


def sample_insights(matches=10):
    teams = [
        "Palmeiras", "Flamengo", "Bahia", "São Paulo", "Corinthians",
        "Santos", "Botafogo", "Cruzeiro", "Fluminense", "Grêmio",
        "Atlético-MG", "Athletico-PR", "Bragantino", "Internacional",
        "Mirassol", "Vitória", "Vasco", "Coritiba", "Chapecoense", "Remo",
    ]
    table = [
        {"team": team, "points": 50 - i * 2, "position": i + 1}
        for i, team in enumerate(teams)
    ]
    return {
        "season": 2026,
        "snapshots": [{"round": 24, "table": table}],
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

    def test_render_creates_instagram_portrait(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "daily.png"
            now = datetime(2026, 8, 23, 10, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
            instagram_daily.render_card(sample_insights(), output, now=now)
            self.assertTrue(output.exists())
            with instagram_daily.Image.open(output) as image:
                self.assertEqual(image.size, (1080, 1350))


if __name__ == "__main__":
    unittest.main()
