#!/usr/bin/env python3
"""Coleta e publica o painel da Copa do Brasil 2026."""

from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "copa_do_brasil_2026.json"
OUTPUT = ROOT / "copa-do-brasil" / "index.html"
SITE_URL = "https://felandim.github.io"
TABLE_ID = "11c5766c-f8f6-4e1b-b5e0-7309f67b54e9"
API = f"https://api.globoesporte.globo.com/tabela/{TABLE_ID}/fase"
SOURCE = "https://ge.globo.com/futebol/copa-do-brasil/"

PHASES = [
    ("primeira-fase-copa-do-brasil-2026", "Primeira fase"),
    ("segunda-fase-copa-do-brasil-2026", "Segunda fase"),
    ("terceira-fase-copa-do-brasil-2026", "Terceira fase"),
    ("quarta-fase-copa-do-brasil-2026", "Quarta fase"),
    ("quinta-fase-copa-do-brasil-2026", "Quinta fase"),
    ("oitavas-de-final-copa-do-brasil-2026", "Oitavas de final"),
    ("quartas-de-final-copa-do-brasil-2026", "Quartas de final"),
    ("semifinal-copa-do-brasil-2026", "Semifinais"),
    ("final-copa-do-brasil-2026", "Final"),
]


def esc(value: Any, quote: bool = False) -> str:
    return html.escape(str(value or ""), quote=quote)


def fetch(url: str, attempts: int = 3) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (Rodada a Rodada)"})
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=35) as response:
                return response.read()
        except Exception as error:  # pragma: no cover - depende da rede
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Falha ao consultar {url}: {last_error}")


def fetch_json(url: str) -> dict[str, Any]:
    return json.loads(fetch(url).decode("utf-8"))


def team(team_data: dict[str, Any] | None) -> dict[str, Any]:
    team_data = team_data or {}
    return {
        "id": team_data.get("id"),
        "name": team_data.get("nome_popular") or team_data.get("label") or "A definir",
        "short": team_data.get("sigla") or "",
        "crest": team_data.get("escudo") or "",
    }


def normalize_game(game: dict[str, Any], phase: str, tie: str = "") -> dict[str, Any]:
    teams = game.get("equipes") or {}
    home_score = game.get("placar_oficial_mandante")
    away_score = game.get("placar_oficial_visitante")
    penalties = None
    if game.get("placar_penaltis_mandante") is not None:
        penalties = [game.get("placar_penaltis_mandante"), game.get("placar_penaltis_visitante")]
    transmission = game.get("transmissao") or {}
    return {
        "id": game.get("id"),
        "phase": phase,
        "tie": tie,
        "date": game.get("data_realizacao") or "",
        "time": game.get("hora_realizacao") or "",
        "venue": (game.get("sede") or {}).get("nome_popular") or "",
        "home": team(teams.get("mandante")),
        "away": team(teams.get("visitante")),
        "home_score": home_score,
        "away_score": away_score,
        "penalties": penalties,
        "completed": home_score is not None and away_score is not None,
        "url": transmission.get("url") or "",
    }


