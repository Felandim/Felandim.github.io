import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import instagram_schedule as schedule


def match(day, hour="20:00", score="1 x 0", round_number=31):
    return {"round": round_number, "date": f"{day:02d}/10/2026", "time": hour,
            "home": f"Time {day}", "away": f"Visitante {day}", "score": score}


def at(day, hour=10):
    return datetime(2026, 10, day, hour, tzinfo=schedule.TZ)


class RoundBlockScheduleTests(unittest.TestCase):
    def test_saturday_sunday_monday_only_posts_tuesday_with_all_games(self):
        games = [match(17), match(18), match(19, score="-")]
        self.assertEqual(schedule.due_blocks(games, at(18)), [])
        self.assertEqual(schedule.due_blocks(games, at(19)), [])
        self.assertEqual(schedule.due_blocks(games, at(20)), [])
        games[-1]["score"] = "0 x 0"
        due = schedule.due_blocks(games, at(20))
        self.assertEqual([len(b["matches"]) for b in due], [3])
        self.assertEqual(schedule.due_blocks(games, at(21)), [])

    def test_postponed_match_does_not_hold_main_block_and_posts_separately(self):
        games = [match(17), match(18), match(19), match(27, score="-")]
        first = schedule.due_blocks(games, at(20))
        self.assertEqual(len(first[0]["matches"]), 3)
        state = {first[0]["id"]: {"match_keys": first[0]["match_keys"], "outcome": "published"}}
        self.assertEqual(schedule.due_blocks(games, at(20), state), [])
        games[-1]["score"] = "2 x 1"
        later = schedule.due_blocks(games, at(28), state)
        self.assertEqual(later[0]["matches"], [games[-1]])

    def test_exactly_48_hours_joins_but_48_hours_one_minute_separates(self):
        games = [match(17), match(19, score="-")]
        self.assertEqual(schedule.due_blocks(games, at(18)), [])
        games[1]["time"] = "20:01"
        self.assertEqual(len(schedule.due_blocks(games, at(18))), 1)

    def test_unscheduled_and_explicitly_postponed_matches_do_not_block(self):
        games = [match(17), dict(match(18), date="A definir"), dict(match(19, score="-"), status="adiado")]
        self.assertEqual(len(schedule.due_blocks(games, at(18))), 1)

    def test_unknown_time_conservatively_keeps_possible_48_hour_gap_together(self):
        games = [match(17, hour=""), match(19, score="-")]
        self.assertEqual(schedule.due_blocks(games, at(18)), [])

    def test_rounds_are_independent_and_can_each_generate_their_own_post(self):
        games = [match(19), match(20, score="-", round_number=32), match(19, round_number=4)]
        due = schedule.due_blocks(games, at(20))
        self.assertEqual([b["round"] for b in due], [4, 31])

    def test_10am_boundary_uses_sao_paulo_even_with_utc_input(self):
        games = [match(19)]
        self.assertEqual(schedule.due_blocks(games, datetime(2026, 10, 20, 12, 59, tzinfo=timezone.utc)), [])
        self.assertEqual(len(schedule.due_blocks(games, datetime(2026, 10, 20, 13, tzinfo=timezone.utc))), 1)

    def test_unfinished_earlier_match_blocks_publication(self):
        games = [match(17, score="-"), match(18), match(19)]
        self.assertEqual(schedule.due_blocks(games, at(20)), [])

    def test_isolated_game_explains_its_points_and_current_position(self):
        block = schedule.due_blocks([match(19)], at(20))[0]
        insights = {"snapshots": [{"table": [{"team": "Time 19", "points": 40, "position": 10}]}]}
        spotlight = schedule.block_spotlight(insights, block)
        self.assertIn("+3 pontos; agora 40 pontos, 10º lugar", spotlight["caption"])
        self.assertIn("Visitante 19: +0 pontos", spotlight["caption"])

    def test_real_next_round_waits_until_tuesday(self):
        path = Path(__file__).resolve().parents[1] / "data/serie_a_2026.json"
        games = [dict(m) for m in json.loads(path.read_text())["matches"] if m["round"] == 31]
        self.assertEqual(len(games), 10)
        for day in (17, 18, 19, 20):
            for m in games:
                m["score"] = "1 x 0" if datetime.strptime(m["date"], "%d/%m/%Y").day < day else "-"
            due = schedule.due_blocks(games, at(day))
            self.assertEqual([len(b["matches"]) for b in due], [10] if day == 20 else [])

    def test_successful_publication_is_not_repeated(self):
        plan = schedule.due_blocks([match(19)], at(20))
        plan[0]["caption"] = "Resumo do bloco."
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"INSTAGRAM_IG_USER_ID": "id", "INSTAGRAM_ACCESS_TOKEN": "test"}), patch("instagram_engagement.publish_when_ready", return_value="media") as publish:
            state = Path(directory) / "state.json"
            schedule.publish_plan(plan, "https://example.com", state)
            schedule.publish_plan(plan, "https://example.com", state)
            publish.assert_called_once()
            self.assertEqual(schedule.read_state(state)[plan[0]["id"]]["outcome"], "published")

    def test_ambiguous_failure_is_recorded_and_never_blindly_retried(self):
        plan = schedule.due_blocks([match(19)], at(20))
        plan[0]["caption"] = "Resumo do bloco."
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"INSTAGRAM_IG_USER_ID": "id", "INSTAGRAM_ACCESS_TOKEN": "test"}), patch("instagram_engagement.publish_when_ready", side_effect=TimeoutError) as publish:
            state = Path(directory) / "state.json"
            with self.assertRaises(TimeoutError):
                schedule.publish_plan(plan, "https://example.com", state)
            schedule.publish_plan(plan, "https://example.com", state)
            publish.assert_called_once()
            self.assertEqual(schedule.read_state(state)[plan[0]["id"]]["outcome"], "started")


if __name__ == "__main__":
    unittest.main()
