#!/usr/bin/env python3
"""Camada editorial para priorizar insights mais fortes no post diário."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from PIL import Image

import instagram_daily
import instagram_matchday


HIGH_PRIORITY_KINDS = {"leader", "g4", "z4", "upset", "g4_cluster", "z4_cluster"}


def high_scoring_match_spotlight(matches: list[dict], minimum_goals: int = 5) -> dict | None:
    candidates = []
    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if not score:
            continue
        total_goals = score[0] + score[1]
        if total_goals >= minimum_goals:
            candidates.append((total_goals, abs(score[0] - score[1]), match))
    if not candidates:
        return None
    total_goals, _, match = max(candidates, key=lambda item: (item[0], -item[1], item[2].get("home", "")))
    return {"kind":"goal_fest","label":"CHUVA DE GOLS","text":f"{match['home']} {match['score']} {match['away']} • {total_goals} gols","caption":f"Chuva de gols: {match['home']} {match['score']} {match['away']} teve {total_goals} gols no placar.","home":match.get("home", ""),"away":match.get("away", ""),"score":match.get("score", ""),"goals":total_goals}


def scoring_surge_spotlight(insights: dict, minimum_matches: int = 5, history_rounds: int = 5, minimum_lift: float = 0.35, minimum_rate: float = 3.0) -> dict | None:
    rounds = insights.get("rounds", [])
    if len(rounds) < history_rounds + 1:
        return None
    current = rounds[-1]
    current_matches, current_goals = int(current.get("matches") or 0), int(current.get("goals") or 0)
    if current_matches < minimum_matches:
        return None
    history = [row for row in rounds[:-1] if int(row.get("matches") or 0) >= 8 and row.get("goals") is not None][-history_rounds:]
    if len(history) < history_rounds:
        return None
    history_matches = sum(int(row["matches"]) for row in history)
    history_goals = sum(int(row["goals"]) for row in history)
    if history_matches <= 0 or history_goals <= 0:
        return None
    current_rate, history_rate = current_goals / current_matches, history_goals / history_matches
    lift = current_rate / history_rate - 1
    if current_rate < minimum_rate or lift < minimum_lift:
        return None
    percentage = round(lift * 100)
    return {"kind":"scoring_surge","label":"RODADA OFENSIVA","text":f"{current_rate:.1f} gols/jogo • {percentage}% acima das últimas {history_rounds}","caption":f"Rodada ofensiva: são {current_rate:.1f} gols por jogo até aqui, {percentage}% acima da média das últimas {history_rounds} rodadas ({history_rate:.1f}).","rate":current_rate,"history_rate":history_rate,"lift":lift,"history_rounds":history_rounds}


def scoring_drought_spotlight(insights: dict, minimum_matches: int = 5, history_rounds: int = 5, minimum_drop: float = 0.25, maximum_rate: float = 1.8) -> dict | None:
    """Destaca uma rodada realmente travada comparando-a ao ritmo recente do campeonato."""
    rounds = insights.get("rounds", [])
    if len(rounds) < history_rounds + 1:
        return None
    current = rounds[-1]
    current_matches, current_goals = int(current.get("matches") or 0), int(current.get("goals") or 0)
    if current_matches < minimum_matches:
        return None
    history = [row for row in rounds[:-1] if int(row.get("matches") or 0) >= 8 and row.get("goals") is not None][-history_rounds:]
    if len(history) < history_rounds:
        return None
    history_matches = sum(int(row["matches"]) for row in history)
    history_goals = sum(int(row["goals"]) for row in history)
    if history_matches <= 0 or history_goals <= 0:
        return None
    current_rate, history_rate = current_goals / current_matches, history_goals / history_matches
    drop = 1 - current_rate / history_rate
    if current_rate > maximum_rate or drop < minimum_drop:
        return None
    percentage = round(drop * 100)
    return {"kind":"scoring_drought","label":"RODADA TRAVADA","text":f"{current_rate:.1f} gols/jogo • {percentage}% abaixo das últimas {history_rounds}","caption":f"Rodada travada: são só {current_rate:.1f} gols por jogo até aqui, {percentage}% abaixo da média das últimas {history_rounds} rodadas ({history_rate:.1f}).","rate":current_rate,"history_rate":history_rate,"drop":drop,"history_rounds":history_rounds}


def away_dominance_spotlight(matches: list[dict], minimum_matches: int = 4, minimum_share: float = 0.75) -> dict | None:
    scored = [score for match in matches if (score := instagram_daily._score(match.get("score", "")))]
    if len(scored) < minimum_matches:
        return None
    away_wins = sum(away > home for home, away in scored)
    share = away_wins / len(scored)
    if share < minimum_share:
        return None
    percentage = round(share * 100)
    return {"kind":"away_dominance","label":"VISITANTES MANDARAM","text":f"{away_wins} vitórias fora em {len(scored)} jogos • {percentage}% do dia","caption":f"Visitantes mandaram: quem jogou fora venceu {away_wins} das {len(scored)} partidas do dia ({percentage}%).","away_wins":away_wins,"matches":len(scored),"share":share}


def home_dominance_spotlight(matches: list[dict], minimum_matches: int = 4, minimum_share: float = 0.75) -> dict | None:
    """Destaca dias em que o mando de campo realmente dominou os resultados."""
    scored = [score for match in matches if (score := instagram_daily._score(match.get("score", "")))]
    if len(scored) < minimum_matches:
        return None
    home_wins = sum(home > away for home, away in scored)
    share = home_wins / len(scored)
    if share < minimum_share:
        return None
    percentage = round(share * 100)
    return {"kind":"home_dominance","label":"MANDO PESOU","text":f"{home_wins} vitórias em casa em {len(scored)} jogos • {percentage}% do dia","caption":f"Mando pesou: os mandantes venceram {home_wins} das {len(scored)} partidas do dia ({percentage}%).","home_wins":home_wins,"matches":len(scored),"share":share}


def drawless_day_spotlight(matches: list[dict], minimum_matches: int = 4) -> dict | None:
    scored = [score for match in matches if (score := instagram_daily._score(match.get("score", "")))]
    if len(scored) < minimum_matches or any(home == away for home, away in scored):
        return None
    return {"kind":"drawless_day","label":"DIA SEM EMPATES","text":f"{len(scored)} jogos, {len(scored)} vencedores • nenhum empate","caption":f"Dia sem empates: as {len(scored)} partidas disputadas terminaram com vencedor.","matches":len(scored)}


def defensive_streak_spotlight(insights: dict, rounds: int = 3, minimum_points: int = 7) -> dict | None:
    snapshots = insights.get("snapshots", [])
    if len(snapshots) < rounds + 1:
        return None
    start, latest = snapshots[-(rounds + 1)], snapshots[-1]
    start_by_team = {row["team"]: row for row in start.get("table", [])}
    candidates = []
    for row in latest.get("table", []):
        previous = start_by_team.get(row["team"])
        if previous is None or "ga" not in row or "ga" not in previous:
            continue
        goals_against, points = int(row["ga"]) - int(previous["ga"]), int(row["points"]) - int(previous["points"])
        if goals_against == 0 and points >= minimum_points:
            candidates.append({"team":row["team"],"points":points,"position":int(row.get("position",99))})
    if not candidates:
        return None
    best = max(candidates, key=lambda item:(item["points"],-item["position"],item["team"]))
    return {"kind":"defensive_streak","label":"MURALHA","text":f"{best['team']} • {rounds} rodadas sem sofrer gol • {best['points']} pts","caption":f"Muralha: {best['team']} não sofreu gols nas últimas {rounds} rodadas e somou {best['points']} pontos no período.","team":best["team"],"rounds":rounds,"points":best["points"]}


def title_race_spotlight(insights: dict, maximum_gap: int = 3, minimum_teams: int = 3, minimum_round: int = 5) -> dict | None:
    snapshot, latest = instagram_daily.current_snapshot(insights)
    round_number, table = int(latest.get("round") or snapshot.get("round") or 0), snapshot.get("table", [])
    if round_number < minimum_round or len(table) < minimum_teams:
        return None
    leader_points = table[0]["points"]
    contenders = [row for row in table if 0 <= leader_points - row["points"] <= maximum_gap]
    if len(contenders) < minimum_teams:
        return None
    spread, teams = leader_points - contenders[-1]["points"], [row["team"] for row in contenders]
    gap_text = f"{spread} {'ponto' if spread == 1 else 'pontos'}"
    return {"kind":"title_cluster","label":"TÍTULO EMBOLADO","text":f"{len(contenders)} times separados por só {gap_text} no topo","caption":f"Briga pelo título: {len(contenders)} times estão separados por apenas {gap_text}; {', '.join(teams)} formam o pelotão da frente.","count":len(contenders),"spread":spread,"teams":teams}


def editorial_spotlight(insights: dict, matches: list[dict]) -> dict:
    base = instagram_matchday.matchday_spotlight(insights, matches)
    if base.get("kind") in HIGH_PRIORITY_KINDS or base.get("kind") == "delayed_match":
        return base
    return high_scoring_match_spotlight(matches) or scoring_surge_spotlight(insights) or scoring_drought_spotlight(insights) or away_dominance_spotlight(matches) or home_dominance_spotlight(matches) or drawless_day_spotlight(matches) or defensive_streak_spotlight(insights) or title_race_spotlight(insights) or base


def _spotlight_sentence(spotlight: dict) -> str:
    caption = (spotlight.get("caption") or "").strip()
    if caption:
        return caption
    text = (spotlight.get("text") or "").strip().rstrip(".")
    if not text:
        return ""
    label = (spotlight.get("label") or "Destaque").strip().capitalize()
    return f"{label}: {text}."


def _standings_context(table: list[dict]) -> list[str]:
    """Acrescenta contexto de distância nos cortes mais disputados da tabela."""
    if len(table) < 17:
        return []
    title_gap = int(table[0]["points"]) - int(table[1]["points"])
    z4_gap = int(table[15]["points"]) - int(table[16]["points"])
    return [
        f"Topo: {table[0]['team']} {table[0]['points']} x {table[1]['points']} {table[1]['team']} • {title_gap} {'pt' if title_gap == 1 else 'pts'} de diferença.",
        f"Corte do Z4: {table[15]['team']} {table[15]['points']} x {table[16]['points']} {table[16]['team']} • {z4_gap} {'pt' if z4_gap == 1 else 'pts'}.",
    ]


def build_caption(insights: dict, matches: list[dict]) -> str:
    snapshot, latest = instagram_daily.current_snapshot(insights)
    table = snapshot["table"]
    spotlight = editorial_spotlight(insights, matches)
    story = _spotlight_sentence(spotlight)
    partial = " (parcial)" if latest.get("matches", 10) < 10 else ""
    lines = [story, f"Brasileirão {insights['season']} — rodada {latest['round']}{partial}.", "", f"Líder: {table[0]['team']} — {table[0]['points']} pts.", f"G4: {', '.join(row['team'] for row in table[:4])}.", f"Z4: {', '.join(row['team'] for row in table[-4:])}.", *_standings_context(table), "", f"Mais números e evolução rodada a rodada: {instagram_daily.SITE_URL}", "", "#Brasileirao #Brasileirao2026 #FutebolBrasileiro #SerieA"]
    return "\n".join(line for line in lines if line is not None)[:2200]


def render_card(insights: dict, matches: list[dict], output: Path = instagram_daily.DEFAULT_OUTPUT, now: datetime | None = None) -> Path:
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
    matches = instagram_matchday.completed_matches_for_date(all_matches, instagram_matchday.publication_date())
    if args.command == "render": print(render_card(insights, matches, args.output))
    else: print(build_caption(insights, matches))


if __name__ == "__main__":
    main()
