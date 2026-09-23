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

    def test_mobile_history_keeps_round_visible_during_horizontal_scroll(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".team-history .br-table th:first-child", css)
        self.assertIn(".team-history .br-table td:first-child", css)
        self.assertIn("left: 0;", css)
        self.assertIn("box-shadow: 8px 0 12px -12px rgba(16, 23, 20, 0.8);", css)

    def test_sticky_round_header_stays_above_body_cells(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".team-history .br-table thead th:first-child", css)
        self.assertIn("z-index: 3;", css)
        self.assertIn("background: var(--br-ink, #101714);", css)

    def test_team_navigation_has_clear_hover_and_keyboard_focus(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".team-page-nav a:hover", css)
        self.assertIn(".team-page-nav a:focus-visible", css)
        self.assertIn("outline: 3px solid var(--br-hot, #dfff00);", css)
        self.assertIn("outline-offset: 3px;", css)

    def test_navigation_motion_respects_reduced_motion_preference(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("transition: none;", css)
        self.assertIn("transform: none;", css)

    def test_center_navigation_action_is_visually_distinct(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".team-page-nav a:nth-child(2)", css)
        self.assertIn("background: var(--br-ink, #101714);", css)
        self.assertIn(".team-page-nav a:nth-child(2):hover", css)
        self.assertIn("background: var(--br-hot, #dfff00);", css)


if __name__ == "__main__":
    unittest.main()
