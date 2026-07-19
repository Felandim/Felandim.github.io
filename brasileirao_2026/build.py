#!/usr/bin/env python3
"""Gera o produto editorial Rodada a Rodada a partir dos dados da Série A."""

from __future__ import annotations

import html
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from og_cards import build_og_cards

ROOT = Path(__file__).resolve().parents[1]
MATCHES_FILE = ROOT / "data" / "serie_a_2026.json"
SCORERS_FILE = ROOT / "data" / "serie_a_2026_scorers.json"
INSIGHTS_FILE = ROOT / "data" / "brasileirao_2026_insights.json"
OUTPUT = ROOT / "brasileirao"
SITE_URL = "https://felandim.github.io"
SEASON = 2026


def esc(value: Any, quote: bool = False) -> str:
    return html.escape(str(value), quote=quote)


def format_count(value: int, singular: str, plural: str | None = None) -> str:
    return f"{value} {singular if value == 1 else plural or singular + 's'}"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def parse_score(value: str) -> tuple[int, int] | None:
    match = re.match(r"^(\d+)\s*x\s*(\d+)", value or "")
    return (int(match.group(1)), int(match.group(2))) if match else None


def blank_stats(team: str) -> dict[str, Any]:
    return {"team": team, "points": 0, "played": 0, "wins": 0, "draws": 0,
            "losses": 0, "gf": 0, "ga": 0, "gd": 0}


def apply_match(stats: dict[str, dict[str, Any]], match: dict[str, Any]) -> None:
    score = parse_score(match.get("score", ""))
    if not score:
        return
    home_goals, away_goals = score
    home, away = stats[match["home"]], stats[match["away"]]
    for row, scored, conceded in ((home, home_goals, away_goals), (away, away_goals, home_goals)):
        row["played"] += 1
        row["gf"] += scored
        row["ga"] += conceded
        row["gd"] = row["gf"] - row["ga"]
    if home_goals > away_goals:
        home["wins"] += 1; home["points"] += 3; away["losses"] += 1
    elif away_goals > home_goals:
        away["wins"] += 1; away["points"] += 3; home["losses"] += 1
    else:
        home["draws"] += 1; away["draws"] += 1
        home["points"] += 1; away["points"] += 1


