#!/usr/bin/env python3
"""Adiciona métricas e histórico completo às páginas estáticas dos times."""

from __future__ import annotations

import html
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("BRASILEIRAO_ROOT", Path(__file__).resolve().parents[1]))
START = "<!-- team-details:start -->"
END = "<!-- team-details:end -->"
CSS = '<link rel="stylesheet" href="../../brasileirao-team-pages.css">'


def esc(value: Any) -> str:
    return html.escape(str(value))


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def pct(points: int, played: int) -> str:
    return (f"{points / (played * 3) * 100:.1f}%" if played else "0,0%").replace(".", ",")


def history_table(history: list[dict[str, int]]) -> str:
    rows, previous_position, previous_points = [], None, 0
    for item in history:
        position, points = int(item["position"]), int(item["points"])
        delta = 0 if previous_position is None else previous_position - position
        movement = f"▲ {delta}" if delta > 0 else f"▼ {abs(delta)}" if delta < 0 else "—"
        css = " up" if delta > 0 else " down" if delta < 0 else ""
        rows.append(
            f'<tr><td>{item["round"]}</td><td><strong>{position}º</strong></td>'
            f'<td class="movement{css}">{movement}</td><td>{points}</td><td>+{points - previous_points}</td></tr>'
        )
        previous_position, previous_points = position, points
    return "".join(rows)


def navigation(teams: list[str], current: str) -> str:
    index = teams.index(current)
    previous, next_team = teams[index - 1], teams[(index + 1) % len(teams)]
    return (
        '<nav class="team-page-nav" aria-label="Navegar entre times">'
        f'<a href="{slugify(previous)}.html">← {esc(previous)}</a>'
        '<a href="../index.html#times">Todos os times</a>'
        f'<a href="{slugify(next_team)}.html">{esc(next_team)} →</a></nav>'
    )


def details(profile: dict[str, Any], teams: list[str]) -> str:
    team, current, history = profile["team"], profile["current"], profile["history"]
    played = int(current["played"])
    best = min(item["position"] for item in history)
    worst = max(item["position"] for item in history)
    metrics = (
        ("Aproveitamento", pct(int(current["points"]), played), f"{played} jogos"),
        ("Gols marcados", current["gf"], f"{current['gf'] / played:.2f} por jogo" if played else "0 por jogo"),
        ("Gols sofridos", current["ga"], f"{current['ga'] / played:.2f} por jogo" if played else "0 por jogo"),
        ("Melhor posição", f"{best}º", f"Pior posição: {worst}º"),
    )
    cards = "".join(
        f'<article><span>{esc(label)}</span><strong>{esc(value)}</strong><small>{esc(note)}</small></article>'
        for label, value, note in metrics
    )
    return (
        START
        + '<section class="br-section team-details"><div class="br-shell">'
        + f'<header><div><p class="br-kicker">Raio-x da campanha</p><h2>{esc(team)} em números</h2>'
        + f'<p>Desempenho consolidado após {played} partidas.</p></div>'
        + '<a href="../classificacao-rodada-a-rodada.html">Ver classificação completa →</a></header>'
        + f'<div class="team-kpis">{cards}</div><div class="team-history">'
        + '<p class="br-kicker">Histórico completo</p><h2>Posição e pontos após cada rodada</h2>'
        + '<p>A variação compara a posição com a rodada anterior.</p>'
        + '<div class="br-table-wrap"><table class="br-table"><thead><tr>'
        + '<th>Rodada</th><th>Posição</th><th>Variação</th><th>Pontos</th><th>Na rodada</th>'
        + f'</tr></thead><tbody>{history_table(history)}</tbody></table></div></div>'
        + navigation(teams, team)
        + "</div></section>"
        + END
    )


def enhance(path: Path, profile: dict[str, Any], teams: list[str]) -> bool:
    original = path.read_text(encoding="utf-8")
    content = re.sub(re.escape(START) + r".*?" + re.escape(END), "", original, flags=re.DOTALL)
    if CSS not in content:
        content = content.replace("</head>", CSS + "</head>", 1)
    marker = '<section class="br-share-section">'
    if marker not in content:
        raise ValueError(f"Seção de compartilhamento não encontrada: {path}")
    content = content.replace(marker, details(profile, teams) + marker, 1)
    if content == original:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> None:
    insights = json.loads((ROOT / "data" / "brasileirao_2026_insights.json").read_text(encoding="utf-8"))
    profiles = insights["team_profiles"]
    teams = sorted(profile["team"] for profile in profiles.values())
    changed = 0
    for slug, profile in profiles.items():
        changed += enhance(ROOT / "brasileirao" / "times" / f"{slug}.html", profile, teams)
    print(f"Páginas de times enriquecidas: {len(profiles)} ({changed} alteradas).")


if __name__ == "__main__":
    main()
