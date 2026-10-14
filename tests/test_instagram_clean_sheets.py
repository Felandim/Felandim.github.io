import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


instagram_editorial = load_module("instagram_editorial")
instagram_engagement = load_module("instagram_engagement")
instagram_matchday = load_module("instagram_matchday")


class InstagramCleanSheetTests(unittest.TestCase):
    def test_detects_clean_sheet_wave_across_a_multi_day_block(self):
        matches = [
            {"date": "17/10/2026", "home": "Palmeiras", "away": "Santos", "score": "1 x 0"},
            {"date": "18/10/2026", "home": "Flamengo", "away": "Botafogo", "score": "0 x 2"},
            {"date": "18/10/2026", "home": "Bahia", "away": "Vitória", "score": "0 x 0"},
            {"date": "19/10/2026", "home": "Grêmio", "away": "Cruzeiro", "score": "2 x 1"},
        ]

        spotlight = instagram_editorial.clean_sheet_wave_spotlight(matches)

        self.assertIsNotNone(spotlight)
        self.assertEqual(spotlight["kind"], "clean_sheet_wave")
        self.assertEqual(spotlight["label"], "REDE ZERADA")
        self.assertEqual(spotlight["clean_sheet_matches"], 3)
        self.assertEqual(spotlight["share"], 0.75)
        self.assertEqual(spotlight["teams"], ["Palmeiras", "Botafogo", "Bahia", "Vitória"])
        self.assertIn("75% do bloco", spotlight["text"])
        self.assertIn("partidas do bloco", spotlight["caption"])

    def test_requires_four_completed_matches_and_seventy_five_percent(self):
        self.assertIsNone(instagram_editorial.clean_sheet_wave_spotlight([
            {"score": "1 x 0"}, {"score": "0 x 2"}, {"score": "0 x 0"},
        ]))
        self.assertIsNone(instagram_editorial.clean_sheet_wave_spotlight([
            {"score": "1 x 0"}, {"score": "0 x 2"}, {"score": "1 x 1"}, {"score": "2 x 1"},
        ]))

    def test_has_a_specific_engagement_question(self):
        question = instagram_engagement.engagement_question({"kind": "clean_sheet_wave"})
        self.assertEqual(question, "Qual dessas defesas mais te impressionou?")

    def test_multi_day_derby_copy_does_not_claim_same_day(self):
        matches = [
            {"date": "17/10/2026", "home": "Flamengo", "away": "Fluminense", "score": "1 x 0"},
            {"date": "18/10/2026", "home": "Palmeiras", "away": "Corinthians", "score": "2 x 1"},
        ]

        spotlight = instagram_editorial.derby_day_spotlight(matches)

        self.assertEqual(spotlight["label"], "BLOCO DE CLÁSSICOS")
        self.assertIn("no mesmo bloco", spotlight["text"])
        self.assertNotIn("mesmo dia", spotlight["text"])
        self.assertTrue(spotlight["caption"].startswith("Bloco de clássicos:"))

    def test_multi_day_copy_is_used_by_existing_result_patterns(self):
        matches = [
            {"date": "17/10/2026", "score": "1 x 0"},
            {"date": "18/10/2026", "score": "0 x 1"},
            {"date": "18/10/2026", "score": "2 x 1"},
            {"date": "19/10/2026", "score": "3 x 0"},
        ]

        self.assertIn("Bloco sem empates", instagram_editorial.drawless_day_spotlight(matches)["caption"])
        self.assertIn("jogos do bloco", instagram_matchday.tight_matchday_spotlight(matches)["text"])


if __name__ == "__main__":
    unittest.main()
