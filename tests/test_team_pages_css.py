import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "brasileirao-team-pages.css"


class TeamPagesCssTests(unittest.TestCase):
    def test_history_table_stays_bounded_and_scrollable(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".team-history .br-table-wrap", css)
        self.assertIn("max-height: min(65vh, 36rem);", css)
        self.assertIn("overflow: auto;", css)
        self.assertIn("overscroll-behavior: contain;", css)

    def test_history_header_stays_visible_while_scrolling(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".team-history .br-table thead th", css)
        self.assertIn("position: sticky;", css)
        self.assertIn("top: 0;", css)


if __name__ == "__main__":
    unittest.main()
