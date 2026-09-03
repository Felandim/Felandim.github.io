#!/usr/bin/env python3
"""Adapta o card diário ao conjunto de jogos que realmente motivou a publicação."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

import instagram_daily


def publication_date(now: datetime | None = None) -> date:
    now = now or datetime.now(instagram_daily.TZ)
    return now.date() - timedelta(days=1)


def completed_matches_for_date(matches: list[dict], target: date) -> list[dict]:
    target_text = target.strftime("%d/%m/%Y")
    return [
        match for match in matches
        if match.get("date") == target_text and instagram_daily._score(match.get("score", ""))
    ]


def delayed_match_spotlight(insights: dict, matches: list[dict]) -> dict | None:
    """Destaca partidas atrasadas sem confundi-las com a rodada corrente."""
    if not matches:
        return None
    _, latest = instagram_daily.current_snapshot(insights)
    latest_round = int(latest["round"])
    delayed = [match for match in matches if int(match.get("round", 0)) != latest_round]
    if not delayed:
        return None

    def importance(match: dict) -> tuple[int, int, str]:
        home_goals, away_goals = instagram_daily._score(match.get("score", "")) or (0, 0)
        return (abs(home_goals - away_goals), home_goals + away_goals, match.get("home", ""))

    match = max(delayed, key=importance)
    return {
        "kind": "delayed_match",
        "label": "JOGO ATRASADO",
        "text": f"{match['home']} {match['score']} {match['away']} • {match['round']}ª rodada",
        "caption": f"Jogo atrasado: {match['home']} {match['score']} {match['away']}, pela {match['round']}ª rodada.",
    }


def matchday_spotlight(insights: dict, matches: list[dict]) -> dict:
    return delayed_match_spotlight(insights, matches) or instagram_daily.round_spotlight(insights, matches)


def build_caption(insights: dict, matches: list[dict]) -> str:
    caption = instagram_daily.build_caption(insights, matches)
    delayed = delayed_match_spotlight(insights, matches)
    if not delayed or delayed["caption"] in caption:
        return caption

    lines = caption.splitlines()
    insert_at = 2 if len(lines) >= 2 else len(lines)
    lines.insert(insert_at, delayed["caption"])
    return "\n".join(lines)[:2200]


def render_card(
    insights: dict,
    matches: list[dict],
    output: Path = instagram_daily.DEFAULT_OUTPUT,
    now: datetime | None = None,
) -> Path:
    output = instagram_daily.render_card(insights, output, now=now, matches=matches)
    delayed = delayed_match_spotlight(insights, matches)
    if not delayed:
        return output

    image = Image.open(output).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((60, 1165, 1020, 1260), radius=24, fill=instagram_daily.PANEL)
    instagram_daily._draw_text(
        draw, (90, 1185), delayed["label"], instagram_daily._font(25), instagram_daily.ACCENT
    )
    instagram_daily._draw_text(
        draw, (90, 1222), delayed["text"], instagram_daily._font(31), instagram_daily.TEXT
    )
    image.save(output, "PNG", optimize=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("render", "caption"))
    parser.add_argument("--insights", type=Path, default=instagram_daily.INSIGHTS_FILE)
    parser.add_argument("--matches", type=Path, default=instagram_daily.MATCHES_FILE)
    parser.add_argument("--output", type=Path, default=instagram_daily.DEFAULT_OUTPUT)
    args = parser.parse_args()

    insights = instagram_daily.load_insights(args.insights)
    all_matches = instagram_daily.load_matches(args.matches)
    matches = completed_matches_for_date(all_matches, publication_date())

    if args.command == "render":
        print(render_card(insights, matches, args.output))
    else:
        print(build_caption(insights, matches))


if __name__ == "__main__":
    main()
