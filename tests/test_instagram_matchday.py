import importlib.util
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "instagram_matchday.py"
spec = importlib.util.spec_from_file_location("instagram_matchday", MODULE_PATH)
instagram_matchday = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(instagram_matchday)


def sample_insights():
    teams = [
        "Palmeiras", "Flamengo", "Bahia", "São Paulo", "Corinthians", "Santos",
        "Botafogo", "Cruzeiro", "Fluminense", "Grêmio", "Atlético-MG", "Athletico-PR",
        "Bragantino", "Internacional", "Mirassol", "Vitória", "Vasco", "Coritiba",
        "Chapecoense", "Remo",
    ]
    table = [
        {"team": team, "points": 50 - index * 2, "position": index + 1}
        for index, team in enumerate(teams)
    ]
    return {
        "season": 2026,
        "snapshots": [{"round": 23, "table": table}, {"round": 24, "table": table}],
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


class InstagramMatchdayTests(unittest.TestCase):
    def test_publication_date_is_previous_day(self):
        now = datetime(2026, 9, 3, 8, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
        self.assertEqual(instagram_matchday.publication_date(now), date(2026, 9, 2))

    def test_completed_matches_for_date_filters_other_days_and_unplayed(self):
        matches = [
            {"date": "02/09/2026", "score": "2 x 0"},
            {"date": "02/09/2026", "score": ""},
            {"date": "01/09/2026", "score": "1 x 0"},
        ]
        selected = instagram_matchday.completed_matches_for_date(matches, date(2026, 9, 2))
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["score"], "2 x 0")

    def test_delayed_match_gets_explicit_context(self):
        matches = [{
            "date": "02/09/2026", "round": 4, "home": "Flamengo",
            "away": "Mirassol", "score": "2 x 0",
        }]
        spotlight = instagram_matchday.delayed_match_spotlight(sample_insights(), matches)
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["label"], "JOGO ATRASADO")
        self.assertEqual(spotlight["text"], "Flamengo 2 x 0 Mirassol • 4ª rodada")

    def test_current_round_match_keeps_existing_editorial_logic(self):
        matches = [{
            "date": "02/09/2026", "round": 24, "home": "Flamengo",
            "away": "Mirassol", "score": "2 x 0",
        }]
        self.assertIsNone(instagram_matchday.delayed_match_spotlight(sample_insights(), matches))

    def test_caption_explains_delayed_fixture(self):
        matches = [{
            "date": "02/09/2026", "round": 4, "home": "Flamengo",
            "away": "Mirassol", "score": "2 x 0",
        }]
        caption = instagram_matchday.build_caption(sample_insights(), matches)
        self.assertIn("Jogo atrasado: Flamengo 2 x 0 Mirassol, pela 4ª rodada.", caption)
        self.assertLessEqual(len(caption), 2200)

    def test_render_overlays_delayed_match_spotlight(self):
        matches = [{
            "date": "02/09/2026", "round": 4, "home": "Flamengo",
            "away": "Mirassol", "score": "2 x 0",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "daily.png"
            instagram_matchday.render_card(sample_insights(), matches, output)
            self.assertTrue(output.exists())
            with instagram_matchday.Image.open(output) as image:
                self.assertEqual(image.size, (1080, 1350))


if __name__ == "__main__":
    unittest.main()
