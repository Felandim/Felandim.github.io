#!/usr/bin/env python3
"""Camada editorial para priorizar insights mais fortes no post diário."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from PIL import Image

import instagram_daily
import instagram_matchday


HIGH_PRIORITY_KINDS = {
    "leader", "g4", "z4", "upset", "g4_cluster", "z4_cluster",
}


def high_scoring_match_spotlight(matches: list[dict], minimum_goals: int = 5) -> dict | None:
    """Destaca o jogo mais goleador do dia quando o placar, por si só, já conta uma história forte."""
    candidates = []
    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if not score:
            continue
        total_goals = score[0] + score[1]
        if total_goals < minimum_goals:
            continue
        candidates.append((total_goals, abs(score[0] - score[1]), match))

    if not candidates:
        return None

    total_goals, _, match = max(
        candidates,
        key=lambda item: (item[0], -item[1], item[2].get("home", "")),
    )
    return {
        "kind": "goal_fest",
        "label": "CHUVA DE GOLS",
        "text": f"{match['home']} {match['score']} {match['away']} • {total_goals} gols",
        "caption": (
            f"Chuva de gols: {match['home']} {match['score']} {match['away']} "
            f"teve {total_goals} gols no placar."
        ),
        "home": match.get("home", ""),
        "away": match.get("away", ""),
        "score": match.get("score", ""),
        "goals": total_goals,
    }


def title_race_spotlight(
    insights: dict,
    maximum_gap: int = 3,
    minimum_teams: int = 3,
    minimum_round: int = 5,
) -> dict | None:
    """Detecta disputa de título comprimida entre vários times, não apenas 1º e 2º."""
    snapshot, latest = instagram_daily.current_snapshot(insights)
    round_number = int(latest.get("round") or snapshot.get("round") or 0)
    table = snapshot.get("table", [])
    if round_number < minimum_round or len(table) < minimum_teams:
        return None

    leader_points = table[0]["points"]
    contenders = [
        row for row in table
        if 0 <= leader_points - row["points"] <= maximum_gap
    ]
    if len(contenders) < minimum_teams:
        return None

    spread = leader_points - contenders[-1]["points"]
    teams = [row["team"] for row in contenders]
    gap_text = f"{spread} {'ponto' if spread == 1 else 'pontos'}"
    return {
        "kind": "title_cluster",
        "label": "TÍTULO EMBOLADO",
        "text": f"{len(contenders)} times separados por só {gap_text} no topo",
        "caption": (
            f"Briga pelo título: {len(contenders)} times estão separados por apenas {gap_text}; "
            f"{', '.join(teams)} formam o pelotão da frente."
        ),
        "count": len(contenders),
        "spread": spread,
        "teams": teams,
    }


def editorial_spotlight(insights: dict, matches: list[dict]) -> dict:
    """Mantém eventos factuais fortes e melhora apenas o fallback editorial."""
    base = instagram_matchday.matchday_spotlight(insights, matches)
    if base.get("kind") in HIGH_PRIORITY_KINDS or base.get("kind") == "delayed_match":
        return base
    return high_scoring_match_spotlight(matches) or title_race_spotlight(insights) or base


def _spotlight_sentence(spotlight: dict) -> str:
    """Transforma o destaque escolhido em uma única frase editorial para a legenda."""
    caption = (spotlight.get("caption") or "").strip()
    if caption:
        return caption

    text = (spotlight.get("text") or "").strip().rstrip(".")
    if not text:
        return ""
    label = (spotlight.get("label") or "Destaque").strip().capitalize()
    return f"{label}: {text}."


def build_caption(insights: dict, matches: list[dict]) -> str:
    """Cria legenda curta com uma história principal, sem empilhar insights concorrentes."""
    snapshot, latest = instagram_daily.current_snapshot(insights)
    table = snapshot["table"]
    spotlight = editorial_spotlight(insights, matches)
    story = _spotlight_sentence(spotlight)
    partial = " (parcial)" if latest.get("matches", 10) < 10 else ""

    lines = [
        story,
        f"Brasileirão {insights['season']} — rodada {latest['round']}{partial}.",
        "",
        f"Líder: {table[0]['team']} — {table[0]['points']} pts.",
        f"G4: {', '.join(row['team'] for row in table[:4])}.",
        f"Z4: {', '.join(row['team'] for row in table[-4:])}.",
        "",
        f"Mais números e evolução rodada a rodada: {instagram_daily.SITE_URL}",
        "",
        "#Brasileirao #Brasileirao2026 #FutebolBrasileiro #SerieA",
    ]
    return "\n".join(line for line in lines if line is not None)[:2200]


def render_card(
    insights: dict,
    matches: list[dict],
    output: Path = instagram_daily.DEFAULT_OUTPUT,
    now: datetime | None = None,
) -> Path:
    """Reaproveita o render existente e substitui apenas o bloco editorial quando necessário."""
    output = instagram_matchday.render_card(insights, matches, output, now=now)
    spotlight = editorial_spotlight(insights, matches)
    image = Image.open(output).convert("RGB")
    instagram_matchday.draw_spotlight(image, spotlight)
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
    matches = instagram_matchday.completed_matches_for_date(
        all_matches, instagram_matchday.publication_date()
    )

    if args.command == "render":
        print(render_card(insights, matches, args.output))
    else:
        print(build_caption(insights, matches))


if __name__ == "__main__":
    main()
