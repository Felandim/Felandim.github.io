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


def single_match_impact_spotlight(insights: dict, matches: list[dict]) -> dict | None:
    """Em dias com um único jogo da rodada, destaca o impacto direto dele na tabela."""
    if len(matches) != 1:
        return None

    match = matches[0]
    snapshots = insights.get("snapshots", [])
    rounds = insights.get("rounds", [])
    if len(snapshots) < 2 or not rounds:
        return None

    latest_round = int(rounds[-1]["round"])
    if int(match.get("round", 0)) != latest_round:
        return None
    if not instagram_daily._score(match.get("score", "")):
        return None

    previous = {row["team"]: row for row in snapshots[-2].get("table", [])}
    current = {row["team"]: row for row in snapshots[-1].get("table", [])}
    teams = [match.get("home"), match.get("away")]
    candidates = []

    for team in teams:
        if not team or team not in previous or team not in current:
            continue

        before, after = previous[team], current[team]
        before_pos, after_pos = int(before["position"]), int(after["position"])
        before_pts, after_pts = int(before["points"]), int(after["points"])
        movement = before_pos - after_pos
        points_delta = after_pts - before_pts

        if after_pos == 1 and before_pos != 1:
            priority = 100
            text = f"{team} assumiu a liderança com {after_pts} pts"
            caption = f"{team} assumiu a liderança e chegou a {after_pts} pontos"
        elif before_pos > 4 and after_pos <= 4:
            priority = 90
            text = f"{team} entrou no G4 e foi a {after_pts} pts"
            caption = f"{team} entrou no G4 e chegou a {after_pts} pontos"
        elif before_pos <= 4 and after_pos > 4:
            priority = 90
            text = f"{team} saiu do G4 e ficou em {after_pos}º"
            caption = f"{team} saiu do G4 e passou a ocupar o {after_pos}º lugar"
        elif before_pos >= 17 and after_pos <= 16:
            priority = 85
            text = f"{team} saiu do Z4 e subiu para {after_pos}º"
            caption = f"{team} saiu do Z4 e subiu para o {after_pos}º lugar"
        elif before_pos <= 16 and after_pos >= 17:
            priority = 85
            text = f"{team} entrou no Z4 e caiu para {after_pos}º"
            caption = f"{team} entrou no Z4 e caiu para o {after_pos}º lugar"
        elif movement > 0:
            priority = 60 + movement
            text = f"{team} subiu para {after_pos}º com {after_pts} pts"
            caption = f"{team} subiu para o {after_pos}º lugar, com {after_pts} pontos"
        elif movement < 0:
            priority = 60 + abs(movement)
            text = f"{team} caiu para {after_pos}º com {after_pts} pts"
            caption = f"{team} caiu para o {after_pos}º lugar, com {after_pts} pontos"
        elif points_delta > 0:
            priority = 40 + max(0, 21 - after_pos)
            text = f"{team} chegou a {after_pts} pts e segue em {after_pos}º"
            caption = f"{team} chegou a {after_pts} pontos e segue em {after_pos}º"
        else:
            priority = 20 + max(0, 21 - after_pos)
            text = f"{team} segue com {after_pts} pts em {after_pos}º"
            caption = f"{team} segue com {after_pts} pontos em {after_pos}º"

        candidates.append({
            "priority": priority,
            "team": team,
            "text": text,
            "caption": caption,
            "position": after_pos,
        })

    if not candidates:
        return None

    best = max(candidates, key=lambda item: (item["priority"], -item["position"], item["team"]))
    home, away, score = match["home"], match["away"], match["score"]
    return {
        "kind": "single_match_impact",
        "label": "IMPACTO DO JOGO",
        "text": best["text"],
        "caption": f"Impacto do jogo: após {home} {score} {away}, {best['caption']}.",
        "match": match,
        "team": best["team"],
    }


def direct_leapfrog_spotlight(insights: dict, matches: list[dict]) -> dict | None:
    """Detecta confronto em que o vencedor começou abaixo e terminou acima do adversário."""
    snapshots = insights.get("snapshots", [])
    rounds = insights.get("rounds", [])
    if len(snapshots) < 2 or not rounds:
        return None

    latest_round = int(rounds[-1]["round"])
    previous = {row["team"]: row["position"] for row in snapshots[-2].get("table", [])}
    current = {row["team"]: row["position"] for row in snapshots[-1].get("table", [])}
    candidates = []

    for match in matches:
        if int(match.get("round", 0)) != latest_round:
            continue
        score = instagram_daily._score(match.get("score", ""))
        if not score or score[0] == score[1]:
            continue

        winner = match["home"] if score[0] > score[1] else match["away"]
        loser = match["away"] if winner == match["home"] else match["home"]
        if winner not in previous or loser not in previous or winner not in current or loser not in current:
            continue
        if previous[winner] <= previous[loser] or current[winner] >= current[loser]:
            continue

        candidates.append({
            "winner": winner,
            "loser": loser,
            "winner_from": previous[winner],
            "winner_to": current[winner],
            "loser_from": previous[loser],
            "loser_to": current[loser],
            "cross": previous[winner] - previous[loser],
        })

    if not candidates:
        return None

    best = max(candidates, key=lambda item: (item["cross"], item["winner_from"] - item["winner_to"], item["winner"]))
    return {
        "kind": "direct_leapfrog",
        "label": "ULTRAPASSAGEM DIRETA",
        "text": f"{best['winner']} venceu o {best['loser']} e terminou a rodada à frente",
        "caption": (
            f"Ultrapassagem direta: {best['winner']} começou a rodada em {best['winner_from']}º, "
            f"venceu o {best['loser']} e terminou em {best['winner_to']}º, à frente do rival."
        ),
        **best,
    }