def phase_games(payload: dict[str, Any], phase_name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    games: list[dict[str, Any]] = []
    ties: list[dict[str, Any]] = []
    for section in payload.get("secao", []):
        for bracket in section.get("chave", []):
            tie_games = [normalize_game(game, phase_name, bracket.get("nome", "")) for game in bracket.get("jogos", [])]
            games.extend(tie_games)
            ties.append({"name": bracket.get("nome", phase_name), "games": tie_games})
    return games, ties


def parse_scorers(page: str) -> list[dict[str, Any]]:
    scorers = []
    wrappers = re.findall(r'<div class="ranking-item-wrapper">(.*?)(?=<div class="ranking-item-wrapper">|</section>)', page, re.S)
    for block in wrappers:
        name = re.search(r'<div class="jogador-nome">\s*(.*?)\s*</div>', block, re.S)
        position = re.search(r'<div class="jogador-posicao">\s*(.*?)\s*</div>', block, re.S)
        goals = re.search(r'<div class="jogador-gols">\s*(\d+)\s*</div>', block, re.S)
        crest_match = re.search(r'<div class="jogador-escudo">.*?<img[^>]+src="([^"]+)"[^>]+alt="([^"]*)"', block, re.S)
        if name and goals:
            scorers.append({
                "name": html.unescape(re.sub(r"<[^>]+>", "", name.group(1))).strip(),
                "position": html.unescape(position.group(1)).strip() if position else "",
                "goals": int(goals.group(1)),
                "team": html.unescape(crest_match.group(2)).strip() if crest_match else "",
                "crest": crest_match.group(1) if crest_match else "",
            })
    return scorers


def collect() -> dict[str, Any]:
    phases = []
    all_games = []
    edition = None
    for slug, name in PHASES:
        payload = fetch_json(f"{API}/{slug}/classificacao/")
        games, ties = phase_games(payload, name)
        phases.append({"slug": slug, "name": name, "games": games, "ties": ties})
        all_games.extend(games)
        edition = edition or payload.get("edicao")

    participants: dict[str, dict[str, Any]] = {}
    for game in all_games:
        for side in (game["home"], game["away"]):
            if side["id"] and side["name"] != "A definir":
                participants[str(side["id"])] = side
    edition = edition or {}
    return {
        "season": 2026,
        "competition": edition.get("nome", "Copa do Brasil 2026"),
        "source": SOURCE,
        "start_date": edition.get("data_inicio", "2026-02-17"),
        "end_date": edition.get("data_fim", "2026-12-06"),
        "regulation": edition.get("regulamento", ""),
        "phases": phases,
        "matches": all_games,
        "participants": sorted(participants.values(), key=lambda item: item["name"]),
        "scorers": parse_scorers(fetch(SOURCE).decode("utf-8", "ignore")),
    }


def date_label(value: str) -> str:
    if not value:
        return "A definir"
    raw = value[:10]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return raw


def crest(team_data: dict[str, Any]) -> str:
    image = team_data.get("crest", "")
    if image.startswith("//"):
        image = "https:" + image
    picture = f'<img src="{esc(image, True)}" alt="" loading="lazy" width="34" height="34">' if image else '<span class="lib-crest-placeholder">·</span>'
    return f'<span class="lib-team">{picture}<span>{esc(team_data["name"])}</span></span>'


def score(game: dict[str, Any]) -> str:
    if not game["completed"]:
        return game["time"] or "—"
    result = f'{game["home_score"]} × {game["away_score"]}'
    if game.get("penalties"):
        result += f'<small>pên. {game["penalties"][0]}–{game["penalties"][1]}</small>'
    return result


def render_phase_overview(phases: list[dict[str, Any]]) -> str:
    cards = []
    for phase in phases:
        dates = sorted(game["date"][:10] for game in phase["games"] if game["date"])
        period = "Datas a definir" if not dates else f"{date_label(dates[0])} — {date_label(dates[-1])}"
        completed = sum(1 for game in phase["games"] if game["completed"])
        cards.append(f'<article class="lib-group cdb-phase-card"><span>{len(phase["ties"])} confrontos</span><h3>{esc(phase["name"])}</h3><p>{period}</p><strong>{completed}/{len(phase["games"])} jogos concluídos</strong></article>')
    return "".join(cards)


def render_bracket(phases: list[dict[str, Any]]) -> str:
    columns = []
    for phase in phases[4:]:
        ties = []
        for tie in phase["ties"]:
            real_games = tie["games"]
            first = real_games[0] if real_games else None
            home = crest(first["home"]) if first else "A definir"
            away = crest(first["away"]) if first else "A definir"
            legs = " · ".join(score(game).replace("<small>", " (").replace("</small>", ")") for game in real_games)
            ties.append(f'<article class="lib-tie"><span>{esc(tie["name"])}</span>{home}{away}<b>{legs}</b></article>')
        columns.append(f'<section class="lib-bracket-column"><h3>{esc(phase["name"])}</h3>{"".join(ties)}</section>')
    return "".join(columns)


def render_games(games: list[dict[str, Any]]) -> str:
    ordered = sorted(games, key=lambda game: (game["date"] or "9999", game["time"], game["phase"], str(game.get("id") or "")))
    cards = []
    for game in ordered:
        details = f'<a href="{esc(game["url"], True)}" target="_blank" rel="noopener noreferrer">Detalhes ↗</a>' if game["url"] else ""
        cards.append(
            f'<article class="lib-game" data-phase="{esc(game["phase"], True)}" data-teams="{esc((game["home"]["name"] + " " + game["away"]["name"]).lower(), True)}">'
            f'<div><span>{esc(game["phase"])}</span><small>{esc(game["tie"])}</small></div>'
            f'<time>{date_label(game["date"])}<small>{esc(game["venue"] or "Local a definir")}</small></time>'
            f'<div class="lib-game-teams">{crest(game["home"])}<strong>{score(game)}</strong>{crest(game["away"])}</div>{details}</article>'
        )
    return "".join(cards)


def render_scorers(scorers: list[dict[str, Any]]) -> str:
    return "".join(
        f'<li><span>{index:02d}</span>{crest({"name": item["team"], "crest": item["crest"]})}<strong>{esc(item["name"])}</strong><small>{esc(item["position"])}</small><b>{item["goals"]} gols</b></li>'
        for index, item in enumerate(scorers[:20], 1)
    )


def render_participants(participants: list[dict[str, Any]]) -> str:
    return "".join(f'<li>{crest(item)}</li>' for item in participants)


def build_page(data: dict[str, Any]) -> str:
    completed = sum(1 for game in data["matches"] if game["completed"])
    upcoming = len(data["matches"]) - completed
    phase_options = "".join(f'<option value="{esc(phase["name"], True)}">{esc(phase["name"])}</option>' for phase in data["phases"])
    json_ld = json.dumps({"@context": "https://schema.org", "@type": "SportsEvent", "name": data["competition"], "startDate": data["start_date"], "endDate": data["end_date"], "url": f"{SITE_URL}/copa-do-brasil/"}, ensure_ascii=False, separators=(",", ":"))
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Copa do Brasil 2026: jogos, chaveamento e artilharia</title><meta name="description" content="Acompanhe as nove fases, todos os jogos, chaveamento, artilharia e 126 participantes da Copa do Brasil 2026."><meta name="theme-color" content="#17120a"><link rel="canonical" href="{SITE_URL}/copa-do-brasil/"><meta property="og:title" content="Copa do Brasil 2026 completa"><meta property="og:description" content="Fases, jogos, chaveamento e artilharia em uma única página."><meta property="og:url" content="{SITE_URL}/copa-do-brasil/"><meta property="og:type" content="website"><meta property="og:locale" content="pt_BR"><meta name="twitter:card" content="summary"><link rel="stylesheet" href="../style.css"><script type="application/ld+json">{json_ld}</script></head>
<body class="br-page lib-page cdb-page"><a class="skip-link" href="#conteudo">Pular para o conteúdo</a>
<header class="br-header"><div class="br-shell br-nav"><a class="br-brand" href="../index.html" aria-label="Rodada a Rodada — página inicial"><span>R/R</span><strong>Rodada a Rodada</strong></a><nav aria-label="Navegação principal"><a href="../brasileirao/classificacao-rodada-a-rodada.html">Brasileirão</a><a href="../libertadores/">Libertadores</a><a href="#fases">Fases</a><a href="#mata-mata">Mata-mata</a><a href="#jogos">Jogos</a><a href="#artilharia">Artilharia</a><a href="#participantes">Times</a></nav></div></header>
<main id="conteudo"><section class="lib-hero"><div class="br-shell lib-hero-grid"><div><p class="br-kicker">Copa do Brasil · 2026</p><h1>Do Brasil inteiro até a taça.</h1><p>As nove fases, os 155 jogos, o chaveamento e a corrida pela artilharia em um único painel.</p><div class="br-actions"><a class="br-button br-button-hot" href="#jogos">Ver todos os jogos</a><a class="br-button" href="#mata-mata">Abrir chaveamento</a></div></div><aside><span>Temporada</span><strong>2026</strong><p>17 de fevereiro — 6 de dezembro</p></aside></div></section>
<section class="lib-stats"><div class="br-shell"><article><strong>{len(data["participants"])}</strong><span>times participantes</span></article><article><strong>{len(data["matches"])}</strong><span>partidas previstas</span></article><article><strong>{completed}</strong><span>jogos concluídos</span></article><article><strong>{upcoming}</strong><span>a disputar</span></article></div></section>
<section class="br-section" id="fases"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Formato completo</p><h2>As nove fases</h2></div></div><div class="lib-groups cdb-phases">{render_phase_overview(data["phases"])}</div></div></section>
<section class="br-section lib-dark" id="mata-mata"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Dos 32 clubes à decisão</p><h2>Chaveamento principal</h2></div></div><div class="lib-bracket cdb-bracket">{render_bracket(data["phases"])}</div></div></section>
<section class="br-section" id="jogos"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Da primeira fase à final</p><h2>Todos os 155 jogos</h2></div></div><div class="lib-filters"><label>Fase<select id="lib-phase-filter"><option value="">Todas</option>{phase_options}</select></label><label>Buscar time<input id="lib-team-filter" type="search" placeholder="Ex.: Palmeiras"></label><span id="lib-result-count" aria-live="polite"></span></div><div class="lib-games" id="lib-games">{render_games(data["matches"])}</div><p class="lib-empty" id="lib-empty" hidden>Nenhuma partida encontrada.</p></div></section>
<section class="br-section lib-soft" id="artilharia"><div class="br-shell lib-two-cols"><div><p class="br-kicker">Goleadores</p><h2>Artilharia</h2><p>Os principais goleadores de todas as fases da Copa do Brasil 2026.</p></div><ol class="lib-scorers">{render_scorers(data["scorers"])}</ol></div></section>
<section class="br-section" id="participantes"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">De todos os estados</p><h2>Todos os participantes</h2></div></div><ul class="lib-participants">{render_participants(data["participants"])}</ul></div></section>
<section class="br-section lib-regulation" id="regulamento"><div class="br-shell lib-two-cols"><div><p class="br-kicker">Formato e calendário</p><h2>Como funciona</h2><dl>{''.join(f'<div><dt>{esc(phase["name"])}</dt><dd>{len(phase["games"])} jogos</dd></div>' for phase in data["phases"])}</dl></div><article><h3>Regulamento</h3><p>{esc(data["regulation"])}</p><p><a href="{SOURCE}" target="_blank" rel="noopener noreferrer">Fonte dos dados: ge ↗</a></p></article></div></section></main>
<footer class="br-footer"><div class="br-shell"><strong>Rodada a Rodada · Copa do Brasil 2026</strong><p>Dados públicos atualizados automaticamente a cada seis horas.</p><div><a href="../projetos.html">Projetos</a><a href="../about.html">Sobre Felipe Landim</a><a href="../privacy.html">Privacidade</a></div></div></footer><script src="../libertadores.js" defer></script><script src="../site.js" defer></script></body></html>'''


def write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def main() -> None:
    data = collect()
    assert len(data["phases"]) == 9, "A Copa do Brasil deve ter nove fases"
    assert len(data["matches"]) == 155, f'Esperadas 155 partidas, recebidas {len(data["matches"])}'
    assert len(data["participants"]) == 126, f'Esperados 126 times, recebidos {len(data["participants"])}'
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
    write_if_changed(DATA_FILE, serialized)
    write_if_changed(OUTPUT, build_page(data))
    print(f'Copa do Brasil 2026: {len(data["participants"])} times, {len(data["matches"])} jogos e {len(data["scorers"])} artilheiros.')


if __name__ == "__main__":
    main()