def ranked(stats: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(stats.values(), key=lambda r: (-r["points"], -r["wins"], -r["gd"], -r["gf"], r["team"]))
    return [{**row, "position": index} for index, row in enumerate(rows, 1)]


def load_data() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    matches = json.loads(MATCHES_FILE.read_text(encoding="utf-8"))["matches"]
    scorer_data = {"matches": {}}
    if SCORERS_FILE.exists():
        scorer_data = json.loads(SCORERS_FILE.read_text(encoding="utf-8"))
    return matches, scorer_data



def streak_summary(results: list[str]) -> dict[str, int]:
    longest_unbeaten = longest_wins = current_unbeaten = current_wins = 0
    for result in results:
        if result != "D":
            current_unbeaten += 1
            longest_unbeaten = max(longest_unbeaten, current_unbeaten)
        else:
            current_unbeaten = 0
        if result == "V":
            current_wins += 1
            longest_wins = max(longest_wins, current_wins)
        else:
            current_wins = 0
    return {
        "longest_unbeaten": longest_unbeaten,
        "longest_wins": longest_wins,
        "current_unbeaten": current_unbeaten,
        "current_wins": current_wins,
    }

def build_insights(matches: list[dict[str, Any]], scorer_data: dict[str, Any]) -> dict[str, Any]:
    teams = sorted({match[side] for match in matches for side in ("home", "away")})
    completed = [match for match in matches if parse_score(match.get("score", ""))]
    current_round = max((int(match["round"]) for match in completed), default=0)
    stats = {team: blank_stats(team) for team in teams}
    snapshots: list[dict[str, Any]] = []
    rounds: list[dict[str, Any]] = []
    previous_positions = {team: 0 for team in teams}
    previous_leader = ""

    scorer_totals: dict[str, dict[str, Any]] = {}
    scorer_history: list[dict[str, Any]] = []
    scorer_matches = scorer_data.get("matches", {})

    for number in range(1, current_round + 1):
        round_matches = [m for m in completed if int(m["round"]) == number]
        goals = 0
        for match in round_matches:
            apply_match(stats, match)
            score = parse_score(match["score"])
            goals += sum(score or (0, 0))
            scorers = scorer_matches.get(match.get("url", ""), {})
            for side in ("home", "away"):
                team = match[side]
                for scorer in scorers.get(side, []):
                    if scorer.get("own_goal"):
                        continue
                    name = scorer["name"]
                    row = scorer_totals.setdefault(name, {"name": name, "team": team, "goals": 0})
                    row["team"] = team
                    row["goals"] += int(scorer.get("goals", 1))

        table = ranked(stats)
        positions = {row["team"]: row["position"] for row in table}
        movement = {team: (previous_positions[team] - positions[team]) if previous_positions[team] else 0 for team in teams}
        rise_value = max(movement.values(), default=0)
        fall_value = min(movement.values(), default=0)
        biggest_win = None
        for match in round_matches:
            home_goals, away_goals = parse_score(match["score"]) or (0, 0)
            margin = abs(home_goals - away_goals)
            if biggest_win is None or margin > biggest_win["margin"]:
                winner = match["home"] if home_goals > away_goals else match["away"] if away_goals > home_goals else "Empate"
                biggest_win = {"winner": winner, "score": match["score"], "home": match["home"], "away": match["away"], "margin": margin}
        current_g4 = {team for team, pos in positions.items() if pos <= 4}
        current_z4 = {team for team, pos in positions.items() if pos >= 17}
        old_g4 = {team for team, pos in previous_positions.items() if pos and pos <= 4}
        old_z4 = {team for team, pos in previous_positions.items() if pos and pos >= 17}
        leader = table[0]["team"] if table else ""
        rounds.append({
            "round": number,
            "matches": len(round_matches),
            "goals": goals,
            "leader": leader,
            "leader_changed": bool(previous_leader and leader != previous_leader),
            "previous_leader": previous_leader,
            "biggest_rise": {"teams": sorted(team for team, value in movement.items() if value == rise_value and value > 0), "places": max(rise_value, 0)},
            "biggest_fall": {"teams": sorted(team for team, value in movement.items() if value == fall_value and value < 0), "places": abs(min(fall_value, 0))},
            "g4_in": sorted(current_g4 - old_g4), "g4_out": sorted(old_g4 - current_g4),
            "z4_in": sorted(current_z4 - old_z4), "z4_out": sorted(old_z4 - current_z4),
            "biggest_win": biggest_win,
        })
        snapshots.append({"round": number, "table": table})
        scorer_history.append({
            "round": number,
            "ranking": sorted(scorer_totals.values(), key=lambda r: (-r["goals"], r["name"]))
        })
        previous_positions = positions
        previous_leader = leader

    history_by_team: dict[str, list[dict[str, int]]] = {team: [] for team in teams}
    for snapshot in snapshots:
        for row in snapshot["table"]:
            history_by_team[row["team"]].append({"round": snapshot["round"], "position": row["position"], "points": row["points"]})

    team_profiles: dict[str, dict[str, Any]] = {}
    current_table = snapshots[-1]["table"] if snapshots else []
    for team in teams:
        team_matches = sorted((m for m in completed if team in (m["home"], m["away"])), key=lambda m: int(m["round"]))
        home_stats, away_stats = blank_stats(team), blank_stats(team)
        for match in team_matches:
            target = home_stats if match["home"] == team else away_stats
            opponent = blank_stats("opponent")
            temp = {team: target, match["away"] if match["home"] == team else match["home"]: opponent}
            apply_match(temp, match)
        last_five = []
        for match in team_matches[-5:]:
            home_goals, away_goals = parse_score(match["score"]) or (0, 0)
            is_home = match["home"] == team
            team_goals, opponent_goals = (home_goals, away_goals) if is_home else (away_goals, home_goals)
            last_five.append({"round": match["round"], "opponent": match["away"] if is_home else match["home"], "venue": "Casa" if is_home else "Fora", "score": match["score"], "result": "V" if team_goals > opponent_goals else "D" if team_goals < opponent_goals else "E"})
        current = next((row for row in current_table if row["team"] == team), blank_stats(team))
        results = []
        for match in team_matches:
            home_goals, away_goals = parse_score(match["score"]) or (0, 0)
            team_goals, opponent_goals = (home_goals, away_goals) if match["home"] == team else (away_goals, home_goals)
            results.append("V" if team_goals > opponent_goals else "D" if team_goals < opponent_goals else "E")
        team_profiles[slugify(team)] = {
            "team": team,
            "current": current,
            "home": home_stats,
            "away": away_stats,
            "last_five": last_five,
            "history": history_by_team[team],
            "streaks": streak_summary(results),
        }

    return {
        "season": SEASON,
        "current_round": current_round,
        "teams": teams,
        "snapshots": snapshots,
        "rounds": rounds,
        "scorers": scorer_history,
        "team_profiles": team_profiles,
        "scorer_coverage": {"completed_matches": len(completed), "matches_with_scorers": sum(1 for m in completed if m.get("url") in scorer_matches)},
    }


def nav(prefix: str = "../", current: str = "") -> str:
    links = [
        ("classificacao", f"{prefix}brasileirao/classificacao-rodada-a-rodada.html", "Classificação"),
        ("artilharia", f"{prefix}brasileirao/artilharia-rodada-a-rodada.html", "Artilharia"),
        ("comparador", f"{prefix}brasileirao/comparador-times.html", "Comparar"),
        ("rankings", f"{prefix}brasileirao/rankings-recordes.html", "Rankings"),
        ("times", f"{prefix}brasileirao/#times", "Times"),
        ("rodadas", f"{prefix}brasileirao/#rodadas", "Rodadas"),
        ("portfolio", f"{prefix}projetos.html", "Portfólio"),
    ]
    items_list = []
    for key, href, label in links:
        current_attribute = ' aria-current="page"' if key == current else ""
        items_list.append(f'<a href="{href}"{current_attribute}>{label}</a>')
    items = "".join(items_list)
    return f'<header class="br-header"><div class="br-shell br-nav"><a class="br-brand" href="{prefix}index.html" aria-label="Rodada a Rodada — página inicial"><span>R/R</span><strong>Rodada a Rodada</strong></a><nav aria-label="Navegação principal">{items}</nav></div></header>'


def footer(prefix: str = "../") -> str:
    return f'<footer class="br-footer"><div class="br-shell"><strong>Rodada a Rodada · Brasileirão {SEASON}</strong><p>Leitura independente construída com resultados públicos. Critérios: pontos, vitórias, saldo de gols e gols marcados.</p><div><a href="{prefix}projetos.html">Projetos</a><a href="{prefix}about.html">Sobre Felipe Landim</a><a href="{prefix}privacy.html">Privacidade</a></div></div></footer>'


def head(
    title: str,
    description: str,
    canonical: str,
    depth: str = "../",
    social_image: str = f"{SITE_URL}/assets/og/rodada-a-rodada.png",
    social_image_alt: str = "Rodada a Rodada — Brasileirão 2026 em números",
) -> str:
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(description, True)}"><meta name="theme-color" content="#101714"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="pt_BR"><meta property="og:title" content="{esc(title, True)}"><meta property="og:description" content="{esc(description, True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{social_image}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{esc(social_image_alt, True)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title, True)}"><meta name="twitter:description" content="{esc(description, True)}"><meta name="twitter:image" content="{social_image}"><meta name="twitter:image:alt" content="{esc(social_image_alt, True)}"><link rel="stylesheet" href="{depth}style.css"></head>'''


