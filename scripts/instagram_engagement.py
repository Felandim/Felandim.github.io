#!/usr/bin/env python3
"""Acrescenta uma pergunta contextual à legenda antes de publicar no Instagram."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import requests


def engagement_question(spotlight: dict) -> str:
    """Cria uma pergunta curta e específica a partir do destaque editorial escolhido."""
    kind = spotlight.get("kind", "")
    text = spotlight.get("text", "")

    if kind == "leader":
        team = text.partition(" assumiu")[0].strip()
        return f"{team} sustenta a liderança na próxima rodada?" if team else "Quem sustenta a liderança na próxima rodada?"
    if kind == "g4":
        return "Quem termina a próxima rodada dentro do G4?"
    if kind == "z4":
        return "Quem consegue sair do Z4 na próxima rodada?"
    if kind == "upset":
        winner = text.partition(" bateu ")[0].strip()
        return f"{winner} confirma a reação na próxima rodada?" if winner else "A zebra confirma a reação na próxima rodada?"
    if kind == "delayed_match":
        return "Esse jogo atrasado muda sua leitura da tabela?"
    if kind == "direct_leapfrog":
        winner = spotlight.get("winner", "")
        return f"{winner} consegue se manter à frente na próxima rodada?" if winner else "A ultrapassagem se sustenta na próxima rodada?"
    if kind == "tight_matches":
        return "A próxima rodada mantém esse nível de equilíbrio?"
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


def _wait_for_container(
    container_id: str,
    access_token: str,
    api_version: str,
    timeout: float = 60,
    interval: float = 2,
) -> None:
    """Espera o Instagram terminar de processar o container antes do publish."""
    deadline = time.monotonic() + timeout
    url = f"https://graph.instagram.com/{api_version}/{container_id}"
    last_status = "UNKNOWN"

    while True:
        response = requests.get(
            url,
            params={"fields": "status_code,status", "access_token": access_token},
            timeout=30,
        )
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


def publish_when_ready(
    instagram_daily,
    image_url: str,
    caption: str,
    ig_user_id: str,
    access_token: str,
    api_version: str,
) -> str:
    """Cria o container, aguarda o processamento e só então publica."""
    base = f"{instagram_daily.GRAPH_HOST}/{api_version}/{ig_user_id}"
    container = instagram_daily._post(
        f"{base}/media",
        {"image_url": image_url, "caption": caption, "access_token": access_token},
    )
    _wait_for_container(container["id"], access_token, api_version)
    media = instagram_daily._post(
        f"{base}/media_publish",
        {"creation_id": container["id"], "access_token": access_token},
    )
    return media["id"]


def main() -> None:
    # Imports tardios mantêm as funções de copy testáveis sem carregar PIL.
    import instagram_daily
    import instagram_matchday

    parser = argparse.ArgumentParser()
    parser.add_argument("--image-url", required=True)
    parser.add_argument("--insights", type=Path, default=instagram_daily.INSIGHTS_FILE)
    parser.add_argument("--matches", type=Path, default=instagram_daily.MATCHES_FILE)
    args = parser.parse_args()

    insights = instagram_daily.load_insights(args.insights)
    all_matches = instagram_daily.load_matches(args.matches)
    matches = instagram_matchday.completed_matches_for_date(all_matches, instagram_matchday.publication_date())
    spotlight = instagram_matchday.matchday_spotlight(insights, matches)
    caption = with_engagement_question(instagram_matchday.build_caption(insights, matches), spotlight)

    media_id = publish_when_ready(
        instagram_daily,
        args.image_url,
        caption,
        os.environ["INSTAGRAM_IG_USER_ID"],
        os.environ["INSTAGRAM_ACCESS_TOKEN"],
        os.getenv("INSTAGRAM_API_VERSION", instagram_daily.DEFAULT_API_VERSION),
    )
    print(f"Publicado: {media_id}")


if __name__ == "__main__":
    main()
