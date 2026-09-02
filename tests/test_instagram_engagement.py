import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "instagram_engagement.py"
spec = importlib.util.spec_from_file_location("instagram_engagement", MODULE_PATH)
instagram_engagement = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(instagram_engagement)


class InstagramEngagementTests(unittest.TestCase):
    def test_leader_question_names_team(self):
        spotlight = {"kind": "leader", "text": "Palmeiras assumiu a ponta"}
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Palmeiras sustenta a liderança na próxima rodada?",
        )

    def test_pressure_question_uses_team(self):
        spotlight = {"kind": "g4_pressure", "team": "Corinthians", "text": "Corinthians está a 1 ponto do G4"}
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Corinthians entra no G4 na próxima rodada?",
        )

    def test_question_is_inserted_before_site_cta(self):
        caption = "Resumo factual.\n\nMais números e evolução rodada a rodada: brasileiraoemrodadas.com.br\n\n#Brasileirao"
        spotlight = {"kind": "g4_cluster", "text": "4 times em até 3 pontos do 4º"}
        enhanced = instagram_engagement.with_engagement_question(caption, spotlight)
        self.assertIn("Quem leva a quarta vaga nesse pelotão?", enhanced)
        self.assertLess(enhanced.index("Quem leva"), enhanced.index("Mais números"))

    def test_question_is_not_duplicated(self):
        spotlight = {"kind": "z4_cluster", "text": "4 times em até 3 pontos da permanência"}
        caption = "Resumo.\n\nQuem consegue abrir distância do Z4?\n\nMais números e evolução rodada a rodada: site"
        enhanced = instagram_engagement.with_engagement_question(caption, spotlight)
        self.assertEqual(enhanced.count("Quem consegue abrir distância do Z4?"), 1)


if __name__ == "__main__":
    unittest.main()