def page(title: str, description: str, canonical: str, content: str, *, depth: str = "../", current: str = "", body_class: str = "br-page", script: bool = False, social_image: str = f"{SITE_URL}/assets/og/rodada-a-rodada.png", social_image_alt: str = "Rodada a Rodada — Brasileirão 2026 em números") -> str:
    script_tag = f'<script src="{depth}brasileirao.js" defer></script>' if script else ""
    return f'{head(title, description, canonical, depth, social_image, social_image_alt)}<body class="{body_class}"><a class="skip-link" href="#conteudo">Pular para o conteúdo</a>{nav(depth, current)}<main id="conteudo">{content}</main>{footer(depth)}{script_tag}<script src="{depth}site.js" defer></script></body></html>\n'


def line_chart(history: list[dict[str, Any]], label: str) -> str:
    if not history:
        return ""
    width, height, pad = 760, 300, 32
    points = []
    for index, row in enumerate(history):
        x = pad + index * (width - 2 * pad) / max(len(history) - 1, 1)
        y = pad + (row["position"] - 1) * (height - 2 * pad) / 19
        points.append(f"{x:.1f},{y:.1f}")
    path_points = " ".join(points)
    last_x, last_y = points[-1].split(",")
    return f'<svg class="br-line-chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label, True)}"><line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}"/><line x1="{pad}" y1="{pad}" x2="{width-pad}" y2="{pad}"/><line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}"/><text x="4" y="{pad+5}">1º</text><text x="4" y="{height-pad+5}">20º</text><polyline points="{path_points}"/><circle cx="{last_x}" cy="{last_y}" r="7"/></svg>'


def table_html(rows: list[dict[str, Any]], limit: int | None = None, team_prefix: str = "times/") -> str:
    body = []
    for row in rows[:limit]:
        zone = " g4" if row["position"] <= 4 else " z4" if row["position"] >= 17 else ""
        body.append(f'<tr class="{zone.strip()}"><td><span class="br-pos{zone}">{row["position"]}</span></td><th scope="row"><a href="{team_prefix}{slugify(row["team"])}.html">{esc(row["team"])}</a></th><td>{row["points"]}</td><td>{row["played"]}</td><td>{row["wins"]}</td><td>{row["draws"]}</td><td>{row["losses"]}</td><td>{row["gd"]:+d}</td></tr>')
    return '<div class="br-table-wrap"><table class="br-table" data-standings-table><thead><tr><th>Pos.</th><th>Time</th><th>Pts</th><th>J</th><th>V</th><th>E</th><th>D</th><th>SG</th></tr></thead><tbody>' + "".join(body) + '</tbody></table></div>'



