#!/usr/bin/env python3
"""Camada editorial para priorizar insights mais fortes no post diário."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from PIL import Image

import instagram_daily
import instagram_matchday


HIGH_PRIORITY_KINDS = {"leader", "g4", "z4", "upset"}

DERBY_NAMES = {
    frozenset(("Athletico-PR", "Coritiba")): "Atletiba",
    frozenset(("Atlético-MG", "Cruzeiro")): "Clássico Mineiro",
    frozenset(("Bahia", "Vitória")): "Ba-Vi",
    frozenset(("Botafogo", "Flamengo")): "Clássico da Rivalidade",
    frozenset(("Botafogo", "Fluminense")): "Clássico Vovô",
    frozenset(("Botafogo", "Vasco")): "Clássico da Amizade",
    frozenset(("Corinthians", "Palmeiras")): "Dérbi Paulista",
    frozenset(("Corinthians", "Santos")): "Clássico Alvinegro",
    frozenset(("Corinthians", "São Paulo")): "Majestoso",
    frozenset(("Flamengo", "Fluminense")): "Fla-Flu",
    frozenset(("Flamengo", "Vasco")): "Clássico dos Milhões",
    frozenset(("Fluminense", "Vasco")): "Clássico dos Gigantes",
    frozenset(("Grêmio", "Internacional")): "Gre-Nal",
    frozenset(("Palmeiras", "Santos")): "Clássico da Saudade",
    frozenset(("Palmeiras", "São Paulo")): "Choque-Rei",
    frozenset(("Santos", "São Paulo")): "San-São",
}


def _join_pt(items: list[str]) -> str:
    if len(items) < 2:
        return "".join(items)
    return f"{', '.join(items[:-1])} e {items[-1]}"


def _period_noun(matches: list[dict]) -> str:
    """Usa 'bloco' quando o recorte reúne jogos de mais de uma data."""
    dates = {str(match.get("date", "")).strip() for match in matches if str(match.get("date", "")).strip()}
    return "bloco" if len(dates) > 1 else "dia"


def derby_day_spotlight(matches: list[dict], minimum_derbies: int = 2) -> dict | None:
    """Destaca datas com vários clássicos concluídos, sem depender de imagens dos jogos."""
    derbies = []
    for match in matches:
        if not instagram_daily._score(match.get("score", "")):
            continue
        name = DERBY_NAMES.get(frozenset((match.get("home", ""), match.get("away", ""))))
        if name:
            derbies.append({"name": name, "home": match["home"], "away": match["away"], "score": match["score"]})
    if len(derbies) < minimum_derbies:
        return None
    names = [item["name"] for item in derbies]
    results = [f"{item['home']} {item['score']} {item['away']}" for item in derbies]
    period = _period_noun(matches)
    label = "BLOCO DE CLÁSSICOS" if period == "bloco" else "DIA DE CLÁSSICOS"
    caption_lead = "Bloco de clássicos" if period == "bloco" else "Dia de clássicos"
    return {
        "kind":"derby_day",
        "label":label,
        "text":f"{len(derbies)} clássicos no mesmo {period} • {_join_pt(names)}",
        "caption":f"{caption_lead}: {'; '.join(results)}.",
        "derbies":names,
        "results":results,
        "count":len(derbies),
    }


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


def multi_goal_scorer_spotlight(
    matches: list[dict],
    scorer_data: dict | None,
    minimum_goals: int = 2,
) -> dict | None:
    """Destaca um jogador que marcou duas ou mais vezes no mesmo jogo do bloco."""
    scorer_matches = (scorer_data or {}).get("matches", {})
    candidates = []
    for match in matches:
        match_scorers = scorer_matches.get(match.get("url", ""), {})
        score = instagram_daily._score(match.get("score", ""))
        if not score:
            continue
        for side_index, side in enumerate(("home", "away")):
            team = match.get(side, "")
            team_goals = score[side_index]
            for scorer in match_scorers.get(side, []):
                goals = int(scorer.get("goals") or 1)
                if scorer.get("own_goal") or goals < minimum_goals:
                    continue
                candidates.append({
                    "player": scorer.get("name", ""),
                    "team": team,
                    "goals": goals,
                    "team_goals": team_goals,
                    "home": match.get("home", ""),
                    "away": match.get("away", ""),
                    "score": match.get("score", ""),
                })
    if not candidates:
        return None

    best = min(
        candidates,
        key=lambda item: (
            -item["goals"],
            -(item["goals"] / max(item["team_goals"], 1)),
            item["player"],
        ),
    )
    hat_trick = best["goals"] >= 3
    lead = "Hat-trick" if hat_trick else "Dois dele"
    return {
        "kind": "multi_goal_scorer",
        "label": "HAT-TRICK" if hat_trick else "DOIS DELE",
        "text": f"{best['player']} • {best['goals']} gols pelo {best['team']}",
        "caption": (
            f"{lead}: {best['player']} marcou {best['goals']} vezes em "
            f"{best['home']} {best['score']} {best['away']}."
        ),
        **best,
    }


def collective_attack_spotlight(
    matches: list[dict],
    scorer_data: dict | None,
    minimum_scorers: int = 3,
) -> dict | None:
    """Destaca uma equipe que distribuiu seus gols entre vários jogadores no mesmo jogo."""
    scorer_matches = (scorer_data or {}).get("matches", {})
    candidates = []
    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if not score:
            continue
        match_scorers = scorer_matches.get(match.get("url", ""), {})
        for side_index, side in enumerate(("home", "away")):
            team_goals = score[side_index]
            scorers = []
            for scorer in match_scorers.get(side, []):
                name = str(scorer.get("name") or "").strip()
                if scorer.get("own_goal") or not name or name in scorers:
                    continue
                scorers.append(name)
            if len(scorers) < minimum_scorers:
                continue
            candidates.append({
                "team": match.get(side, ""),
                "team_goals": team_goals,
                "scorers": scorers,
                "scorer_count": len(scorers),
                "home": match.get("home", ""),
                "away": match.get("away", ""),
                "score": match.get("score", ""),
            })
    if not candidates:
        return None

    best = min(
        candidates,
        key=lambda item: (-item["scorer_count"], -item["team_goals"], item["team"]),
    )
    scorer_word = "autores" if best["scorer_count"] != 1 else "autor"
    return {
        "kind": "collective_attack",
        "label": "ATAQUE COLETIVO",
        "text": f"{best['team']} • {best['team_goals']} gols, {best['scorer_count']} {scorer_word}",
        "caption": (
            f"Ataque coletivo: {_join_pt(best['scorers'])} marcaram pelo {best['team']} em "
            f"{best['home']} {best['score']} {best['away']}."
        ),
        **best,
    }


def rout_wave_spotlight(
    matches: list[dict],
    minimum_matches: int = 4,
    minimum_routs: int = 2,
    minimum_margin: int = 3,
    minimum_share: float = 0.40,
) -> dict | None:
    """Destaca blocos com várias goleadas, não apenas o maior placar isolado."""
    completed = []
    routs = []
    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if not score:
            continue
        completed.append(match)
        home_goals, away_goals = score
        margin = abs(home_goals - away_goals)
        if margin < minimum_margin:
            continue
        winner = match.get("home", "") if home_goals > away_goals else match.get("away", "")
        routs.append({
            "winner": winner,
            "home": match.get("home", ""),
            "away": match.get("away", ""),
            "score": match.get("score", ""),
            "margin": margin,
        })

    if len(completed) < minimum_matches or len(routs) < minimum_routs:
        return None
    share = len(routs) / len(completed)
    if share < minimum_share:
        return None

    percentage = round(share * 100)
    period = _period_noun(completed)
    results = [f"{item['home']} {item['score']} {item['away']}" for item in routs]
    return {
        "kind": "rout_wave",
        "label": "GOLEADAS EM SÉRIE",
        "text": f"{len(routs)} de {len(completed)} jogos decididos por {minimum_margin}+ gols • {percentage}% do {period}",
        "caption": (
            f"Goleadas em série: {'; '.join(results)}. Foram {len(routs)} das {len(completed)} partidas "
            f"do {period} decididas por {minimum_margin} ou mais gols de diferença ({percentage}%)."
        ),
        "routs": routs,
        "matches": len(completed),
        "share": share,
        "minimum_margin": minimum_margin,
    }


def bounce_back_spotlight(
    insights: dict,
    matches: list[dict],
    minimum_previous_margin: int = 2,
    minimum_current_margin: int = 2,
) -> dict | None:
    """Destaca uma resposta forte após derrota clara no jogo anterior."""
    profiles = {
        profile.get("team"): profile
        for profile in insights.get("team_profiles", {}).values()
        if profile.get("team")
    }
    candidates = []

    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if not score or score[0] == score[1]:
            continue
        current_margin = abs(score[0] - score[1])
        if current_margin < minimum_current_margin:
            continue

        home_win = score[0] > score[1]
        winner_side = "home" if home_win else "away"
        winner = match.get(winner_side, "")
        opponent = match.get("away" if home_win else "home", "")
        current_round = int(match.get("round") or 0)
        profile = profiles.get(winner, {})
        previous_games = [
            game for game in profile.get("last_five", [])
            if int(game.get("round") or 0) < current_round
        ]
        if not previous_games:
            continue
        previous = max(previous_games, key=lambda game: int(game.get("round") or 0))
        previous_score = instagram_daily._score(previous.get("score", ""))
        if previous.get("result") != "D" or not previous_score:
            continue

        previous_margin = abs(previous_score[0] - previous_score[1])
        if previous_margin < minimum_previous_margin:
            continue

        if previous.get("venue") == "Casa":
            previous_team_goals, previous_opponent_goals = previous_score
        else:
            previous_opponent_goals, previous_team_goals = previous_score
        current_team_goals = score[0] if home_win else score[1]
        current_opponent_goals = score[1] if home_win else score[0]
        candidates.append({
            "team": winner,
            "opponent": opponent,
            "previous_opponent": previous.get("opponent", ""),
            "previous_score": f"{previous_team_goals} x {previous_opponent_goals}",
            "current_score": f"{current_team_goals} x {current_opponent_goals}",
            "previous_margin": previous_margin,
            "current_margin": current_margin,
            "position": int(profile.get("current", {}).get("position") or 99),
        })

    if not candidates:
        return None

    best = max(
        candidates,
        key=lambda item: (
            item["previous_margin"] + item["current_margin"],
            item["current_margin"],
            -item["position"],
            item["team"],
        ),
    )
    return {
        "kind": "bounce_back",
        "label": "RESPOSTA IMEDIATA",
        "text": f"{best['team']} • de {best['previous_score']} para {best['current_score']}",
        "caption": (
            f"Resposta imediata — {best['team']}: depois de perder por {best['previous_score']} "
            f"para {best['previous_opponent']}, venceu {best['opponent']} por {best['current_score']}."
        ),
        **best,
    }


def winless_run_ended_spotlight(
    insights: dict,
    matches: list[dict],
    minimum_winless: int = 3,
) -> dict | None:
    """Destaca uma vitória que encerrou uma sequência relevante sem vencer."""
    profiles = {
        profile.get("team"): profile
        for profile in insights.get("team_profiles", {}).values()
        if profile.get("team")
    }
    candidates = []

    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if not score or score[0] == score[1]:
            continue
        home_win = score[0] > score[1]
        team = match.get("home" if home_win else "away", "")
        opponent = match.get("away" if home_win else "home", "")
        match_round = int(match.get("round") or 0)
        profile = profiles.get(team, {})
        recent = profile.get("last_five", [])
        if not any(
            int(game.get("round") or 0) == match_round and game.get("result") == "V"
            for game in recent
        ):
            continue

        previous = sorted(
            (game for game in recent if int(game.get("round") or 0) < match_round),
            key=lambda game: int(game.get("round") or 0),
            reverse=True,
        )
        winless = 0
        earlier_win_found = False
        for game in previous:
            if game.get("result") == "V":
                earlier_win_found = True
                break
            winless += 1
        if winless < minimum_winless:
            continue

        team_goals, opponent_goals = score if home_win else (score[1], score[0])
        candidates.append({
            "team": team,
            "opponent": opponent,
            "score": f"{team_goals} x {opponent_goals}",
            "winless_matches": winless,
            "at_least": not earlier_win_found,
            "position": int(profile.get("current", {}).get("position") or 99),
        })

    if not candidates:
        return None
    best = max(
        candidates,
        key=lambda item: (item["winless_matches"], -item["position"], item["team"]),
    )
    duration = (
        f"pelo menos {best['winless_matches']} jogos"
        if best["at_least"]
        else f"{best['winless_matches']} jogos"
    )
    return {
        "kind": "winless_run_ended",
        "label": "FIM DO JEJUM",
        "text": f"{best['team']} • venceu após {duration} sem vitória",
        "caption": (
            f"Fim do jejum: {best['team']} voltou a vencer após {duration} sem vitória; "
            f"bateu o {best['opponent']} por {best['score']}."
        ),
        **best,
    }


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


def both_teams_scored_spotlight(matches: list[dict], minimum_matches: int = 4, minimum_share: float = 0.75) -> dict | None:
    """Destaca dias abertos em que os dois lados marcaram na maioria dos jogos."""
    scored = [score for match in matches if (score := instagram_daily._score(match.get("score", "")))]
    if len(scored) < minimum_matches:
        return None
    both_scored = sum(home > 0 and away > 0 for home, away in scored)
    share = both_scored / len(scored)
    if share < minimum_share:
        return None
    percentage = round(share * 100)
    period = _period_noun(matches)
    return {
        "kind":"both_teams_scored",
        "label":"LÁ E CÁ",
        "text":f"{both_scored} de {len(scored)} jogos com gols dos dois times • {percentage}% do {period}",
        "caption":f"Lá e cá: {both_scored} das {len(scored)} partidas do {period} tiveram gols dos dois times ({percentage}%).",
        "both_scored":both_scored,
        "matches":len(scored),
        "share":share,
    }


def clean_sheet_wave_spotlight(matches: list[dict], minimum_matches: int = 4, minimum_share: float = 0.75) -> dict | None:
    """Destaca blocos em que ao menos uma defesa saiu zerada na maioria dos jogos."""
    completed = []
    teams = []
    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if not score:
            continue
        completed.append(score)
        home_goals, away_goals = score
        if away_goals == 0 and match.get("home"):
            teams.append(match["home"])
        if home_goals == 0 and match.get("away"):
            teams.append(match["away"])
    if len(completed) < minimum_matches:
        return None
    clean_sheet_matches = sum(home == 0 or away == 0 for home, away in completed)
    share = clean_sheet_matches / len(completed)
    if share < minimum_share:
        return None
    percentage = round(share * 100)
    period = _period_noun(matches)
    teams = list(dict.fromkeys(teams))
    team_context = f" Saíram sem sofrer: {_join_pt(teams)}." if teams else ""
    return {
        "kind":"clean_sheet_wave",
        "label":"REDE ZERADA",
        "text":f"{clean_sheet_matches} de {len(completed)} jogos com ao menos uma defesa zerada • {percentage}% do {period}",
        "caption":f"Rede zerada: {clean_sheet_matches} das {len(completed)} partidas do {period} tiveram ao menos um time sem sofrer gol ({percentage}%).{team_context}",
        "clean_sheet_matches":clean_sheet_matches,
        "matches":len(completed),
        "share":share,
        "teams":teams,
    }


def away_dominance_spotlight(matches: list[dict], minimum_matches: int = 4, minimum_share: float = 0.75) -> dict | None:
    scored = [score for match in matches if (score := instagram_daily._score(match.get("score", "")))]
    if len(scored) < minimum_matches:
        return None
    away_wins = sum(away > home for home, away in scored)
    share = away_wins / len(scored)
    if share < minimum_share:
        return None
    percentage = round(share * 100)
    period = _period_noun(matches)
    return {"kind":"away_dominance","label":"VISITANTES MANDARAM","text":f"{away_wins} vitórias fora em {len(scored)} jogos • {percentage}% do {period}","caption":f"Visitantes mandaram: quem jogou fora venceu {away_wins} das {len(scored)} partidas do {period} ({percentage}%).","away_wins":away_wins,"matches":len(scored),"share":share}


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
    period = _period_noun(matches)
    return {"kind":"home_dominance","label":"MANDO PESOU","text":f"{home_wins} vitórias em casa em {len(scored)} jogos • {percentage}% do {period}","caption":f"Mando pesou: os mandantes venceram {home_wins} das {len(scored)} partidas do {period} ({percentage}%).","home_wins":home_wins,"matches":len(scored),"share":share}


def draw_dominance_spotlight(matches: list[dict], minimum_matches: int = 4, minimum_share: float = 0.75) -> dict | None:
    """Destaca um recorte amplo de jogos em que ninguém conseguiu abrir vantagem."""
    scored = [score for match in matches if (score := instagram_daily._score(match.get("score", "")))]
    if len(scored) < minimum_matches:
        return None
    draws = sum(home == away for home, away in scored)
    share = draws / len(scored)
    if share < minimum_share:
        return None
    percentage = round(share * 100)
    period = _period_noun(matches)
    return {"kind":"draw_dominance","label":"EMPATE EM ALTA","text":f"{draws} empates em {len(scored)} jogos • {percentage}% do {period}","caption":f"Empate em alta: {draws} das {len(scored)} partidas do {period} terminaram iguais ({percentage}%).","draws":draws,"matches":len(scored),"share":share}


def drawless_day_spotlight(matches: list[dict], minimum_matches: int = 4) -> dict | None:
    scored = [score for match in matches if (score := instagram_daily._score(match.get("score", "")))]
    if len(scored) < minimum_matches or any(home == away for home, away in scored):
        return None
    period = _period_noun(matches)
    label = "BLOCO SEM EMPATES" if period == "bloco" else "DIA SEM EMPATES"
    caption_lead = "Bloco sem empates" if period == "bloco" else "Dia sem empates"
    return {"kind":"drawless_day","label":label,"text":f"{len(scored)} jogos, {len(scored)} vencedores • nenhum empate","caption":f"{caption_lead}: as {len(scored)} partidas disputadas terminaram com vencedor.","matches":len(scored)}


def winning_streak_spotlight(insights: dict, matches: list[dict], minimum_wins: int = 3) -> dict | None:
    """Destaca uma sequência de vitórias renovada por um vencedor do bloco publicado."""
    winners = set()
    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if not score or score[0] == score[1]:
            continue
        winners.add(match.get("home") if score[0] > score[1] else match.get("away"))

    candidates = []
    for profile in insights.get("team_profiles", {}).values():
        team = profile.get("team")
        current = profile.get("current", {})
        streak = int(profile.get("streaks", {}).get("current_wins") or 0)
        if team not in winners or streak < minimum_wins:
            continue
        candidates.append({
            "team": team,
            "wins": streak,
            "position": int(current.get("position") or 99),
            "points": int(current.get("points") or 0),
        })

    if not candidates:
        return None
    best = max(candidates, key=lambda item: (item["wins"], -item["position"], item["team"]))
    return {
        "kind": "winning_streak",
        "label": "VITÓRIAS EM SÉRIE",
        "text": f"{best['team']} • {best['wins']} vitórias seguidas • {best['position']}º lugar",
        "caption": (
            f"Vitórias em série: {best['team']} venceu os últimos {best['wins']} jogos e ocupa "
            f"o {best['position']}º lugar, com {best['points']} pontos."
        ),
        **best,
    }


def unbeaten_run_spotlight(insights: dict, matches: list[dict], minimum_matches: int = 5) -> dict | None:
    """Destaca uma série invicta renovada por um time que não perdeu no bloco."""
    unbeaten_teams = set()
    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if not score:
            continue
        if score[0] >= score[1]:
            unbeaten_teams.add(match.get("home"))
        if score[1] >= score[0]:
            unbeaten_teams.add(match.get("away"))

    candidates = []
    for profile in insights.get("team_profiles", {}).values():
        team = profile.get("team")
        current = profile.get("current", {})
        streaks = profile.get("streaks", {})
        unbeaten = int(streaks.get("current_unbeaten") or 0)
        wins = int(streaks.get("current_wins") or 0)
        # Uma série composta só por vitórias já tem um destaque mais específico.
        if team not in unbeaten_teams or unbeaten < minimum_matches or unbeaten == wins:
            continue
        candidates.append({
            "team": team,
            "unbeaten_matches": unbeaten,
            "position": int(current.get("position") or 99),
            "points": int(current.get("points") or 0),
        })

    if not candidates:
        return None
    best = max(
        candidates,
        key=lambda item: (item["unbeaten_matches"], -item["position"], item["team"]),
    )
    return {
        "kind": "unbeaten_run",
        "label": "SÉRIE INVICTA",
        "text": (
            f"{best['team']} • {best['unbeaten_matches']} jogos sem perder • "
            f"{best['position']}º lugar"
        ),
        "caption": (
            f"Série invicta: {best['team']} chegou a {best['unbeaten_matches']} jogos sem perder "
            f"e ocupa o {best['position']}º lugar, com {best['points']} pontos."
        ),
        **best,
    }


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


def editorial_spotlight(insights: dict, matches: list[dict], scorer_data: dict | None = None) -> dict:
    base = instagram_matchday.matchday_spotlight(insights, matches)
    if base.get("kind") in HIGH_PRIORITY_KINDS or base.get("kind") == "delayed_match":
        return base
    return derby_day_spotlight(matches) or multi_goal_scorer_spotlight(matches, scorer_data) or collective_attack_spotlight(matches, scorer_data) or rout_wave_spotlight(matches) or high_scoring_match_spotlight(matches) or bounce_back_spotlight(insights, matches) or winless_run_ended_spotlight(insights, matches) or unbeaten_run_spotlight(insights, matches) or scoring_surge_spotlight(insights) or scoring_drought_spotlight(insights) or winning_streak_spotlight(insights, matches) or both_teams_scored_spotlight(matches) or clean_sheet_wave_spotlight(matches) or away_dominance_spotlight(matches) or home_dominance_spotlight(matches) or draw_dominance_spotlight(matches) or drawless_day_spotlight(matches) or defensive_streak_spotlight(insights) or title_race_spotlight(insights) or base


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


def build_caption(insights: dict, matches: list[dict], scorer_data: dict | None = None) -> str:
    snapshot, latest = instagram_daily.current_snapshot(insights)
    table = snapshot["table"]
    spotlight = editorial_spotlight(insights, matches, scorer_data)
    story = _spotlight_sentence(spotlight)
    partial = " (parcial)" if latest.get("matches", 10) < 10 else ""
    lines = [story, f"Brasileirão {insights['season']} — rodada {latest['round']}{partial}.", "", f"Líder: {table[0]['team']} — {table[0]['points']} pts.", f"G4: {', '.join(row['team'] for row in table[:4])}.", f"Z4: {', '.join(row['team'] for row in table[-4:])}.", *_standings_context(table), "", f"Mais números e evolução rodada a rodada: {instagram_daily.SITE_URL}", "", "#Brasileirao #Brasileirao2026 #FutebolBrasileiro #SerieA"]
    return "\n".join(line for line in lines if line is not None)[:2200]


def render_card(insights: dict, matches: list[dict], output: Path = instagram_daily.DEFAULT_OUTPUT, now: datetime | None = None, scorer_data: dict | None = None) -> Path:
    output = instagram_matchday.render_card(insights, matches, output, now=now)
    spotlight = editorial_spotlight(insights, matches, scorer_data)
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
    scorer_data = instagram_daily.load_scorers()
    matches = instagram_matchday.completed_matches_for_date(all_matches, instagram_matchday.publication_date())
    if args.command == "render": print(render_card(insights, matches, args.output, scorer_data=scorer_data))
    else: print(build_caption(insights, matches, scorer_data))


if __name__ == "__main__":
    main()
