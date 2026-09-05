import importlib.util
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

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


def make_table(order=None):
    order = order or TEAMS
    return [
        {"team": team, "points": 50 - index * 2, "position": index + 1}
        for index, team in enumerate(order)
    ]


def sample_insights():
    table = make_table()
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


def volatile_insights(record=True):
    orders = []
    base = list(TEAMS)
    orders.append(base[:])
    for shift in (1, 2, 1, 2):
        order = base[:]
        order[4], order[4 + shift] = order[4 + shift], order[4]
        orders.append(order)
    if record:
        final = base[:]
        final[1], final[10] = final[10], final[1]
        final[3], final[15] = final[15], final[3]
    else:
        final = orders[-1][:]
    orders.append(final)

    snapshots = [{"round": 19 + index, "table": make_table(order)} for index, order in enumerate(orders)]
    data = sample_insights()
    data["snapshots"] = snapshots
    data["rounds"][-1]["round"] = snapshots[-1]["round"]
    return data


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

    def test_table_volatility_detects_new_season_record(self):
        spotlight = instagram_matchday.table_volatility_spotlight(volatile_insights(record=True))
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "table_volatility")
        self.assertIn("recorde do campeonato", spotlight["text"])
        self.assertGreater(spotlight["movement"], 0)

    def test_table_volatility_ignores_ordinary_round(self):
        self.assertIsNone(instagram_matchday.table_volatility_spotlight(volatile_insights(record=False)))

    def test_volatility_replaces_only_generic_spotlights(self):
        data = volatile_insights(record=True)
        spotlight = instagram_matchday.matchday_spotlight(data, [])
        self.assertEqual(spotlight["kind"], "table_volatility")

        data["rounds"][-1]["leader_changed"] = True
        data["rounds"][-1]["leader"] = "Palmeiras"
        spotlight = instagram_matchday.matchday_spotlight(data, [])
        self.assertEqual(spotlight["kind"], "leader")

    def test_caption_includes_volatility_context(self):
        caption = instagram_matchday.build_caption(volatile_insights(record=True), [])
        self.assertIn("Tabela em ebulição:", caption)
        self.assertLessEqual(len(caption), 2200)

    def test_spotlight_layout_wraps_long_copy_inside_available_width(self):
        image = Image.new("RGB", (1080, 1350))
        draw = ImageDraw.Draw(image)
        text = "Athletico-PR bateu o Atlético-MG • diferença de 14 posições antes da rodada"
        lines, font = instagram_matchday.spotlight_text_layout(draw, text)

        self.assertLessEqual(len(lines), 2)
        for line in lines:
            width = draw.textbbox((0, 0), line, font=font)[2]
            self.assertLessEqual(width, instagram_matchday.SPOTLIGHT_TEXT_WIDTH)

    def test_spotlight_layout_keeps_short_copy_on_one_line(self):
        image = Image.new("RGB", (1080, 1350))
        draw = ImageDraw.Draw(image)
        lines, _ = instagram_matchday.spotlight_text_layout(draw, "Palmeiras assumiu a ponta")
        self.assertEqual(lines, ["Palmeiras assumiu a ponta"])

    def test_render_overlays_responsive_spotlight(self):
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