def direct_rival_spotlight(
    insights: dict,
    matches: list[dict],
    maximum_points_gap: int = 3,
) -> dict | None:
    """Destaca vitória sobre adversário que começou a rodada praticamente empatado em pontos."""
    snapshots = insights.get("snapshots", [])
    rounds = insights.get("rounds", [])
    if len(snapshots) < 2 or not rounds:
        return None

    latest_round = int(rounds[-1]["round"])
    previous = {
        row["team"]: {"points": row["points"], "position": row["position"]}
        for row in snapshots[-2].get("table", [])
    }
    candidates = []

    for match in matches:
        if int(match.get("round", 0)) != latest_round:
            continue
        score = instagram_daily._score(match.get("score", ""))
        if not score or score[0] == score[1]:
            continue

        winner = match["home"] if score[0] > score[1] else match["away"]
        loser = match["away"] if winner == match["home"] else match["home"]
        if winner not in previous or loser not in previous:
            continue

        points_gap = abs(previous[winner]["points"] - previous[loser]["points"])
        if points_gap > maximum_points_gap:
            continue

        candidates.append({
            "winner": winner,
            "loser": loser,
            "points_gap": points_gap,
            "winner_position": previous[winner]["position"],
            "loser_position": previous[loser]["position"],
            "goal_margin": abs(score[0] - score[1]),
        })

    if not candidates:
        return None

    best = min(
        candidates,
        key=lambda item: (
            item["points_gap"],
            min(item["winner_position"], item["loser_position"]),
            -item["goal_margin"],
            item["winner"],
        ),
    )
    gap_text = "empatados em pontos" if best["points_gap"] == 0 else (
        f"separados por {best['points_gap']} {'ponto' if best['points_gap'] == 1 else 'pontos'}"
    )
    return {
        "kind": "direct_rival",
        "label": "CONFRONTO DIRETO",
        "text": f"{best['winner']} bateu {best['loser']} • {gap_text} antes da rodada",
        "caption": (
            f"Confronto direto: {best['winner']} venceu {best['loser']}; "
            f"os dois começaram a rodada {gap_text}."
        ),
        **best,
    }


def tight_matchday_spotlight(
    matches: list[dict],
    minimum_matches: int = 3,
    minimum_share: float = 0.75,
) -> dict | None:
    """Destaca dias em que quase todos os jogos foram decididos no detalhe."""
    scored = []
    for match in matches:
        score = instagram_daily._score(match.get("score", ""))
        if score:
            scored.append(score)

    if len(scored) < minimum_matches:
        return None

    close_games = sum(1 for home, away in scored if abs(home - away) <= 1)
    share = close_games / len(scored)
    if share < minimum_share:
        return None

    return {
        "kind": "tight_matches",
        "label": "JOGOS NO LIMITE",
        "text": f"{close_games} de {len(scored)} jogos do dia decididos por até 1 gol",
        "caption": (
            f"Jogos no limite: {close_games} de {len(scored)} partidas do dia "
            "terminaram empatadas ou foram decididas por apenas um gol."
        ),
        "close_games": close_games,
        "matches": len(scored),
        "share": share,
    }


def sustained_climb_spotlight(
    insights: dict,
    transitions: int = 3,
    minimum_gain: int = 3,
) -> dict | None:
    """Detecta um time que ganhou posições em todas as últimas rodadas, evitando destaque de ruído pontual."""
    snapshots = insights.get("snapshots", [])
    if len(snapshots) < transitions + 1:
        return None

    recent = snapshots[-(transitions + 1):]
    positions = [
        {row["team"]: row["position"] for row in snapshot.get("table", [])}
        for snapshot in recent
    ]
    candidates = []
    for team, start_position in positions[0].items():
        series = [table.get(team) for table in positions]
        if any(position is None for position in series):
            continue
        if not all(series[index + 1] < series[index] for index in range(transitions)):
            continue
        gain = start_position - series[-1]
        if gain < minimum_gain:
            continue
        candidates.append({"team": team, "gain": gain, "from": start_position, "to": series[-1]})

    if not candidates:
        return None

    best = max(candidates, key=lambda item: (item["gain"], -item["to"], item["team"]))
    rounds = transitions
    return {
        "kind": "sustained_climb",
        "label": "ARRANCADA NA TABELA",
        "text": f"{best['team']} subiu {best['gain']} posições nas últimas {rounds} rodadas",
        "caption": (
            f"Arrancada na tabela: {best['team']} ganhou posição em cada uma das últimas {rounds} rodadas, "
            f"saindo de {best['from']}º para {best['to']}º."
        ),
        **best,
        "rounds": rounds,
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

    single_match = single_match_impact_spotlight(insights, matches)
    if single_match:
        return single_match

    base = instagram_daily.round_spotlight(insights, matches)
    high_priority = {
        "leader", "g4", "z4", "upset", "g4_cluster", "z4_cluster",
    }
    if base.get("kind") in high_priority:
        return base

    leapfrog = direct_leapfrog_spotlight(insights, matches)
    if leapfrog:
        return leapfrog

    direct_rival = direct_rival_spotlight(insights, matches)
    if direct_rival:
        return direct_rival

    climb = sustained_climb_spotlight(insights)
    if climb:
        return climb

    tight = tight_matchday_spotlight(matches)
    if tight:
        return tight

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
