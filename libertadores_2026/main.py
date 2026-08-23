#!/usr/bin/env python3
"""Coleta e publica o painel da Libertadores 2026."""

from __future__ import annotations

import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "libertadores_2026.json"
OUTPUT = ROOT / "libertadores" / "index.html"
SITE_URL = "https://felandim.github.io"
TABLE_ID = "83ad0ca5-f84e-4906-9242-a40d6585ebca"
API = f"https://api.globoesporte.globo.com/tabela/{TABLE_ID}/fase"
SOURCE = "https://ge.globo.com/futebol/libertadores/"

PHASES = [
    ("primeira-fase-libertadores-2026", "Primeira fase"),
    ("segunda-fase-libertadores-2026", "Segunda fase"),
    ("terceira-fase-libertadores-2026", "Terceira fase"),
    ("fase-de-grupos-libertadores-2026", "Fase de grupos"),
    ("oitavas-de-final-libertadores-2026", "Oitavas de final"),
    ("quartas-de-final-libertadores-2026", "Quartas de final"),
    ("semifinal-libertadores-2026", "Semifinais"),
    ("final-libertadores-2026", "Final"),
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
        crest = re.search(r'<div class="jogador-escudo">.*?<img[^>]+src="([^"]+)"[^>]+alt="([^"]*)"', block, re.S)
        if name and goals:
            scorers.append({
                "name": html.unescape(re.sub(r"<[^>]+>", "", name.group(1))).strip(),
                "position": html.unescape(position.group(1)).strip() if position else "",
                "goals": int(goals.group(1)),
                "team": html.unescape(crest.group(2)).strip() if crest else "",
                "crest": crest.group(1) if crest else "",
            })
    return scorers


def collect() -> dict[str, Any]:
    raw = {slug: fetch_json(f"{API}/{slug}/classificacao/") for slug, _ in PHASES}
    group_payload = raw["fase-de-grupos-libertadores-2026"]
    group_games = []

    def collect_group(group: dict[str, Any]) -> dict[str, Any]:
        standings = [{
            "position": row["ordem"], "name": row["nome_popular"], "short": row.get("sigla", ""),
            "crest": row.get("escudo", ""), "points": row["pontos"], "played": row["jogos"],
            "wins": row["vitorias"], "draws": row["empates"], "losses": row["derrotas"],
            "gf": row["gols_pro"], "ga": row["gols_contra"], "gd": row["saldo_gols"],
        } for row in group["classificacao"]]
        return {"id": group["grupo_id"], "name": group["nome_grupo"], "standings": standings, "games": []}

    groups = [collect_group(group) for group in group_payload["grupos"]]

    def collect_round(task: tuple[int, dict[str, Any], int]) -> tuple[int, list[dict[str, Any]]]:
        group_index, group, round_number = task
        round_url = f"{API}/fase-de-grupos-libertadores-2026/rodada/{round_number}/grupo/{group['grupo_id']}/jogos/"
        round_payload = fetch_json(round_url)
        round_games = round_payload if isinstance(round_payload, list) else round_payload.get("jogos", [])
        games = []
        for game in round_games:
            normalized = normalize_game(game, "Fase de grupos", f"{group['nome_grupo']} · Rodada {round_number}")
            normalized["round"] = round_number
            games.append(normalized)
        return group_index, games

    tasks = [(index, group, round_number) for index, group in enumerate(group_payload["grupos"]) for round_number in range(1, 7)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        rounds = list(executor.map(collect_round, tasks))
    for group_index, games in rounds:
        groups[group_index]["games"].extend(games)
    for group in groups:
        group_games.extend(group["games"])

    phases = []
    all_games = []
    for slug, name in PHASES:
        if slug == "fase-de-grupos-libertadores-2026":
            games, ties = group_games, []
        else:
            games, ties = phase_games(raw[slug], name)
        phases.append({"slug": slug, "name": name, "games": games, "ties": ties})
        all_games.extend(games)

    participants: dict[str, dict[str, Any]] = {}
    for game in all_games:
        for side in (game["home"], game["away"]):
            if side["id"] and side["name"] != "A definir":
                participants[str(side["id"])] = side
    edition = group_payload["edicao"]
    return {
        "season": 2026,
        "competition": edition["nome"],
        "source": SOURCE,
        "start_date": edition["data_inicio"],
        "end_date": edition["data_fim"],
        "regulation": edition["regulamento"],
        "groups": groups,
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


def render_groups(groups: list[dict[str, Any]]) -> str:
    cards = []
    for group in groups:
        rows = "".join(
            f'<tr class="{"lib-qualified" if row["position"] <= 2 else ""}"><td>{row["position"]}</td><th>{crest(row)}</th><td><strong>{row["points"]}</strong></td><td>{row["played"]}</td><td>{row["wins"]}</td><td>{row["draws"]}</td><td>{row["losses"]}</td><td>{row["gd"]:+d}</td></tr>'
            for row in group["standings"]
        )
        cards.append(f'<article class="lib-group"><h3>{esc(group["name"])}</h3><div class="lib-table-scroll"><table><thead><tr><th>#</th><th>Time</th><th>PTS</th><th>J</th><th>V</th><th>E</th><th>D</th><th>SG</th></tr></thead><tbody>{rows}</tbody></table></div></article>')
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
            f'<div class="lib-game-teams">{crest(game["home"])}<strong>{score(game)}</strong>{crest(game["away"])}</div>'
            f'{details}</article>'
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
    json_ld = json.dumps({"@context": "https://schema.org", "@type": "SportsEvent", "name": data["competition"], "startDate": data["start_date"], "endDate": data["end_date"], "url": f"{SITE_URL}/libertadores/"}, ensure_ascii=False, separators=(",", ":"))
    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Libertadores 2026: tabela, jogos, mata-mata e artilharia</title><meta name="description" content="Acompanhe grupos, classificação, todos os jogos, mata-mata, artilharia e participantes da Libertadores 2026."><meta name="theme-color" content="#071c18"><link rel="canonical" href="{SITE_URL}/libertadores/"><meta property="og:title" content="Libertadores 2026 completa"><meta property="og:description" content="Tabela, jogos, mata-mata e artilharia em uma única página."><meta property="og:url" content="{SITE_URL}/libertadores/"><meta property="og:type" content="website"><meta property="og:locale" content="pt_BR"><meta name="twitter:card" content="summary"><link rel="stylesheet" href="../style.css"><script type="application/ld+json">{json_ld}</script></head>
<body class="br-page lib-page"><a class="skip-link" href="#conteudo">Pular para o conteúdo</a>
<header class="br-header"><div class="br-shell br-nav"><a class="br-brand" href="../index.html" aria-label="Rodada a Rodada — página inicial"><span>R/R</span><strong>Rodada a Rodada</strong></a><nav aria-label="Navegação principal"><a href="../brasileirao/classificacao-rodada-a-rodada.html">Brasileirão</a><a href="../copa-do-brasil/">Copa do Brasil</a><a href="#grupos">Grupos</a><a href="#mata-mata">Mata-mata</a><a href="#jogos">Jogos</a><a href="#artilharia">Artilharia</a><a href="#participantes">Times</a></nav></div></header>
<main id="conteudo"><section class="lib-hero"><div class="br-shell lib-hero-grid"><div><p class="br-kicker">CONMEBOL Libertadores · 2026</p><h1>A América inteira em uma página.</h1><p>Classificação dos oito grupos, chaveamento, todos os jogos e a corrida pela artilharia.</p><div class="br-actions"><a class="br-button br-button-hot" href="#jogos">Ver todos os jogos</a><a class="br-button" href="#mata-mata">Abrir mata-mata</a></div></div><aside><span>Temporada</span><strong>2026</strong><p>3 de fevereiro — 28 de novembro</p></aside></div></section>
<section class="lib-stats"><div class="br-shell"><article><strong>{len(data["participants"])}</strong><span>times participantes</span></article><article><strong>{len(data["matches"])}</strong><span>partidas previstas</span></article><article><strong>{completed}</strong><span>jogos concluídos</span></article><article><strong>{upcoming}</strong><span>a disputar</span></article></div></section>
<section class="br-section" id="grupos"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Fase de grupos</p><h2>Classificação completa</h2></div><p class="lib-legend"><i></i> Classificados às oitavas</p></div><div class="lib-groups">{render_groups(data["groups"])}</div></div></section>
<section class="br-section lib-dark" id="mata-mata"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Caminho até a taça</p><h2>Mata-mata</h2></div></div><div class="lib-bracket">{render_bracket(data["phases"])}</div></div></section>
<section class="br-section" id="jogos"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Da primeira fase à final</p><h2>Todos os 155 jogos</h2></div></div><div class="lib-filters"><label>Fase<select id="lib-phase-filter"><option value="">Todas</option>{phase_options}</select></label><label>Buscar time<input id="lib-team-filter" type="search" placeholder="Ex.: Flamengo"></label><span id="lib-result-count" aria-live="polite"></span></div><div class="lib-games" id="lib-games">{render_games(data["matches"])}</div><p class="lib-empty" id="lib-empty" hidden>Nenhuma partida encontrada.</p></div></section>
<section class="br-section lib-soft" id="artilharia"><div class="br-shell lib-two-cols"><div><p class="br-kicker">Goleadores</p><h2>Artilharia</h2><p>Os principais goleadores de todas as fases da Libertadores 2026.</p></div><ol class="lib-scorers">{render_scorers(data["scorers"])}</ol></div></section>
<section class="br-section" id="participantes"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Mapa da competição</p><h2>Todos os participantes</h2></div></div><ul class="lib-participants">{render_participants(data["participants"])}</ul></div></section>
<section class="br-section lib-regulation" id="regulamento"><div class="br-shell lib-two-cols"><div><p class="br-kicker">Formato e calendário</p><h2>Como funciona</h2><dl><div><dt>Fases preliminares</dt><dd>3 de fevereiro a 12 de março</dd></div><div><dt>Fase de grupos</dt><dd>7 de abril a 28 de maio</dd></div><div><dt>Oitavas de final</dt><dd>11 a 20 de agosto</dd></div><div><dt>Quartas de final</dt><dd>8 a 17 de setembro</dd></div><div><dt>Semifinais</dt><dd>14 a 22 de outubro</dd></div><div><dt>Final</dt><dd>28 de novembro</dd></div></dl></div><article><h3>Regulamento</h3><p>{esc(data["regulation"])}</p><p><a href="{SOURCE}" target="_blank" rel="noopener noreferrer">Fonte dos dados: ge ↗</a></p></article></div></section></main>
<footer class="br-footer"><div class="br-shell"><strong>Rodada a Rodada · Libertadores 2026</strong><p>Dados públicos atualizados automaticamente a cada seis horas.</p><div><a href="../projetos.html">Projetos</a><a href="../about.html">Sobre Felipe Landim</a><a href="../privacy.html">Privacidade</a></div></div></footer><script src="../libertadores.js" defer></script><script src="../site.js" defer></script></body></html>'''


def write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def main() -> None:
    data = collect()
    assert len(data["groups"]) == 8, "A Libertadores deve ter oito grupos"
    assert sum(len(group["games"]) for group in data["groups"]) == 96, "Esperadas 96 partidas na fase de grupos"
    assert len(data["matches"]) == 155, f'Esperadas 155 partidas, recebidas {len(data["matches"])}'
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
    write_if_changed(DATA_FILE, serialized)
    write_if_changed(OUTPUT, build_page(data))
    print(f'Libertadores 2026: {len(data["participants"])} times, {len(data["matches"])} jogos e {len(data["scorers"])} artilheiros.')


if __name__ == "__main__":
    main()
