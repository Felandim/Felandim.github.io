import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location("instagram_editorial", SCRIPTS / "instagram_editorial.py")
instagram_editorial = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(instagram_editorial)

engagement_spec = importlib.util.spec_from_file_location("instagram_engagement", SCRIPTS / "instagram_engagement.py")
instagram_engagement = importlib.util.module_from_spec(engagement_spec)
assert engagement_spec.loader is not None
engagement_spec.loader.exec_module(instagram_engagement)


TEAMS = [
    "Palmeiras", "Flamengo", "Bahia", "São Paulo", "Corinthians", "Santos",
    "Botafogo", "Cruzeiro", "Fluminense", "Grêmio", "Atlético-MG", "Athletico-PR",
    "Bragantino", "Internacional", "Mirassol", "Vitória", "Vasco", "Coritiba",
    "Chapecoense", "Remo",
]


def insights(points=(50, 49, 47, 43), leader_changed=False):
    table = []
    for index, team in enumerate(TEAMS):
        value = points[index] if index < len(points) else max(0, 39 - index * 2)
        table.append({"team": team, "points": value, "position": index + 1})
    snapshot = {"round": 24, "table": table}
    return {
        "season": 2026,
        "snapshots": [{"round": 23, "table": table}, snapshot],
        "rounds": [{
            "round": 24,
            "matches": 10,
            "goals": 24,
            "leader": "Palmeiras",
            "leader_changed": leader_changed,
            "g4_in": [], "g4_out": [], "z4_in": [], "z4_out": [],
            "biggest_rise": {"teams": ["Corinthians"], "places": 3},
            "biggest_fall": {"teams": ["Santos"], "places": 2},
            "biggest_win": {"winner": "Palmeiras", "home": "Palmeiras", "away": "Santos", "score": "4 x 0", "margin": 4},
        }],
    }


class InstagramEditorialTests(unittest.TestCase):
    def test_title_race_requires_three_teams_within_three_points(self):
        spotlight = instagram_editorial.title_race_spotlight(insights())
        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "title_cluster")
        self.assertEqual(spotlight["count"], 3)
        self.assertEqual(spotlight["spread"], 3)
        self.assertEqual(spotlight["teams"], ["Palmeiras", "Flamengo", "Bahia"])
        self.assertIn("3 times separados por só 3 pontos", spotlight["text"])

    def test_title_race_ignores_two_team_gap(self):
        self.assertIsNone(instagram_editorial.title_race_spotlight(insights((50, 49, 46, 43))))

    def test_title_race_does_not_override_new_leader(self):
        spotlight = instagram_editorial.editorial_spotlight(insights(leader_changed=True), [])
        self.assertEqual(spotlight["kind"], "leader")

    def test_caption_and_question_use_title_race_context(self):
        data = insights()
        spotlight = instagram_editorial.editorial_spotlight(data, [])
        caption = instagram_editorial.build_caption(data, [])
        question = instagram_engagement.engagement_question(spotlight)
        self.assertIn("Briga pelo título: 3 times estão separados por apenas 3 pontos", caption)
        self.assertEqual(question, "Quem sai desse pelotão como principal candidato ao título?")
        self.assertLessEqual(len(caption), 2200)

    def test_caption_keeps_one_editorial_story_instead_of_stat_dump(self):
        caption = instagram_editorial.build_caption(insights(), [])
        self.assertEqual(caption.count("Briga pelo título:"), 1)
        self.assertNotIn("Maior subida:", caption)
        self.assertNotIn("Maior queda:", caption)
        self.assertNotIn("Maior vitória:", caption)
        self.assertNotIn("Em alta:", caption)
        self.assertIn("Líder: Palmeiras — 50 pts.", caption)
        self.assertIn("G4: Palmeiras, Flamengo, Bahia, São Paulo.", caption)
        self.assertIn("Z4: Vasco, Coritiba, Chapecoense, Remo.", caption)
        self.assertIn("Mais números e evolução rodada a rodada:", caption)

    def test_engagement_question_is_inserted_before_site_cta(self):
        data = insights()
        spotlight = instagram_editorial.editorial_spotlight(data, [])
        caption = instagram_editorial.build_caption(data, [])
        enriched = instagram_engagement.with_engagement_question(caption, spotlight)
        question_index = enriched.index("Quem sai desse pelotão")
        site_index = enriched.index("Mais números e evolução rodada a rodada:")
        self.assertLess(question_index, site_index)
        self.assertLessEqual(len(enriched), 2200)

    def test_render_keeps_instagram_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "daily.png"
            instagram_editorial.render_card(insights(), [], output)
            self.assertTrue(output.exists())
            with instagram_editorial.Image.open(output) as image:
                self.assertEqual(image.size, (1080, 1350))


if __name__ == "__main__":
    unittest.main()
