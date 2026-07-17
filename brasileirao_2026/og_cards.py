#!/usr/bin/env python3
"""Gera imagens Open Graph estáticas para as páginas do Brasileirão."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
INK = "#101714"
PAPER = "#F5F3EA"
HOT = "#DFFF00"
CORAL = "#FF654D"
MUTED = "#AAB5AE"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size > 32:
        candidate = font(size, bold=True)
        if draw.textbbox((0, 0), text, font=candidate)[2] <= max_width:
            return candidate
        size -= 2
    return font(32, bold=True)


def base_card(kicker: str, title: str, detail: str, accent: str = HOT) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), INK)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 24, HEIGHT), fill=accent)
    draw.rectangle((790, 0, WIDTH, HEIGHT), fill=accent)
    draw.ellipse((920, 68, 1270, 418), outline=INK, width=58)
    draw.text((70, 58), kicker.upper(), fill=accent, font=font(22, bold=True))
    title_font = fit_font(draw, title.upper(), 680, 76)
    draw.text((70, 145), title.upper(), fill=PAPER, font=title_font)
    draw.line((70, 360, 715, 360), fill=accent, width=8)
    draw.text((70, 402), detail, fill=MUTED, font=font(28))
    draw.text((70, 555), "RODADA A RODADA", fill=PAPER, font=font(22, bold=True))
    draw.text((950, 535), "R/R", fill=INK, font=font(48, bold=True))
    return image, draw


def save_card(path: Path, kicker: str, title: str, detail: str, accent: str = HOT) -> None:
    image, _ = base_card(kicker, title, detail, accent)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def save_team_card(path: Path, profile: dict[str, Any], current_round: int) -> None:
    team = profile["team"]
    row = profile["current"]
    image, draw = base_card(
        f"Brasileirão 2026 · rodada {current_round}",
        team,
        f'{row["position"]}º lugar  ·  {row["points"]} pontos  ·  {row["wins"]} vitórias',
    )
    history = profile.get("history", [])
    if history:
        left, top, right, bottom = 825, 335, 1140, 500
        draw.line((left, top, left, bottom), fill=INK, width=3)
        draw.line((left, bottom, right, bottom), fill=INK, width=3)
        points = []
        for index, item in enumerate(history):
            x = left + index * (right - left) / max(len(history) - 1, 1)
            y = top + (item["position"] - 1) * (bottom - top) / 19
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=INK, width=7, joint="curve")
        x, y = points[-1]
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=CORAL)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def build_og_cards(root: Path, insights: dict[str, Any]) -> None:
    output = root / "assets" / "og"
    current_round = insights["current_round"]
    current_table = insights["snapshots"][-1]["table"]
    leader = current_table[0]
    latest_scorers = insights["scorers"][-1]["ranking"] if insights["scorers"] else []
    top_scorer = latest_scorers[0] if latest_scorers else None

    save_card(
        output / "rodada-a-rodada.png",
        "Brasileirão Série A · 2026",
        "A tabela tem memória.",
        f'{leader["team"]} lidera após a rodada {current_round}',
    )
    save_card(
        output / "classificacao.png",
        "Classificação histórica",
        "Rodada a rodada",
        "Reconstrua a tabela em qualquer rodada",
    )
    scorer_detail = (
        f'{top_scorer["name"]}: {top_scorer["goals"]} gols'
        if top_scorer
        else "Acompanhe a disputa gol a gol"
    )
    save_card(output / "artilharia.png", "Artilharia 2026", "Gol a gol.", scorer_detail, CORAL)
    save_card(
        output / "comparador.png",
        "Comparador de times",
        "Campanha contra campanha",
        "Posição, pontos, vitórias e saldo por rodada",
        CORAL,
    )

    for slug, profile in insights["team_profiles"].items():
        save_team_card(output / "times" / f"{slug}.png", profile, current_round)

    for summary in insights["rounds"]:
        number = summary["round"]
        save_card(
            output / "rodadas" / f"rodada-{number}.png",
            f"Brasileirão 2026 · rodada {number}",
            f"O que mudou na rodada {number}",
            f'{summary["leader"]} líder  ·  {summary["goals"]} gols  ·  {summary["matches"]} jogos',
        )