def rankings_data(insights: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    profiles = list(insights["team_profiles"].items())

    def row(slug: str, profile: dict[str, Any], value: int, detail: str) -> dict[str, Any]:
        return {"slug": slug, "team": profile["team"], "value": value, "detail": detail}

    attack = sorted(
        (row(slug, profile, profile["current"]["gf"], format_count(profile["current"]["played"], "jogo")) for slug, profile in profiles),
        key=lambda item: (-item["value"], item["team"]),
    )
    defense = sorted(
        (row(slug, profile, profile["current"]["ga"], format_count(profile["current"]["played"], "jogo")) for slug, profile in profiles),
        key=lambda item: (item["value"], item["team"]),
    )
    home = sorted(
        (row(slug, profile, profile["home"]["points"], f'{format_count(profile["home"]["wins"], "vitória", "vitórias")} · saldo {profile["home"]["gd"]:+d}') for slug, profile in profiles),
        key=lambda item: (-item["value"], item["team"]),
    )
    away = sorted(
        (row(slug, profile, profile["away"]["points"], f'{format_count(profile["away"]["wins"], "vitória", "vitórias")} · saldo {profile["away"]["gd"]:+d}') for slug, profile in profiles),
        key=lambda item: (-item["value"], item["team"]),
    )
    unbeaten = sorted(
        (row(slug, profile, profile["streaks"]["longest_unbeaten"], f'atual: {format_count(profile["streaks"]["current_unbeaten"], "jogo")}') for slug, profile in profiles),
        key=lambda item: (-item["value"], item["team"]),
    )
    wins = sorted(
        (row(slug, profile, profile["streaks"]["longest_wins"], f'atual: {format_count(profile["streaks"]["current_wins"], "jogo")}') for slug, profile in profiles),
        key=lambda item: (-item["value"], item["team"]),
    )
    return {"attack": attack, "defense": defense, "home": home, "away": away, "unbeaten": unbeaten, "wins": wins}


def record_preview(rankings: dict[str, list[dict[str, Any]]]) -> str:
    items = [
        ("Melhor ataque", rankings["attack"][0], "gol", "gols"),
        ("Melhor defesa", rankings["defense"][0], "gol sofrido", "gols sofridos"),
        ("Melhor mandante", rankings["home"][0], "ponto em casa", "pontos em casa"),
        ("Melhor visitante", rankings["away"][0], "ponto fora", "pontos fora"),
    ]
    return "".join(
        f'<article><span>{label}</span><strong>{esc(item["team"])}</strong><b>{format_count(item["value"], singular, plural)}</b></article>'
        for label, item, singular, plural in items
    )


def rankings_content(insights: dict[str, Any]) -> str:
    rankings = rankings_data(insights)
    categories = [
        ("Melhores ataques", "Gols marcados", rankings["attack"], "gol", "gols"),
        ("Melhores defesas", "Menos gols sofridos", rankings["defense"], "gol sofrido", "gols sofridos"),
        ("Força em casa", "Pontos como mandante", rankings["home"], "ponto", "pontos"),
        ("Força fora", "Pontos como visitante", rankings["away"], "ponto", "pontos"),
        ("Maiores invencibilidades", "Maior sequência sem derrota", rankings["unbeaten"], "jogo", "jogos"),
        ("Sequências de vitórias", "Maior série de vitórias", rankings["wins"], "jogo", "jogos"),
    ]
    leaders = "".join(
        f'<article><span>{title}</span><strong>{esc(rows[0]["team"])}</strong><b>{format_count(rows[0]["value"], singular, plural)}</b><small>{subtitle}</small></article>'
        for title, subtitle, rows, singular, plural in categories
    )
    lists = []
    for title, subtitle, rows, singular, plural in categories:
        items = "".join(
            f'<li><span>{position:02d}</span><a href="times/{item["slug"]}.html">{esc(item["team"])}</a><small>{esc(item["detail"])}</small><strong>{format_count(item["value"], singular, plural)}</strong></li>'
            for position, item in enumerate(rows[:5], 1)
        )
        lists.append(f'<article class="br-record-ranking"><p class="br-kicker">{esc(subtitle)}</p><h2>{esc(title)}</h2><ol>{items}</ol></article>')
    return f'''<section class="br-page-hero br-record-hero"><div class="br-shell"><p class="br-kicker">Rankings e recordes</p><h1>Quem domina cada recorte do campeonato?</h1><p>Ataque, defesa, desempenho em casa e fora, invencibilidade e sequências de vitórias atualizados com os resultados do Brasileirão {SEASON}.</p></div></section><section class="br-section"><div class="br-shell"><div class="br-record-leaders">{leaders}</div><div class="br-section-head br-top-gap"><div><p class="br-kicker">Top 5 por categoria</p><h2>Os números por trás da tabela</h2></div></div><div class="br-record-rankings">{''.join(lists)}</div><p class="br-record-note">Os rankings usam somente partidas concluídas. Em caso de igualdade, os times são apresentados em ordem alfabética.</p></div></section>'''

def home_content(insights: dict[str, Any]) -> str:
    current = insights["snapshots"][-1]["table"]
    latest = insights["rounds"][-1]
    leader = current[0]
    top_scorer = insights["scorers"][-1]["ranking"][0] if insights["scorers"] and insights["scorers"][-1]["ranking"] else None
    scorer_text = f'{top_scorer["name"]}<small>{top_scorer["goals"]} gols · {top_scorer["team"]}</small>' if top_scorer else 'Em atualização<small>Autores dos gols sendo consolidados</small>'
    leader_length = len(leader["team"])
    leader_class = "br-cover-team-xlong" if leader_length > 12 else "br-cover-team-long" if leader_length > 9 else ""
    cards = "".join(f'<a class="br-team-chip" href="brasileirao/times/{slugify(team)}.html">{esc(team)}</a>' for team in insights["teams"])
    rankings = rankings_data(insights)
    return f'''<section class="br-hero"><div class="br-shell br-hero-grid"><div><p class="br-kicker">Brasileirão Série A · {SEASON}</p><h1>A tabela tem memória.</h1><p>Acompanhe quem subiu, quem caiu e como a disputa mudou a cada rodada.</p><div class="br-actions"><a class="br-button br-button-hot" href="brasileirao/classificacao-rodada-a-rodada.html">Explorar classificação</a><a class="br-button" href="brasileirao/rodadas/rodada-{insights['current_round']}.html">Ver a rodada {insights['current_round']}</a></div></div><div class="br-cover" aria-label="Resumo da temporada"><span>EDIÇÃO {insights['current_round']:02d}</span><strong class="{leader_class}">{leader['team']}</strong><p>líder com {leader['points']} pontos</p><b>20 TIMES<br>38 RODADAS<br>1 HISTÓRIA</b></div></div></section>
<section class="br-ticker"><div class="br-shell"><span>Rodada {insights['current_round']}</span><strong>{latest['goals']} gols</strong><strong>{latest['leader']} na liderança</strong><strong>{latest['matches']} jogos concluídos</strong></div></section>
<section class="br-section"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Painel da temporada</p><h2>O campeonato agora</h2></div><a href="brasileirao/classificacao-rodada-a-rodada.html">Ver evolução completa →</a></div><div class="br-dashboard"><article class="br-ranking-card"><span>Líder</span><strong>{leader['team']}</strong><b>{leader['points']} pts</b><small>{leader['wins']} vitórias · saldo {leader['gd']:+d}</small></article><article class="br-ranking-card br-ranking-card-hot"><span>Artilharia</span><strong>{scorer_text}</strong><a href="brasileirao/artilharia-rodada-a-rodada.html">Abrir corrida →</a></article><div class="br-table-card">{table_html(current, 6, 'brasileirao/times/')}<a href="brasileirao/classificacao-rodada-a-rodada.html">Tabela completa e rodada a rodada →</a></div></div></div></section>
<section class="br-record-preview"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Rankings atualizados</p><h2>Quem domina o campeonato?</h2></div><a href="brasileirao/rankings-recordes.html">Ver todos os rankings →</a></div><div class="br-record-preview-grid">{record_preview(rankings)}</div></div></section>
<section class="br-section br-section-dark"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">O que mudou</p><h2>Raio-x da rodada {latest['round']}</h2></div><a href="brasileirao/rodadas/rodada-{latest['round']}.html">Ler resumo completo →</a></div><div class="br-change-grid"><article><span>01</span><h3>Liderança</h3><p>{latest['leader']}{' assumiu a ponta.' if latest['leader_changed'] else ' manteve a ponta.'}</p></article><article><span>02</span><h3>Maior subida</h3><p>{', '.join(latest['biggest_rise']['teams']) or 'Sem mudança'} · {latest['biggest_rise']['places']} posições</p></article><article><span>03</span><h3>Z4</h3><p>Entraram: {', '.join(latest['z4_in']) or 'ninguém'}<br>Saíram: {', '.join(latest['z4_out']) or 'ninguém'}</p></article></div></div></section>
<section class="br-compare-promo"><div class="br-shell br-compare-promo-grid"><div><p class="br-kicker">Novo comparador</p><h2>{esc(leader['team'])} ou {esc(current[1]['team'])}: quem fez a melhor campanha?</h2><p>Coloque dois times frente a frente e acompanhe a disputa rodada a rodada.</p></div><a class="br-button" href="brasileirao/comparador-times.html">Comparar times</a></div></section>
<section class="br-section" id="times"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">20 trajetórias</p><h2>Escolha seu time</h2></div></div><div class="br-team-cloud">{cards}</div></div></section>
<section class="br-section br-round-index" id="rodadas"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Arquivo do campeonato</p><h2>Rodada por rodada</h2></div></div><div class="br-round-links">{''.join(f'<a href="brasileirao/rodadas/rodada-{n}.html"><span>{n:02d}</span>Rodada {n}</a>' for n in range(1, insights['current_round']+1))}</div></div></section>
<section class="br-cta"><div class="br-shell"><p class="br-kicker">Feito para compartilhar</p><h2>Transforme a evolução do seu time em um Story.</h2><p>Cada página de time gera um card vertical pronto para baixar.</p><a class="br-button br-button-hot" href="#times">Escolher time</a></div></section>'''


def hub_content(insights: dict[str, Any]) -> str:
    return f'''<section class="br-page-hero"><div class="br-shell"><p class="br-kicker">Brasileirão {SEASON}</p><h1>Todos os caminhos do campeonato.</h1><p>Classificação, artilharia, times e o que mudou em cada rodada.</p></div></section><section class="br-section"><div class="br-shell br-feature-links"><a href="classificacao-rodada-a-rodada.html"><span>01</span><h2>Classificação rodada a rodada</h2><p>Veja a posição de cada time em qualquer ponto da competição.</p></a><a href="artilharia-rodada-a-rodada.html"><span>02</span><h2>Artilharia rodada a rodada</h2><p>Acompanhe ultrapassagens e a evolução cumulativa dos gols.</p></a><a href="comparador-times.html"><span>03</span><h2>Comparador de times</h2><p>Coloque duas campanhas frente a frente e compartilhe o duelo.</p></a><a href="rankings-recordes.html"><span>04</span><h2>Rankings e recordes</h2><p>Descubra os melhores ataques, defesas e sequências do campeonato.</p></a></div><div class="br-section-head" id="times"><div><p class="br-kicker">Times</p><h2>20 páginas, 20 histórias</h2></div></div><div class="br-team-cloud">{''.join(f'<a class="br-team-chip" href="times/{slugify(t)}.html">{esc(t)}</a>' for t in insights['teams'])}</div><div class="br-section-head br-top-gap" id="rodadas"><div><p class="br-kicker">Rodadas</p><h2>O que mudou em cada capítulo</h2></div></div><div class="br-round-links">{''.join(f'<a href="rodadas/rodada-{n}.html"><span>{n:02d}</span>Rodada {n}</a>' for n in range(1, insights['current_round']+1))}</div></div></section>'''


def classification_content(insights: dict[str, Any]) -> str:
    current = insights["snapshots"][-1]
    options = "".join(f'<option value="{n}"{(" selected" if n == insights["current_round"] else "")}>Rodada {n}</option>' for n in range(1, insights["current_round"] + 1))
    return f'''<section class="br-page-hero"><div class="br-shell"><p class="br-kicker">Classificação histórica</p><h1>Onde cada time estava depois de cada rodada?</h1><p>Selecione uma rodada para reconstruir a tabela e compare as trajetórias.</p></div></section><section class="br-section"><div class="br-shell"><div class="br-control"><label for="round-select">Ver classificação após</label><select id="round-select" data-round-select>{options}</select></div><div class="br-analysis-grid"><div>{table_html(current['table'])}</div><div class="br-chart-panel"><p class="br-kicker">Evolução visual</p><h2>Corrida por posição</h2><div data-multi-chart aria-live="polite"></div><p class="br-note">Quanto mais alto, melhor. Critérios disponíveis: pontos, vitórias, saldo e gols marcados.</p></div></div></div></section>'''


def scorers_content(insights: dict[str, Any]) -> str:
    current = insights["scorers"][-1]["ranking"] if insights["scorers"] else []
    options = "".join(f'<option value="{n}"{(" selected" if n == insights["current_round"] else "")}>Rodada {n}</option>' for n in range(1, insights["current_round"] + 1))
    rows = "".join(f'<tr><td>{i}</td><th scope="row">{esc(row["name"])}</th><td>{esc(row["team"])}</td><td><strong>{row["goals"]}</strong></td></tr>' for i, row in enumerate(current, 1))
    coverage = insights["scorer_coverage"]
    return f'''<section class="br-page-hero br-page-hero-hot"><div class="br-shell"><p class="br-kicker">Corrida pela artilharia</p><h1>Gol a gol. Rodada a rodada.</h1><p>Quem liderava, quando houve ultrapassagem e como a disputa evoluiu.</p></div></section><section class="br-section"><div class="br-shell"><div class="br-control"><label for="scorer-round-select">Ver artilharia após</label><select id="scorer-round-select" data-scorer-round-select>{options}</select></div><div class="br-analysis-grid"><div class="br-table-wrap"><table class="br-table br-scorer-table" data-scorer-table><thead><tr><th>#</th><th>Jogador</th><th>Time</th><th>Gols</th></tr></thead><tbody>{rows}</tbody></table></div><div class="br-chart-panel"><p class="br-kicker">Disputa acumulada</p><h2>Os líderes da corrida</h2><div data-scorer-chart></div><p class="br-note">Cobertura: {coverage['matches_with_scorers']} de {coverage['completed_matches']} partidas concluídas.</p></div></div></div></section>'''



def comparison_content(insights: dict[str, Any]) -> str:
    current = insights["snapshots"][-1]["table"]
    default_a = current[0]["team"]
    default_b = current[1]["team"]
    options_a = "".join(
        f'<option value="{slugify(team)}"{(" selected" if team == default_a else "")}>{esc(team)}</option>'
        for team in insights["teams"]
    )
    options_b = "".join(
        f'<option value="{slugify(team)}"{(" selected" if team == default_b else "")}>{esc(team)}</option>'
        for team in insights["teams"]
    )
    return f'''<section class="br-page-hero br-compare-hero"><div class="br-shell"><p class="br-kicker">Comparador de campanhas</p><h1>Dois times. A mesma linha do tempo.</h1><p>Compare posição, pontos, vitórias, saldo e aproveitamento rodada a rodada no Brasileirão {SEASON}.</p></div></section><section class="br-section"><div class="br-shell" data-comparison><div class="br-compare-controls"><label>Primeiro time<select data-team-a>{options_a}</select></label><span>×</span><label>Segundo time<select data-team-b>{options_b}</select></label></div><p class="br-compare-error" data-compare-error aria-live="polite"></p><div class="br-compare-summary" data-compare-summary aria-live="polite"></div><div class="br-compare-layout"><div class="br-chart-panel"><p class="br-kicker">Evolução por posição</p><h2>Rodada a rodada</h2><div data-compare-chart></div></div><div class="br-compare-stats" data-compare-stats></div></div><div class="br-compare-share"><div><h2>Compartilhe o duelo</h2><p>O link preserva os dois times escolhidos.</p></div><div class="br-actions"><button class="br-button br-button-hot" type="button" data-share-comparison>Compartilhar</button><button class="br-button" type="button" data-copy-comparison>Copiar link</button></div><p data-compare-status aria-live="polite"></p></div></div></section>'''


def team_content(profile: dict[str, Any], current_round: int) -> str:
    team, row = profile["team"], profile["current"]
    last = "".join(f'<li><span class="br-result br-result-{m["result"].lower()}">{m["result"]}</span><div><strong>{esc(m["opponent"])}</strong><small>{m["venue"]} · rodada {m["round"]}</small></div><b>{esc(m["score"])}</b></li>' for m in profile["last_five"])
    history_json = esc(json.dumps(profile["history"], ensure_ascii=False), True)
    return f'''<section class="br-team-hero"><div class="br-shell"><p class="br-kicker">Trajetória no Brasileirão {SEASON}</p><h1>{esc(team)}</h1><div class="br-team-score"><strong>{row['position']}º</strong><span>{row['points']} pontos<br>{row['wins']} vitórias · saldo {row['gd']:+d}</span></div></div></section><section class="br-section"><div class="br-shell"><div class="br-team-grid"><div class="br-chart-panel"><p class="br-kicker">Posição após cada rodada</p><h2>Uma temporada em movimento</h2>{line_chart(profile['history'], f'Evolução do {team} até a rodada {current_round}')}</div><div><h2>Últimos cinco jogos</h2><ul class="br-form-list">{last}</ul></div></div><div class="br-split-stats"><article><span>Como mandante</span><strong>{profile['home']['points']} pts</strong><p>{profile['home']['wins']}V · {profile['home']['draws']}E · {profile['home']['losses']}D<br>{profile['home']['gf']} gols feitos · {profile['home']['ga']} sofridos</p></article><article><span>Como visitante</span><strong>{profile['away']['points']} pts</strong><p>{profile['away']['wins']}V · {profile['away']['draws']}E · {profile['away']['losses']}D<br>{profile['away']['gf']} gols feitos · {profile['away']['ga']} sofridos</p></article></div></div></section><section class="br-share-section"><div class="br-shell br-share-grid"><div><p class="br-kicker">Card compartilhável</p><h2>Leve a trajetória do {esc(team)} para os Stories.</h2><p>O card é criado no seu navegador e não envia dados.</p><div class="br-actions"><button class="br-button br-button-hot" type="button" data-download-card>Baixar card</button><button class="br-button" type="button" data-share-card>Compartilhar</button></div><p class="br-card-status" data-card-status aria-live="polite"></p></div><div class="br-story-frame"><canvas width="1080" height="1920" data-evolution-card data-team="{esc(team, True)}" data-position="{row['position']}" data-points="{row['points']}" data-round="{current_round}" data-history="{history_json}" aria-label="Prévia do card de evolução do {esc(team, True)}"></canvas></div></div></section>'''


def round_content(number: int, summary: dict[str, Any], matches: list[dict[str, Any]], table: list[dict[str, Any]]) -> str:
    results = "".join(f'<li><span>{esc(m["home"])}</span><strong>{esc(m["score"])}</strong><span>{esc(m["away"])}</span></li>' for m in matches)
    rise = ", ".join(summary["biggest_rise"]["teams"]) or "Sem mudança"
    fall = ", ".join(summary["biggest_fall"]["teams"]) or "Sem mudança"
    lead_text = f'{summary["leader"]} assumiu a liderança, antes ocupada por {summary["previous_leader"]}.' if summary["leader_changed"] else f'{summary["leader"]} terminou a rodada na liderança.'
    return f'''<section class="br-round-hero"><div class="br-shell"><p class="br-kicker">Arquivo do Brasileirão {SEASON}</p><span class="br-round-number">{number:02d}</span><h1>O que mudou na rodada {number}</h1><p>{lead_text}</p></div></section><section class="br-ticker"><div class="br-shell"><span>Rodada {number}</span><strong>{summary['goals']} gols</strong><strong>{summary['matches']} jogos</strong><strong>{summary['leader']} líder</strong></div></section><section class="br-section"><div class="br-shell br-round-grid"><div><h2>Resultados</h2><ul class="br-results">{results}</ul></div><div><h2>Movimentos da rodada</h2><div class="br-change-stack"><article><span>Maior subida</span><strong>{esc(rise)}</strong><p>{summary['biggest_rise']['places']} posições</p></article><article><span>Maior queda</span><strong>{esc(fall)}</strong><p>{summary['biggest_fall']['places']} posições</p></article><article><span>Zona de rebaixamento</span><strong>Entraram: {esc(', '.join(summary['z4_in']) or 'ninguém')}</strong><p>Saíram: {esc(', '.join(summary['z4_out']) or 'ninguém' )}</p></article></div></div></div></section><section class="br-section br-section-soft"><div class="br-shell"><div class="br-section-head"><div><p class="br-kicker">Depois da rodada {number}</p><h2>Classificação</h2></div><a href="../classificacao-rodada-a-rodada.html">Comparar rodadas →</a></div>{table_html(table, team_prefix='../times/')}</div></section>'''


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def build_sitemap(insights: dict[str, Any]) -> None:
    static = [
        ("/", "1.0"), ("/brasileirao/", "1.0"),
        ("/brasileirao/classificacao-rodada-a-rodada.html", "0.9"),
        ("/brasileirao/artilharia-rodada-a-rodada.html", "0.9"),
        ("/brasileirao/comparador-times.html", "0.9"),
        ("/brasileirao/rankings-recordes.html", "0.9"),
        ("/gerador-card-futebol.html", "0.8"), ("/projetos.html", "0.6"),
        ("/dados-futebol.html", "0.6"), ("/artigos.html", "0.5"), ("/about.html", "0.5"),
    ]
    urls = [f'  <url><loc>{SITE_URL}{path}</loc><changefreq>daily</changefreq><priority>{priority}</priority></url>' for path, priority in static]
    urls += [f'  <url><loc>{SITE_URL}/brasileirao/times/{slug}.html</loc><changefreq>daily</changefreq><priority>0.8</priority></url>' for slug in insights["team_profiles"]]
    urls += [f'  <url><loc>{SITE_URL}/brasileirao/rodadas/rodada-{number}.html</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>' for number in range(1, insights["current_round"] + 1)]
    write(ROOT / "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")


def main() -> None:
    matches, scorer_data = load_data()
    insights = build_insights(matches, scorer_data)
    write(INSIGHTS_FILE, json.dumps(insights, ensure_ascii=False, separators=(",", ":")) + "\n")
    build_og_cards(ROOT, insights)
    home = page("Rodada a Rodada | Brasileirão 2026 em números", "Veja a evolução da classificação, artilharia, times e rodadas do Brasileirão 2026.", f"{SITE_URL}/", home_content(insights), depth="", body_class="br-page br-home", script=True)
    write(ROOT / "index.html", home)
    write(OUTPUT / "index.html", page("Brasileirão 2026 rodada a rodada", "Explore classificação, artilharia, times e todas as rodadas do Brasileirão 2026.", f"{SITE_URL}/brasileirao/", hub_content(insights)))
    write(OUTPUT / "classificacao-rodada-a-rodada.html", page("Classificação do Brasileirão 2026 rodada a rodada", "Reconstrua a classificação do Brasileirão 2026 após qualquer rodada e compare a evolução dos times.", f"{SITE_URL}/brasileirao/classificacao-rodada-a-rodada.html", classification_content(insights), current="classificacao", script=True, social_image=f"{SITE_URL}/assets/og/classificacao.png", social_image_alt="Classificação histórica do Brasileirão 2026 rodada a rodada"))
    write(OUTPUT / "artilharia-rodada-a-rodada.html", page("Artilharia do Brasileirão 2026 rodada a rodada", "Veja quem liderava a artilharia do Brasileirão 2026 após cada rodada e acompanhe a corrida gol a gol.", f"{SITE_URL}/brasileirao/artilharia-rodada-a-rodada.html", scorers_content(insights), current="artilharia", script=True, social_image=f"{SITE_URL}/assets/og/artilharia.png", social_image_alt="Artilharia do Brasileirão 2026 rodada a rodada"))
    write(OUTPUT / "comparador-times.html", page("Comparador de times do Brasileirão 2026 | Rodada a Rodada", "Compare dois times do Brasileirão 2026 por posição, pontos, vitórias, saldo e aproveitamento em cada rodada.", f"{SITE_URL}/brasileirao/comparador-times.html", comparison_content(insights), current="comparador", script=True, social_image=f"{SITE_URL}/assets/og/comparador.png", social_image_alt="Comparador de campanhas dos times do Brasileirão 2026"))
    write(OUTPUT / "rankings-recordes.html", page("Rankings e recordes do Brasileirão 2026 | Rodada a Rodada", "Veja os melhores ataques, defesas, mandantes, visitantes e as maiores sequências do Brasileirão 2026.", f"{SITE_URL}/brasileirao/rankings-recordes.html", rankings_content(insights), current="rankings", social_image=f"{SITE_URL}/assets/og/rankings-recordes.png", social_image_alt="Rankings e recordes do Brasileirão 2026"))

    for slug, profile in insights["team_profiles"].items():
        title = f'Evolução do {profile["team"]} no Brasileirão 2026'
        description = f'Posição, pontos, aproveitamento, últimos jogos e evolução rodada a rodada do {profile["team"]} no Brasileirão 2026.'
        write(OUTPUT / "times" / f"{slug}.html", page(title, description, f"{SITE_URL}/brasileirao/times/{slug}.html", team_content(profile, insights["current_round"]), depth="../../", current="times", script=True, social_image=f"{SITE_URL}/assets/og/times/{slug}.png", social_image_alt=f'Evolução do {profile["team"]} no Brasileirão 2026'))

    completed = [match for match in matches if parse_score(match.get("score", ""))]
    for summary, snapshot in zip(insights["rounds"], insights["snapshots"]):
        number = summary["round"]
        round_matches = [m for m in completed if int(m["round"]) == number]
        write(OUTPUT / "rodadas" / f"rodada-{number}.html", page(f'O que mudou na rodada {number} do Brasileirão 2026', f'Resultados, líder, maiores subidas, quedas e mudanças no Z4 após a rodada {number} do Brasileirão 2026.', f"{SITE_URL}/brasileirao/rodadas/rodada-{number}.html", round_content(number, summary, round_matches, snapshot["table"]), depth="../../", current="rodadas", social_image=f"{SITE_URL}/assets/og/rodadas/rodada-{number}.png", social_image_alt=f'Resumo da rodada {number} do Brasileirão 2026'))

    build_sitemap(insights)
    print(f"Produto gerado: {len(insights['team_profiles'])} times, {insights['current_round']} rodadas e {insights['scorer_coverage']['matches_with_scorers']} jogos com artilheiros.")


if __name__ == "__main__":
    main()
