#!/usr/bin/env python3
"""Acrescenta uma pergunta contextual à legenda antes de publicar no Instagram."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import requests


def _wait_for_image_url(image_url: str, timeout: float = 60, interval: float = 2) -> None:
    """Confirma que o card público já pode ser baixado antes de chamar o Instagram."""
    deadline = time.monotonic() + timeout
    last_status = "indisponível"
    while True:
        try:
            response = requests.get(image_url, timeout=30)
            content_type = response.headers.get("content-type", "").lower()
            if response.ok and content_type.startswith("image/") and response.content.startswith(b"\x89PNG\r\n\x1a\n"):
                return
            last_status = f"HTTP {response.status_code} ({content_type or 'sem content-type'})"
        except requests.RequestException as exc:
            last_status = exc.__class__.__name__
        if time.monotonic() >= deadline:
            raise TimeoutError(f"O card não ficou publicamente disponível em {timeout}s; último estado: {last_status}")
        time.sleep(interval)


def _create_container_with_retry(instagram_daily, url: str, data: dict, attempts: int = 4, interval: float = 3) -> dict:
    """Repete a criação do container, etapa sujeita a atraso de propagação da imagem."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return instagram_daily._post(url, data)
        except RuntimeError as exc:
            last_error = exc
            if attempt == attempts:
                raise
            time.sleep(interval * attempt)
    raise last_error  # pragma: no cover


def engagement_question(spotlight: dict) -> str:
    """Cria uma pergunta curta e específica a partir do destaque editorial escolhido."""
    kind = spotlight.get("kind", "")
    text = spotlight.get("text", "")

    if kind == "leader":
        team = text.partition(" assumiu")[0].strip()
        return f"{team} sustenta a liderança na próxima rodada?" if team else "Quem sustenta a liderança na próxima rodada?"
    if kind == "g4":
        advantaged = str(spotlight.get("advantaged", "")).strip()
        displaced = str(spotlight.get("displaced", "")).strip()
        if spotlight.get("tiebreaker") and advantaged and displaced:
            return f"{advantaged} sustenta a vaga à frente do {displaced}?"
        return "Quem termina a próxima rodada dentro do G4?"
    if kind == "z4":
        advantaged = str(spotlight.get("advantaged", "")).strip()
        displaced = str(spotlight.get("displaced", "")).strip()
        if spotlight.get("tiebreaker") and advantaged and displaced:
            return f"{advantaged} mantém a vantagem sobre o {displaced}?"
        return "Quem consegue sair do Z4 na próxima rodada?"
    if kind == "upset":
        winner = text.partition(" bateu ")[0].strip()
        return f"{winner} confirma a reação na próxima rodada?" if winner else "A zebra confirma a reação na próxima rodada?"
    if kind == "delayed_match":
        return "Esse jogo atrasado muda sua leitura da tabela?"
    if kind == "single_match_impact":
        team = str(spotlight.get("team", "")).strip()
        return f"Esse resultado muda o que você espera do {team} na próxima rodada?" if team else "Esse resultado muda sua leitura para a próxima rodada?"
    if kind == "direct_leapfrog":
        winner = spotlight.get("winner", "")
        return f"{winner} consegue se manter à frente na próxima rodada?" if winner else "A ultrapassagem se sustenta na próxima rodada?"
    if kind == "direct_rival":
        winner = spotlight.get("winner", "")
        loser = spotlight.get("loser", "")
        if winner and loser:
            return f"{winner} abre vantagem sobre {loser} nas próximas rodadas?"
        return "Quem leva vantagem nessa disputa direta?"
    if kind == "tight_matches":
        return "A próxima rodada mantém esse nível de equilíbrio?"
    if kind == "derby_day":
        return "Qual clássico mais mexeu com você?"
    if kind == "goal_fest":
        goals = spotlight.get("goals")
        return f"Qual jogo da rodada ainda pode superar esses {goals} gols?" if goals else "Qual jogo da rodada ainda pode superar esse placar?"
    if kind == "multi_goal_scorer":
        player = str(spotlight.get("player", "")).strip()
        return f"{player} repete a dose na próxima rodada?" if player else "Quem repete esse feito na próxima rodada?"
    if kind == "collective_attack":
        team = str(spotlight.get("team", "")).strip()
        names = [str(name).strip() for name in spotlight.get("scorers", []) if str(name).strip()]
        if team and names:
            return f"Qual desses nomes pode decidir de novo pelo {team}: {_join_question_options(names)}?"
        return "Qual ataque pode repetir essa força coletiva na próxima rodada?"
    if kind == "rout_wave":
        winners = [str(item.get("winner", "")).strip() for item in spotlight.get("routs", [])]
        winners = [winner for winner in winners if winner]
        if len(winners) >= 2:
            return f"Qual goleada foi mais marcante: {_join_question_options(winners)}?"
        return "Qual dessas goleadas mais marcou a rodada?"
    if kind == "bounce_back":
        team = str(spotlight.get("team", "")).strip()
        return f"{team} confirma a reação na próxima rodada?" if team else "Quem confirma a reação na próxima rodada?"
    if kind == "scoring_surge":
        return "Esse ritmo de gols se mantém até o fim da rodada?"
    if kind == "scoring_drought":
        return "A rodada destrava ou termina com cara de jogo amarrado?"
    if kind == "both_teams_scored":
        return "Na próxima rodada, qual duelo promete gols dos dois lados?"
    if kind == "clean_sheet_wave":
        return "Qual dessas defesas mais te impressionou?"
    if kind == "away_dominance":
        return "Na próxima rodada, os mandantes retomam a vantagem?"
    if kind == "home_dominance":
        return "Na próxima rodada, quem consegue quebrar a força dos mandantes?"
    if kind == "draw_dominance":
        return "Qual time está mais perto de transformar equilíbrio em vitória?"
    if kind == "drawless_day":
        return "Na próxima rodada, qual confronto tem mais cara de empate?"
    if kind == "winning_streak":
        team = spotlight.get("team", "")
        return f"Quem consegue parar o {team}?" if team else "Quem consegue parar essa sequência?"
    if kind == "defensive_streak":
        team = spotlight.get("team", "")
        return f"Quem consegue furar a defesa do {team}?" if team else "Quanto tempo essa sequência sem sofrer gols dura?"
    if kind == "title_cluster":
        teams = [str(team).strip() for team in spotlight.get("teams", []) if str(team).strip()]
        if len(teams) >= 2:
            options = ", ".join(teams[:3])
            return f"Hoje, quem está mais forte nessa disputa: {options}?"
        return "Quem sai desse pelotão como principal candidato ao título?"
    if kind == "g4_cluster":
        return "Quem leva a quarta vaga nesse pelotão?"
    if kind == "z4_cluster":
        return "Quem consegue abrir distância do Z4?"
    if kind == "g4_pressure":
        team = spotlight.get("team", "")
        return f"{team} entra no G4 na próxima rodada?" if team else "Quem entra no G4 na próxima rodada?"
    if kind == "z4_pressure":
        team = spotlight.get("team", "")
        return f"{team} sai do Z4 na próxima rodada?" if team else "Quem sai do Z4 na próxima rodada?"
    if kind == "biggest_win":
        return "Esse placar muda sua leitura sobre esses times?"
    if kind == "form":
        return "Quem consegue manter esse ritmo nas próximas rodadas?"
    return "A próxima rodada supera essa marca?"


