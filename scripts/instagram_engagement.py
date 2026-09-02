#!/usr/bin/env python3
"""Acrescenta uma pergunta contextual à legenda antes de publicar no Instagram."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


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


def main() -> None:
    # Import tardio mantém as funções de copy testáveis sem carregar PIL/requests.
    import instagram_daily

    parser = argparse.ArgumentParser()
    parser.add_argument("--image-url", required=True)
    parser.add_argument("--insights", type=Path, default=instagram_daily.INSIGHTS_FILE)
    parser.add_argument("--matches", type=Path, default=instagram_daily.MATCHES_FILE)
    args = parser.parse_args()

    insights = instagram_daily.load_insights(args.insights)
    matches = instagram_daily.load_matches(args.matches)
    spotlight = instagram_daily.round_spotlight(insights, matches)
    caption = with_engagement_question(instagram_daily.build_caption(insights, matches), spotlight)

    media_id = instagram_daily.publish(
        args.image_url,
        caption,
        os.environ["INSTAGRAM_IG_USER_ID"],
        os.environ["INSTAGRAM_ACCESS_TOKEN"],
        os.getenv("INSTAGRAM_API_VERSION", instagram_daily.DEFAULT_API_VERSION),
    )
    print(f"Publicado: {media_id}")


if __name__ == "__main__":
    main()
