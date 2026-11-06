import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageColor


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import instagram_editorial
import instagram_engagement


def table(points, played, order=None):
    order = order or [f"Time {index:02d}" for index in range(1, 21)]
    return [
        {
            "team": team,
            "position": index,
            "points": points[index - 1],
            "played": played[index - 1],
        }
        for index, team in enumerate(order, 1)
    ]


def insights(previous, current):
    return {"snapshots": [{"round": 33, "table": previous}, {"round": 34, "table": current}]}


class ClinchedStatusTest(unittest.TestCase):
    def test_detects_title_only_when_it_becomes_mathematically_certain(self):
        previous = table([75, 65, 62, 59, *range(54, 39, -1), 20], [33] * 20)
        current = table([78, 65, 62, 59, *range(54, 39, -1), 20], [34] * 20)

        spotlight = instagram_editorial.clinched_status_spotlight(insights(previous, current))

        self.assertEqual(spotlight["kind"], "champion_clinched")
        self.assertEqual(spotlight["team"], "Time 01")
        self.assertIn("78 pontos", spotlight["text"])

    def test_detects_new_top_four_place_with_conservative_tie_handling(self):
        previous = table([78, 76, 74, 65, 55, *range(50, 35, -1)], [33] * 20)
        current = table([78, 76, 74, 68, 55, *range(50, 35, -1)], [34] * 20)
        spotlight = instagram_editorial.clinched_status_spotlight(insights(previous, current))
        self.assertEqual(spotlight["kind"], "top_four_clinched")
        self.assertEqual(spotlight["team"], "Time 04")

        tied_previous = table([78, 76, 74, 65, 56, *range(50, 35, -1)], [33] * 20)
        tied_current = table([78, 76, 74, 68, 56, *range(50, 35, -1)], [34] * 20)
        tie_story = instagram_editorial.clinched_status_spotlight(insights(tied_previous, tied_current))
        self.assertNotEqual(tie_story and tie_story["kind"], "top_four_clinched")

    def test_detects_new_survival_and_relegation_without_guessing_tiebreakers(self):
        previous_safe = table([70, 66, 62, 58, 55, 52, 50, 48, 46, 44, 42, 41, 40, 39, 36, 35, 32, 31, 30, 29], [35] * 20)
        current_safe = table(
            [70, 66, 62, 58, 55, 52, 50, 48, 46, 44, 42, 41, 40, 39, 39, 35, 32, 31, 30, 29],
            [35] * 14 + [36, 35, 36, 36, 36, 36],
        )
        safe = instagram_editorial.clinched_status_spotlight(insights(previous_safe, current_safe))
        self.assertEqual(safe["kind"], "survival_clinched")
        self.assertEqual(safe["team"], "Time 15")

        previous_drop = table([70, 66, 62, 58, 55, 52, 50, 48, 46, 44, 42, 41, 40, 36, 34, 30, 27, 25, 23, 20], [34] * 20)
        current_drop = table(
            [70, 66, 62, 58, 55, 52, 50, 48, 46, 44, 42, 41, 40, 36, 34, 30, 27, 25, 23, 20],
            [34] * 19 + [35],
        )
        relegated = instagram_editorial.clinched_status_spotlight(insights(previous_drop, current_drop))
        self.assertEqual(relegated["kind"], "relegation_clinched")
        self.assertEqual(relegated["team"], "Time 20")
        self.assertEqual(relegated["tone"], "danger")

    def test_mathematical_event_outweighs_ordinary_table_story(self):
        previous = table([75, 65, 62, 59, *range(54, 39, -1), 20], [33] * 20)
        current = table([78, 65, 62, 59, *range(54, 39, -1), 20], [34] * 20)
        with patch.object(
            instagram_editorial.instagram_matchday,
            "matchday_spotlight",
            return_value={"kind": "leader", "label": "NOVA LIDERANÇA", "text": "outro fato"},
        ):
            spotlight = instagram_editorial.editorial_spotlight(insights(previous, current), [])
        self.assertEqual(spotlight["kind"], "champion_clinched")

    def test_each_status_gets_a_specific_engagement_question(self):
        self.assertEqual(
            instagram_engagement.engagement_question({"kind": "champion_clinched", "team": "Flamengo"}),
            "Quem foi o principal nome do título do Flamengo?",
        )
        self.assertEqual(
            instagram_engagement.engagement_question({"kind": "relegation_clinched", "team": "Time 20"}),
            "O que mais pesou na campanha do Time 20?",
        )

    def test_relegation_label_uses_the_existing_danger_color(self):
        image = Image.new("RGB", (1080, 1350), instagram_editorial.instagram_daily.BG)
        instagram_editorial.instagram_matchday.draw_spotlight(
            image,
            {"label": "REBAIXAMENTO CONFIRMADO", "text": "Time 20 • queda confirmada", "tone": "danger"},
        )
        colors = image.crop((80, 1150, 600, 1192)).getcolors(maxcolors=100_000)
        self.assertIn(ImageColor.getrgb(instagram_editorial.instagram_daily.RED), [color for _, color in colors])


if __name__ == "__main__":
    unittest.main()
