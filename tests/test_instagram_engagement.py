import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

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

    def test_delayed_match_question_uses_table_context(self):
        spotlight = {"kind": "delayed_match", "text": "Flamengo 2 x 0 Mirassol • 4ª rodada"}
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "Esse jogo atrasado muda sua leitura da tabela?",
        )

    def test_tight_matchday_question_asks_about_competitive_balance(self):
        spotlight = {"kind": "tight_matches", "text": "4 de 5 jogos do dia decididos por até 1 gol"}
        self.assertEqual(
            instagram_engagement.engagement_question(spotlight),
            "A próxima rodada mantém esse nível de equilíbrio?",
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

    @patch.object(instagram_engagement.time, "sleep", return_value=None)
    @patch.object(instagram_engagement.time, "monotonic", side_effect=[0, 1, 2])
    @patch.object(instagram_engagement.requests, "get")
    def test_wait_for_container_polls_until_finished(self, get, _monotonic, _sleep):
        in_progress = Mock(ok=True)
        in_progress.json.return_value = {"status_code": "IN_PROGRESS"}
        finished = Mock(ok=True)
        finished.json.return_value = {"status_code": "FINISHED"}
        get.side_effect = [in_progress, finished]

        instagram_engagement._wait_for_container("container-1", "token", "v23.0", timeout=30, interval=0)

        self.assertEqual(get.call_count, 2)

    @patch.object(instagram_engagement.time, "monotonic", side_effect=[0, 0])
    @patch.object(instagram_engagement.requests, "get")
    def test_wait_for_container_fails_on_error_status(self, get, _monotonic):
        failed = Mock(ok=True)
        failed.json.return_value = {"status_code": "ERROR", "status": "Falha no processamento"}
        get.return_value = failed

        with self.assertRaises(RuntimeError):
            instagram_engagement._wait_for_container("container-1", "token", "v23.0")


if __name__ == "__main__":
    unittest.main()