def _join_question_options(items: list[str]) -> str:
    unique = list(dict.fromkeys(items))
    if len(unique) < 2:
        return "".join(unique)
    return f"{', '.join(unique[:-1])} ou {unique[-1]}"


def with_engagement_question(caption: str, spotlight: dict, limit: int = 2200) -> str:
    """Insere a pergunta antes do CTA do site, preservando o limite do Instagram."""
    question = engagement_question(spotlight)
    if question in caption:
        return caption[:limit]

    marker = "\n\nMais números e evolução rodada a rodada:"
    if marker in caption:
        caption = caption.replace(marker, f"\n\n{question}{marker}", 1)
    else:
        caption = f"{caption.rstrip()}\n\n{question}"
    return caption[:limit]


def _wait_for_container(container_id: str, access_token: str, api_version: str, timeout: float = 60, interval: float = 2) -> None:
    """Espera o Instagram terminar de processar o container antes do publish."""
    deadline = time.monotonic() + timeout
    url = f"https://graph.instagram.com/{api_version}/{container_id}"
    last_status = "UNKNOWN"
    while True:
        response = requests.get(url, params={"fields": "status_code,status", "access_token": access_token}, timeout=30)
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}
        if not response.ok:
            raise RuntimeError(f"Instagram container status {response.status_code}: {payload}")
        status_code = str(payload.get("status_code") or "").upper()
        last_status = status_code or str(payload.get("status") or "UNKNOWN")
        if status_code in {"FINISHED", "PUBLISHED"}:
            return
        if status_code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram container {container_id} terminou com status {status_code}: {payload}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Instagram container {container_id} não ficou pronto em {timeout}s; último status: {last_status}")
        time.sleep(interval)


def publish_when_ready(instagram_daily, image_url: str, caption: str, ig_user_id: str, access_token: str, api_version: str) -> str:
    """Cria o container, aguarda o processamento e só então publica."""
    base = f"{instagram_daily.GRAPH_HOST}/{api_version}/{ig_user_id}"
    _wait_for_image_url(image_url)
    container = _create_container_with_retry(
        instagram_daily,
        f"{base}/media",
        {"image_url": image_url, "caption": caption, "access_token": access_token},
    )
    _wait_for_container(container["id"], access_token, api_version)
    media = instagram_daily._post(f"{base}/media_publish", {"creation_id": container["id"], "access_token": access_token})
    return media["id"]


def main() -> None:
    import instagram_daily
    import instagram_editorial
    import instagram_matchday

    parser = argparse.ArgumentParser()
    parser.add_argument("--image-url", required=True)
    parser.add_argument("--insights", type=Path, default=instagram_daily.INSIGHTS_FILE)
    parser.add_argument("--matches", type=Path, default=instagram_daily.MATCHES_FILE)
    args = parser.parse_args()

    insights = instagram_daily.load_insights(args.insights)
    all_matches = instagram_daily.load_matches(args.matches)
    scorer_data = instagram_daily.load_scorers()
    matches = instagram_matchday.completed_matches_for_date(all_matches, instagram_matchday.publication_date())
    spotlight = instagram_editorial.editorial_spotlight(insights, matches, scorer_data)
    caption = with_engagement_question(instagram_editorial.build_caption(insights, matches, scorer_data), spotlight)

    media_id = publish_when_ready(
        instagram_daily, args.image_url, caption,
        os.environ["INSTAGRAM_IG_USER_ID"], os.environ["INSTAGRAM_ACCESS_TOKEN"],
        os.getenv("INSTAGRAM_API_VERSION", instagram_daily.DEFAULT_API_VERSION),
    )
    print(f"Publicado: {media_id}")


if __name__ == "__main__":
    main()
