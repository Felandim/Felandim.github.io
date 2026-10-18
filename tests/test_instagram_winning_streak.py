import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


instagram_editorial = load_module("instagram_editorial")
instagram_engagement = load_module("instagram_engagement")


def profile(team, wins, position, points):
    return {
        "team": team,
        "current": {"position": position, "points": points},
        "streaks": {"current_wins": wins},
    }


def insights(leader_changed=False):
    teams = [
        {"team": name, "position": index + 1, "points": 70 - index}
        for index, name in enumerate([
            "Palmeiras", "Flamengo", "Bahia", "São Paulo", "Atlético-MG", "Botafogo",
            "Cruzeiro", "Fluminense", "Grêmio", "Corinthians", "Santos", "Bragantino",
            "Athletico-PR", "Mirassol", "Internacional", "Vasco", "Vitória", "Coritiba",
            "Chapecoense", "Remo",
        ])
    ]
    return {
        "season": 2026,
        "team_profiles": {
            "palmeiras": profile("Palmeiras", 3, 1, 67),
            "atletico-mg": profile("Atlético-MG", 4, 5, 52),
            "botafogo": profile("Botafogo", 2, 6, 49),
        },
        "snapshots": [{"round": 31, "table": teams}],
        "rounds": [{
            "round": 31, "matches": 10, "goals": 20, "leader": "Palmeiras",
            "leader_changed": leader_changed, "g4_in": [], "g4_out": [],
            "z4_in": [], "z4_out": [], "biggest_win": None,
        }],
    }


class InstagramWinningStreakTests(unittest.TestCase):
    def test_detects_longest_streak_renewed_by_block_winner(self):
        matches = [
            {"home": "Atlético-MG", "away": "Coritiba", "score": "1 x 0"},
            {"home": "Palmeiras", "away": "Santos", "score": "2 x 0"},
        ]

        spotlight = instagram_editorial.winning_streak_spotlight(insights(), matches)

        self.assertEqual(spotlight["kind"], "winning_streak")
        self.assertEqual(spotlight["team"], "Atlético-MG")
        self.assertEqual(spotlight["wins"], 4)
        self.assertIn("4 vitórias seguidas", spotlight["text"])
        self.assertIn("5º lugar, com 52 pontos", spotlight["caption"])

    def test_ignores_streak_not_renewed_in_published_block_and_short_runs(self):
        matches = [{"home": "Botafogo", "away": "Coritiba", "score": "1 x 0"}]
        self.assertIsNone(instagram_editorial.winning_streak_spotlight(insights(), matches))

        matches = [{"home": "Coritiba", "away": "Atlético-MG", "score": "1 x 0"}]
        self.assertIsNone(instagram_editorial.winning_streak_spotlight(insights(), matches))

    def test_major_table_event_keeps_priority_over_winning_streak(self):
        matches = [
            {"round": 31, "home": "Palmeiras", "away": "Santos", "score": "2 x 0"},
            {"round": 31, "home": "Botafogo", "away": "Cruzeiro", "score": "1 x 1"},
        ]
        spotlight = instagram_editorial.editorial_spotlight(insights(leader_changed=True), matches)
        self.assertEqual(spotlight["kind"], "leader")

    def test_caption_and_question_turn_streak_into_team_story(self):
        matches = [
            {"round": 31, "home": "Palmeiras", "away": "Santos", "score": "2 x 0"},
            {"round": 31, "home": "Botafogo", "away": "Cruzeiro", "score": "1 x 1"},
        ]
        spotlight = instagram_editorial.editorial_spotlight(insights(), matches)
        caption = instagram_editorial.build_caption(insights(), matches)

        self.assertEqual(spotlight["kind"], "winning_streak")
        self.assertIn("Palmeiras venceu os últimos 3 jogos", caption)
        self.assertEqual(instagram_engagement.engagement_question(spotlight), "Quem consegue parar o Palmeiras?")


if __name__ == "__main__":
    unittest.main()
