#!/usr/bin/env python3
"""Adapta o card diário ao conjunto de jogos que realmente motivou a publicação."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

import instagram_daily


SPOTLIGHT_BOX = (60, 1140, 1020, 1275)
SPOTLIGHT_TEXT_WIDTH = 870


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


def table_volatility_spotlight(insights: dict, minimum_history: int = 5) -> dict | None:
    """Destaca quando a rodada bate ou iguala o maior movimento agregado da tabela no campeonato."""
    snapshots = insights.get("snapshots", [])
    if len(snapshots) < minimum_history + 1:
        return None

    scores: list[int] = []
    for previous, current in zip(snapshots, snapshots[1:]):
        previous_positions = {row["team"]: row["position"] for row in previous["table"]}
        movement = sum(
            abs(previous_positions[row["team"]] - row["position"])
            for row in current["table"]
            if row["team"] in previous_positions
        )
        scores.append(movement)

    current_score = scores[-1]
    previous_best = max(scores[:-1], default=0)
    if current_score <= 0 or current_score < previous_best:
        return None

    if current_score > previous_best:
        qualifier = "recorde do campeonato"
        caption = f"Tabela em ebulição: a rodada somou {current_score} posições de movimento, a maior marca do campeonato até aqui."
    else:
        qualifier = "iguala maior marca"
        caption = f"Tabela em ebulição: a rodada somou {current_score} posições de movimento e igualou a maior marca do campeonato."

    return {
        "kind": "table_volatility",
        "label": "TABELA EM EBULIÇÃO",
        "text": f"{current_score} posições de movimento • {qualifier}",
        "caption": caption,
        "movement": current_score,
    }


def matchday_spotlight(insights: dict, matches: list[dict]) -> dict:
    delayed = delayed_match_spotlight(insights, matches)
    if delayed:
        return delayed

    base = instagram_daily.round_spotlight(insights, matches)
    high_priority = {
        "leader", "g4", "z4", "upset", "g4_cluster", "z4_cluster", "g4_pressure", "z4_pressure",
    }
    if base.get("kind") in high_priority:
        return base

    return table_volatility_spotlight(insights) or base


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Quebra texto por palavras sem ultrapassar a largura disponível."""
    words = text.split()
    if not words:
        return [""]

    lines = [words[0]]
    for word in words[1:]:
        candidate = f"{lines[-1]} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def spotlight_text_layout(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int = SPOTLIGHT_TEXT_WIDTH,
    max_lines: int = 2,
    preferred_size: int = 31,
    minimum_size: int = 23,
) -> tuple[list[str], object]:
    """Ajusta tamanho e quebra para manter o destaque legível dentro do card."""
    for size in range(preferred_size, minimum_size - 1, -1):
        font = instagram_daily._font(size)
        lines = _wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return lines, font

    font = instagram_daily._font(minimum_size)
    lines = _wrap_text(draw, text, font, max_width)
    if len(lines) <= max_lines:
        return lines, font

    kept = lines[:max_lines]
    tail = " ".join(lines[max_lines - 1:])
    ellipsis = "…"
    while tail and draw.textbbox((0, 0), tail + ellipsis, font=font)[2] > max_width:
        tail = tail[:-1].rstrip()
    kept[-1] = (tail + ellipsis) if tail else ellipsis
    return kept, font


def draw_spotlight(image: Image.Image, spotlight: dict) -> None:
    """Redesenha o destaque com quebra e redução de fonte quando necessário."""
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(SPOTLIGHT_BOX, radius=24, fill=instagram_daily.PANEL)
    instagram_daily._draw_text(
        draw, (90, 1158), spotlight["label"], instagram_daily._font(25), instagram_daily.ACCENT
    )

    lines, font = spotlight_text_layout(draw, spotlight["text"])
    y = 1195
    for line in lines:
        instagram_daily._draw_text(draw, (90, y), line, font, instagram_daily.TEXT)
        y += 34


def build_caption(insights: dict, matches: list[dict]) -> str:
    caption = instagram_daily.build_caption(insights, matches)
    spotlight = matchday_spotlight(insights, matches)
    extra = spotlight.get("caption", "")
    if not extra or extra in caption:
        return caption

    lines = caption.splitlines()
    insert_at = 2 if len(lines) >= 2 else len(lines)
    lines.insert(insert_at, extra)
    return "\n".join(lines)[:2200]


def render_card(
    insights: dict,
    matches: list[dict],
    output: Path = instagram_daily.DEFAULT_OUTPUT,
    now: datetime | None = None,
) -> Path:
    output = instagram_daily.render_card(insights, output, now=now, matches=matches)
    image = Image.open(output).convert("RGB")
    draw_spotlight(image, matchday_spotlight(insights, matches))
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
