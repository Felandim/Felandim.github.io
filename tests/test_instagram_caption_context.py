import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location("instagram_editorial", SCRIPTS / "instagram_editorial.py")
instagram_editorial = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(instagram_editorial)


class CaptionContextTests(unittest.TestCase):
    def test_standings_context_exposes_title_and_z4_gaps(self):
        table = [
            {"team": f"Time {i}", "points": 60 - i, "position": i + 1}
            for i in range(20)
        ]
        table[0].update(team="Palmeiras", points=55)
        table[1].update(team="Flamengo", points=53)
        table[15].update(team="Vitória", points=30)
        table[16].update(team="Vasco", points=29)

        lines = instagram_editorial._standings_context(table)

        self.assertEqual(lines[0], "Topo: Palmeiras 55 x 53 Flamengo • 2 pts de diferença.")
        self.assertEqual(lines[1], "Corte do Z4: Vitória 30 x 29 Vasco • 1 pt.")

    def test_standings_context_requires_complete_table(self):
        self.assertEqual(instagram_editorial._standings_context([]), [])


if __name__ == "__main__":
    unittest.main()
