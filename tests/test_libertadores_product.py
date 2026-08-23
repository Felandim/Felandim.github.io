import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LibertadoresProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data" / "libertadores_2026.json").read_text(encoding="utf-8"))
        cls.page = (ROOT / "libertadores" / "index.html").read_text(encoding="utf-8")

    def test_complete_competition_structure(self):
        self.assertEqual(8, len(self.data["groups"]))
        self.assertEqual(96, sum(len(group["games"]) for group in self.data["groups"]))
        self.assertEqual(155, len(self.data["matches"]))
        self.assertEqual(8, len(self.data["phases"]))

    def test_page_has_every_main_section(self):
        for section in ("grupos", "mata-mata", "jogos", "artilharia", "participantes", "regulamento"):
            self.assertIn(f'id="{section}"', self.page)

    def test_page_has_searchable_matches_and_metadata(self):
        self.assertIn('id="lib-phase-filter"', self.page)
        self.assertIn('id="lib-team-filter"', self.page)
        self.assertIn('<link rel="canonical" href="https://felandim.github.io/libertadores/">', self.page)
        self.assertIn('type="application/ld+json"', self.page)


if __name__ == "__main__":
    unittest.main()
