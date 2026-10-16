import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import instagram_editorial
import instagram_engagement


def match(home, score, away, date="18/10/2026"):
    return {"home": home, "score": score, "away": away, "date": date, "round": 31}


class RoutWaveTests(unittest.TestCase):
    def test_detects_multiple_routs_and_lists_the_scores(self):
        matches = [
            match("Palmeiras", "4 x 0", "Santos"),
            match("Bahia", "3 x 0", "Vitória"),
            match("Flamengo", "2 x 1", "Fluminense"),
            match("Corinthians", "1 x 1", "São Paulo"),
            match("Grêmio", "1 x 0", "Internacional"),
        ]

        spotlight = instagram_editorial.rout_wave_spotlight(matches)

        self.assertEqual(spotlight["kind"], "rout_wave")
        self.assertEqual(spotlight["label"], "GOLEADAS EM SÉRIE")
        self.assertEqual(spotlight["matches"], 5)
        self.assertEqual(len(spotlight["routs"]), 2)
        self.assertIn("2 de 5 jogos", spotlight["text"])
        self.assertIn("Palmeiras 4 x 0 Santos", spotlight["caption"])
        self.assertIn("Bahia 3 x 0 Vitória", spotlight["caption"])

    def test_requires_both_volume_and_share(self):
        one_rout = [
            match("Palmeiras", "4 x 0", "Santos"),
            match("Bahia", "1 x 0", "Vitória"),
            match("Flamengo", "2 x 1", "Fluminense"),
            match("Corinthians", "1 x 1", "São Paulo"),
        ]
        low_share = one_rout + [
            match("Grêmio", "3 x 0", "Internacional"),
            match("Vasco", "1 x 0", "Botafogo"),
            match("Cruzeiro", "2 x 1", "Atlético-MG"),
        ]

        self.assertIsNone(instagram_editorial.rout_wave_spotlight(one_rout))
        self.assertIsNone(instagram_editorial.rout_wave_spotlight(low_share))

    def test_uses_block_wording_for_multiple_dates(self):
        matches = [
            match("Palmeiras", "4 x 0", "Santos", "17/10/2026"),
            match("Bahia", "0 x 3", "Vitória", "18/10/2026"),
            match("Flamengo", "2 x 1", "Fluminense", "18/10/2026"),
            match("Corinthians", "1 x 1", "São Paulo", "18/10/2026"),
        ]

        spotlight = instagram_editorial.rout_wave_spotlight(matches)

        self.assertIn("50% do bloco", spotlight["text"])
        self.assertIn("partidas do bloco", spotlight["caption"])
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Qual goleada foi mais marcante: Palmeiras ou Vitória?",
        )

    def test_does_not_override_high_priority_table_event(self):
        matches = [
            match("Palmeiras", "4 x 0", "Santos"),
            match("Bahia", "3 x 0", "Vitória"),
            match("Flamengo", "2 x 1", "Fluminense"),
            match("Corinthians", "1 x 1", "São Paulo"),
        ]
        leader = {"kind": "leader", "label": "NOVO LÍDER", "text": "Palmeiras assumiu", "caption": ""}

        with patch.object(instagram_editorial.instagram_matchday, "matchday_spotlight", return_value=leader):
            self.assertEqual(instagram_editorial.editorial_spotlight({}, matches), leader)

    def test_multi_rout_story_beats_single_high_scoring_match(self):
        matches = [
            match("Palmeiras", "5 x 1", "Remo"),
            match("Bahia", "3 x 0", "Chapecoense"),
            match("Flamengo", "2 x 1", "Mirassol"),
            match("Corinthians", "1 x 1", "Vasco"),
        ]
        generic = {"kind": "goals", "label": "NÚMERO DA RODADA", "text": "12 gols", "caption": ""}

        with patch.object(instagram_editorial.instagram_matchday, "matchday_spotlight", return_value=generic):
            self.assertEqual(instagram_editorial.editorial_spotlight({}, matches)["kind"], "rout_wave")


if __name__ == "__main__":
    unittest.main()
